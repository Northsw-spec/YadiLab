"""Explicit switchport shutdown and access-VLAN isolation in a volatile DHCP lab."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.dhcp_registry import DhcpSessionRegistry
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_dhcp_registry import clients, start


def vlan_clients():
    p = clients()
    for port in p["nodes"][1]["ports"]:
        port["vlan"] = {"mode": "access", "vlan": 20 if port["id"] == "p-3" else 10}
    return p


class PortFaultTests(unittest.TestCase):
    def test_t1_t2_fail_after_real_dora_then_original_lease_expires(self):
        p = clients()
        before = copy.deepcopy(p)
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        first = reg.run(sid, p, "client", "eth0", 101, 60)
        self.assertEqual(first["result"]["status"], "ACK_RECEIVED")
        down = reg.port_fault(sid, p, "sw", "s", True)
        self.assertEqual(down["faultedPorts"], [{"nodeId": "sw", "portId": "s"}])
        self.assertEqual(down["faultedLinks"], [])
        self.assertEqual(down["macTables"], [])
        self.assertEqual(down["leaseCount"], 1)
        reg.advance(sid, p, 30)
        t1 = reg.renew(sid, p, "client", "eth0", 102)
        self.assertEqual(t1["result"]["phase"], "RENEWING")
        self.assertEqual(t1["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertFalse(t1["result"]["leaseRenewed"])
        self.assertFalse(t1["result"]["request"]["receivedAtServer"])
        self.assertNotIn("to-server", [x["linkId"] for x in t1["result"]["request"]["transmissions"]])
        self.assertEqual(t1["leases"][0]["expiresAtSeconds"], 60)
        reg.advance(sid, p, 23)
        t2 = reg.renew(sid, p, "client", "eth0", 103)
        self.assertEqual(t2["result"]["phase"], "REBINDING")
        self.assertEqual(t2["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(t2["result"]["request"]["ipDestination"], "255.255.255.255")
        self.assertEqual(t2["leases"][0]["renewalCount"], 0)
        expired = reg.advance(sid, p, 7)
        self.assertEqual(expired["leaseCount"], 0)
        self.assertEqual(expired["expiredLeases"][0]["ipv4"], "192.0.2.70")
        self.assertEqual(expired["faultedPorts"], [{"nodeId": "sw", "portId": "s"}])
        up = reg.port_fault(sid, p, "sw", "s", False)
        self.assertEqual(up["faultedPorts"], [])
        self.assertEqual(up["macTables"], [])
        fresh = reg.run(sid, p, "client-2", "eth0", 104, 60)
        self.assertEqual(fresh["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(fresh["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(p, before)

    def test_shutdown_client_switchport_drops_at_ingress_then_restores_at_t2(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 101, 60)
        reg.port_fault(sid, p, "sw", "c", True)
        reg.advance(sid, p, 30)
        t1 = reg.renew(sid, p, "client", "eth0", 102)
        self.assertEqual(t1["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(t1["result"]["request"]["transmissions"], [])
        reg.advance(sid, p, 23)
        reg.port_fault(sid, p, "sw", "c", False)
        t2 = reg.renew(sid, p, "client", "eth0", 103)
        self.assertEqual(t2["result"]["status"], "ACK_RECEIVED")
        self.assertTrue(t2["result"]["request"]["receivedAtServer"])
        self.assertTrue(t2["result"]["ack"]["receivedAtClient"])
        self.assertEqual(t2["leases"][0]["expiresAtSeconds"], 113)

    def test_link_and_port_faults_do_not_resurrect_each_other(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.link_fault(sid, p, "to-server", True)
        reg.port_fault(sid, p, "sw", "s", True)
        link_restored = reg.link_fault(sid, p, "to-server", False)
        self.assertEqual(link_restored["faultedLinks"], [])
        self.assertEqual(link_restored["faultedPorts"], [{"nodeId": "sw", "portId": "s"}])
        missing = reg.run(sid, p, "client", "eth0", 101, 60)
        self.assertEqual(missing["result"]["status"], "DISCOVER_NOT_RECEIVED")
        restored = reg.port_fault(sid, p, "sw", "s", False)
        self.assertEqual(restored["faultedPorts"], [])
        success = reg.run(sid, p, "client", "eth0", 102, 60)
        self.assertEqual(success["result"]["status"], "ACK_RECEIVED")
        reg.port_fault(sid, p, "sw", "s", True)
        reg.link_fault(sid, p, "to-server", True)
        reg.port_fault(sid, p, "sw", "s", False)
        self.assertEqual(reg._get(sid).state()["faultedLinks"], ["to-server"])
        self.assertEqual(reg._get(sid).dhcp.fabric.wires.get(("sw", "s")), None)

    def test_invalid_port_faults_never_touch_lease_mac_or_operation_count(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 101, 60)
        before = reg._get(sid).state()
        changed = copy.deepcopy(p)
        changed["links"][0]["enabled"] = False
        invalid = (
            ("sw", "invalid", True, p), ("client", "eth0", True, p),
            ("sw", "s", True, changed), ("sw", "s", 1, p),
            ("sw", "s", "true", p), ("sw", "s", False, p),
            (None, "s", True, p),
        )
        for nid, pid, disabled, project in invalid:
            with self.subTest(nid=nid, pid=pid), self.assertRaises(ProjectValidationError):
                reg.port_fault(sid, project, nid, pid, disabled)
            self.assertEqual(reg._get(sid).state(), before)
        reg.port_fault(sid, p, "sw", "s", True)
        frozen = reg._get(sid).state()
        with self.assertRaises(ProjectValidationError):
            reg.port_fault(sid, p, "sw", "s", True)
        self.assertEqual(reg._get(sid).state(), frozen)
        reg.reset(sid, p)
        self.assertEqual(reg._get(sid).state()["faultedPorts"], [])

    def test_faults_only_in_one_session(self):
        p = clients()
        reg = DhcpSessionRegistry()
        sid1 = start(reg, p)["sessionId"]
        sid2 = start(reg, p)["sessionId"]
        reg.port_fault(sid1, p, "sw", "s", True)
        self.assertEqual(reg.run(sid1, p, "client", "eth0", 101, 60)
                         ["result"]["status"], "DISCOVER_NOT_RECEIVED")
        self.assertEqual(reg.run(sid2, p, "client", "eth0", 102, 60)
                         ["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(reg._get(sid2).state()["faultedPorts"], [])


class VlanFaultTests(unittest.TestCase):
    def test_vlan_isolation_after_ack_t1_and_t2_fail_and_restore_allows_new_dora(self):
        p = vlan_clients()
        original = copy.deepcopy(p)
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        first = reg.run(sid, p, "client", "eth0", 101, 60)
        self.assertEqual(first["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(first["leases"][0]["ipv4"], "192.0.2.70")
        fault = reg.vlan_fault(sid, p, "sw", "c", 20)
        self.assertEqual(fault["faultedAccessVlans"], [{
            "nodeId": "sw", "portId": "c", "originalVlan": 10, "faultVlan": 20,
        }])
        self.assertEqual(fault["macTables"], [])
        reg.advance(sid, p, 30)
        t1 = reg.renew(sid, p, "client", "eth0", 102)
        self.assertEqual(t1["result"]["phase"], "RENEWING")
        self.assertEqual(t1["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertFalse(t1["result"]["request"]["receivedAtServer"])
        self.assertFalse(t1["result"]["leaseRenewed"])
        self.assertEqual(t1["leases"][0]["expiresAtSeconds"], 60)
        reg.advance(sid, p, 23)
        t2 = reg.renew(sid, p, "client", "eth0", 103)
        self.assertEqual(t2["result"]["phase"], "REBINDING")
        self.assertEqual(t2["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertFalse(t2["result"]["request"]["receivedAtServer"])
        self.assertEqual(t2["leases"][0]["expiresAtSeconds"], 60)
        expire = reg.advance(sid, p, 7)
        self.assertEqual(expire["leaseCount"], 0)
        self.assertEqual(expire["expiredLeases"][0]["state"], "EXPIRED")
        restored = reg.vlan_fault(sid, p, "sw", "c", None)
        self.assertEqual(restored["faultedAccessVlans"], [])
        self.assertEqual(restored["macTables"], [])
        recovered = reg.run(sid, p, "client", "eth0", 104, 60)
        self.assertEqual(recovered["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(recovered["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(p, original)

    def test_restore_before_expiry_validates_ack_over_vlan10(self):
        p = vlan_clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        reg.run(sid, p, "client", "eth0", 101, 60)
        reg.vlan_fault(sid, p, "sw", "c", 20)
        reg.advance(sid, p, 30)
        self.assertEqual(reg.renew(sid, p, "client", "eth0", 102)["result"]["status"],
                         "REQUEST_NOT_RECEIVED")
        reg.advance(sid, p, 23)
        reg.vlan_fault(sid, p, "sw", "c", None)
        success = reg.renew(sid, p, "client", "eth0", 103)
        self.assertEqual(success["result"]["status"], "ACK_RECEIVED")
        self.assertTrue(success["result"]["request"]["receivedAtServer"])
        self.assertTrue(success["result"]["ack"]["receivedAtClient"])
        self.assertEqual(success["leases"][0]["expiresAtSeconds"], 113)
        self.assertEqual(success["leases"][0]["renewalCount"], 1)

    def test_reject_undocumented_vlan_trunk_unconfigured_and_invalid_id(self):
        p = vlan_clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, p)["sessionId"]
        frozen = reg._get(sid).state()
        changed = copy.deepcopy(p)
        changed["links"][0]["enabled"] = False
        bad = (
            ("sw", "c", 99, p), ("sw", "c", True, p),
            ("sw", "c", 10, p), ("sw", "c", None, p),
            ("sw", "s", 30, p), ("sw", "bad", 20, p),
            ("client", "eth0", 20, p), ("sw", "c", 20, changed),
        )
        for nid, pid, vlan, project in bad:
            with self.subTest(port=pid, vlan=vlan), self.assertRaises(ProjectValidationError):
                reg.vlan_fault(sid, project, nid, pid, vlan)
            self.assertEqual(reg._get(sid).state(), frozen)
        reg.vlan_fault(sid, p, "sw", "c", 20)
        changed_state = reg._get(sid).state()
        with self.assertRaises(ProjectValidationError):
            reg.vlan_fault(sid, p, "sw", "c", 20)
        self.assertEqual(reg._get(sid).state(), changed_state)
        reg.reset(sid, p)
        self.assertEqual(reg._get(sid).state()["faultedAccessVlans"], [])

    def test_trunk_and_switch_to_switch_access_port_rejected(self):
        p = vlan_clients()
        p["nodes"][1]["ports"][0]["vlan"] = {"mode": "trunk", "allowedVlans": [10, 20]}
        # Endpoint-to-trunk is invalid topology, so creation must reject.
        with self.assertRaises(ProjectValidationError):
            start(DhcpSessionRegistry(), p)
        q = vlan_clients()
        q["nodes"][1]["ports"][0]["vlan"] = None
        with self.assertRaises(ProjectValidationError):
            start(DhcpSessionRegistry(), q)


class PortVlanFaultHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = ProjectStore(self.root)
        self.server = LabHTTPServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def post(self, path, body):
        request = Request(
            self.url + path, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as r:
                return r.status, json.loads(r.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_http_port_vlan_faults_and_true_saved_project_bytes(self):
        p = vlan_clients()
        self.store.save("baseline", p)
        file = self.root / "baseline.yadilab"
        saved = file.read_bytes()
        digest = hashlib.sha256(saved).hexdigest()
        code, start_state = self.post("/api/dhcp/session/start", {
            "project": p, "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"})
        self.assertEqual(code, 200)
        sid = start_state["sessionId"]
        base = {"sessionId": sid, "project": p}
        def call(name, **parts):
            return self.post("/api/dhcp/session/" + name, {**base, **parts})
        code, a = call("run", clientNode="client", clientPort="eth0",
                       transactionId=101, leaseSeconds=60)
        self.assertEqual(code, 200)
        self.assertEqual(a["result"]["status"], "ACK_RECEIVED")
        code, portdown = call("port-fault", nodeId="sw", portId="s", disabled=True)
        self.assertEqual(code, 200)
        self.assertEqual(portdown["faultedPorts"], [{"nodeId": "sw", "portId": "s"}])
        self.assertEqual(portdown["leaseCount"], 1)
        self.assertEqual(call("advance", seconds=30)[1]["clockSeconds"], 30)
        self.assertEqual(call("renew", clientNode="client", clientPort="eth0",
                              transactionId=102)[1]["result"]["status"],
                         "REQUEST_NOT_RECEIVED")
        code, portup = call("port-fault", nodeId="sw", portId="s", disabled=False)
        self.assertEqual(code, 200)
        self.assertEqual(portup["faultedPorts"], [])
        code, vlan = call("vlan-fault", nodeId="sw", portId="c", vlanId=20)
        self.assertEqual(code, 200)
        self.assertEqual(vlan["faultedAccessVlans"][0]["faultVlan"], 20)
        self.assertEqual(call("advance", seconds=23)[1]["clockSeconds"], 53)
        code, rebind = call("renew", clientNode="client", clientPort="eth0",
                            transactionId=103)
        self.assertEqual(code, 200)
        self.assertEqual(rebind["result"]["phase"], "REBINDING")
        self.assertEqual(rebind["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(rebind["leases"][0]["expiresAtSeconds"], 60)
        code, restore = call("vlan-fault", nodeId="sw", portId="c", vlanId=None)
        self.assertEqual(code, 200)
        self.assertEqual(restore["faultedAccessVlans"], [])
        code, renewed = call("renew", clientNode="client", clientPort="eth0",
                             transactionId=104)
        self.assertEqual(code, 200)
        self.assertEqual(renewed["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(renewed["leases"][0]["expiresAtSeconds"], 113)
        self.assertEqual(file.read_bytes(), saved)
        self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), digest)
        self.assertEqual(ProjectStore(self.root).read("baseline")["project"], p)
        self.assertEqual(sorted(x.name for x in self.root.glob("*.yadilab")),
                         ["baseline.yadilab"])

    def test_http_invalid_fails_closed_and_server_restart_discards_faults(self):
        p = vlan_clients()
        code, state = self.post("/api/dhcp/session/start", {
            "project": p, "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"})
        self.assertEqual(code, 200)
        sid = state["sessionId"]
        base = {"sessionId": sid, "project": p,
                "nodeId": "sw", "portId": "s", "disabled": True}
        mutated = copy.deepcopy(p)
        mutated["links"][0]["enabled"] = False
        for path, payload in (
            ("/api/dhcp/session/port-fault", {**base, "disabled": 1}),
            ("/api/dhcp/session/port-fault", {**base, "nodeId": "server"}),
            ("/api/dhcp/session/port-fault", {**base, "project": mutated}),
            ("/api/dhcp/session/port-fault", {**base, "extra": 1}),
            ("/api/dhcp/session/vlan-fault", {**base, "vlanId": 20}),
            ("/api/dhcp/session/vlan-fault", {"sessionId": sid, "project": p,
                                                "nodeId": "sw", "portId": "c", "vlanId": 99}),
        ):
            with self.subTest(path=path):
                status, response = self.post(path, payload)
                self.assertEqual(status, 422)
                self.assertEqual(response["error"], "INVALID_PROJECT")
                self.assertEqual(self.server.dhcp_sessions._get(sid).state()["operationCount"], 0)
        self.assertEqual(self.post("/api/dhcp/session/port-fault", base)[0], 200)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.server = LabHTTPServer(("127.0.0.1", 0), ProjectStore(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        status, response = self.post("/api/dhcp/session/port-fault", base)
        self.assertEqual(status, 422)
        self.assertIn("unknown or expired", response["message"])
