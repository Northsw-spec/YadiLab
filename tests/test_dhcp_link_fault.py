"""Fault injection only in a running DHCP session; real T1/T2 and disk invariants."""
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


class SessionCableFaultTests(unittest.TestCase):
    def test_break_after_ack_t1_and_t2_fail_then_expire_and_reallocate(self):
        project = clients()
        original = copy.deepcopy(project)
        registry = DhcpSessionRegistry()
        sid = start(registry, project)["sessionId"]
        first = registry.run(sid, project, "client", "eth0", 101, 60)
        self.assertEqual(first["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(first["leases"][0]["expiresAtSeconds"], 60)
        self.assertTrue(first["macTables"])
        broken = registry.link_fault(sid, project, "to-server", True)
        self.assertEqual(broken["faultedLinks"], ["to-server"])
        self.assertEqual(broken["leaseCount"], 1)
        self.assertEqual(broken["clockSeconds"], 0)
        self.assertEqual(broken["macTables"], [])
        self.assertEqual(broken["operationCount"], 2)
        self.assertEqual(project, original)
        registry.advance(sid, project, 30)
        t1 = registry.renew(sid, project, "client", "eth0", 102)
        self.assertEqual(t1["result"]["phase"], "RENEWING")
        self.assertEqual(t1["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertFalse(t1["result"]["leaseRenewed"])
        self.assertEqual(t1["result"]["ack"]["transmissions"], [])
        self.assertEqual([x["linkId"] for x in t1["result"]["request"]["transmissions"]],
                         ["to-client"])
        self.assertEqual(t1["leases"][0]["expiresAtSeconds"], 60)
        self.assertEqual(t1["leases"][0]["remainingSeconds"], 30)
        registry.advance(sid, project, 23)
        t2 = registry.renew(sid, project, "client", "eth0", 103)
        self.assertEqual(t2["result"]["phase"], "REBINDING")
        self.assertEqual(t2["result"]["request"]["ipDestination"], "255.255.255.255")
        self.assertEqual(t2["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(t2["leases"][0]["expiresAtSeconds"], 60)
        expired = registry.advance(sid, project, 7)
        self.assertEqual(expired["clockSeconds"], 60)
        self.assertEqual(expired["leaseCount"], 0)
        self.assertEqual([v["ipv4"] for v in expired["expiredLeases"]], ["192.0.2.70"])
        self.assertEqual(expired["faultedLinks"], ["to-server"])
        restored = registry.link_fault(sid, project, "to-server", False)
        self.assertEqual(restored["faultedLinks"], [])
        self.assertEqual(restored["macTables"], [])
        allocated = registry.run(sid, project, "client-2", "eth0", 104, 60)
        self.assertEqual(allocated["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(allocated["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(allocated["leases"][0]["startedAtSeconds"], 60)
        self.assertEqual(allocated["leases"][0]["expiresAtSeconds"], 120)
        self.assertEqual(project, original)
        self.assertIsNone(project["nodes"][0]["ports"][0]["ipv4"])

    def test_link_restored_before_expiry_allows_real_t2_ack(self):
        project = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, project)["sessionId"]
        reg.run(sid, project, "client", "eth0", 101, 60)
        reg.link_fault(sid, project, "to-server", True)
        reg.advance(sid, project, 30)
        missing_t1 = reg.renew(sid, project, "client", "eth0", 102)
        self.assertFalse(missing_t1["result"]["leaseRenewed"])
        reg.advance(sid, project, 23)
        reg.link_fault(sid, project, "to-server", False)
        renewed = reg.renew(sid, project, "client", "eth0", 103)
        self.assertEqual(renewed["result"]["status"], "ACK_RECEIVED")
        self.assertTrue(renewed["result"]["request"]["receivedAtServer"])
        self.assertTrue(renewed["result"]["ack"]["receivedAtClient"])
        self.assertEqual(renewed["result"]["phase"], "REBINDING")
        self.assertEqual([t["linkId"] for t in renewed["result"]["request"]["transmissions"]],
                         ["to-client", "to-server"])
        self.assertEqual(renewed["leases"][0]["startedAtSeconds"], 53)
        self.assertEqual(renewed["leases"][0]["expiresAtSeconds"], 113)
        self.assertEqual(renewed["leases"][0]["renewalCount"], 1)
        self.assertEqual(reg.advance(sid, project, 7)["leaseCount"], 1)

    def test_client_cable_fault_drops_first_hop_then_reconnect_renews(self):
        project = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, project)["sessionId"]
        reg.run(sid, project, "client", "eth0", 101, 60)
        reg.advance(sid, project, 30)
        reg.link_fault(sid, project, "to-client", True)
        result = reg.renew(sid, project, "client", "eth0", 102)
        self.assertEqual(result["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(result["result"]["request"]["transmissions"], [])
        self.assertEqual(result["leases"][0]["expiresAtSeconds"], 60)
        reg.link_fault(sid, project, "to-client", False)
        ok = reg.renew(sid, project, "client", "eth0", 103)
        self.assertEqual(ok["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(ok["leases"][0]["expiresAtSeconds"], 90)

    def test_invalid_faults_do_not_change_state_or_spend_operation(self):
        project = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, project)["sessionId"]
        reg.run(sid, project, "client", "eth0", 101, 60)
        before = reg._get(sid).state()
        changed = copy.deepcopy(project)
        changed["links"][0]["enabled"] = False
        for link_id, disabled, snapshot in (
            ("no-such-link", True, project), ("to-server", "true", project),
            ("to-server", 1, project), ("to-server", None, project),
            ("to-server", False, project), ("to-server", True, changed),
            (None, True, project),
        ):
            with self.subTest(link=link_id, disabled=disabled), self.assertRaises(
                    ProjectValidationError):
                reg.link_fault(sid, snapshot, link_id, disabled)
            self.assertEqual(reg._get(sid).state(), before)
        disabled_original = copy.deepcopy(project)
        disabled_original["links"][1]["enabled"] = False
        second = start(reg, disabled_original)["sessionId"]
        with self.assertRaisesRegex(ProjectValidationError, "not active"):
            reg.link_fault(second, disabled_original, "to-server", True)
        self.assertEqual(reg._get(second).state()["faultedLinks"], [])
        self.assertEqual(reg._get(second).state()["operationCount"], 0)
        reg.link_fault(sid, project, "to-server", True)
        frozen = reg._get(sid).state()
        with self.assertRaisesRegex(ProjectValidationError, "already active"):
            reg.link_fault(sid, project, "to-server", True)
        self.assertEqual(reg._get(sid).state(), frozen)
        reg.link_fault(sid, project, "to-server", False)
        self.assertEqual(reg._get(sid).state()["faultedLinks"], [])

    def test_faults_isolated_between_sessions_and_reset_rebuilds_fabric(self):
        project = clients()
        reg = DhcpSessionRegistry()
        a = start(reg, project)["sessionId"]
        b = start(reg, project)["sessionId"]
        reg.link_fault(a, project, "to-server", True)
        failed = reg.run(a, project, "client", "eth0", 101, 60)
        self.assertEqual(failed["result"]["status"], "DISCOVER_NOT_RECEIVED")
        self.assertEqual(failed["leaseCount"], 0)
        successful = reg.run(b, project, "client", "eth0", 102, 60)
        self.assertEqual(successful["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(successful["leaseCount"], 1)
        self.assertEqual(successful["faultedLinks"], [])
        clear = reg.reset(a, project)
        self.assertEqual(clear["faultedLinks"], [])
        self.assertEqual(clear["clockSeconds"], 0)
        self.assertEqual(clear["operationCount"], 0)
        self.assertEqual(clear["macTables"], [])
        self.assertEqual(reg.run(a, project, "client", "eth0", 103, 60)
                         ["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(reg._get(b).state()["leaseCount"], 1)

    def test_fault_operation_limit(self):
        project = clients()
        reg = DhcpSessionRegistry()
        sid = start(reg, project)["sessionId"]
        lab = reg._get(sid)
        lab.operation_count = 256
        frozen = lab.state()
        with self.assertRaisesRegex(ProjectValidationError, "operation limit"):
            reg.link_fault(sid, project, "to-server", True)
        self.assertEqual(lab.state(), frozen)


class CableFaultHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = ProjectStore(self.root)
        self.server = LabHTTPServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def post(self, path, payload):
        request = Request(self.url + path, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as reply:
                return reply.status, json.loads(reply.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_http_faulted_renewal_expiration_and_real_file_bytes(self):
        project = clients()
        self.store.save("baseline", project)
        file = self.root / "baseline.yadilab"
        baseline = file.read_bytes()
        code, started = self.post("/api/dhcp/session/start", {
            "project": project, "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"})
        self.assertEqual(code, 200)
        sid = started["sessionId"]
        initial = {"project": project, "sessionId": sid}
        def post(path, **extras):
            return self.post("/api/dhcp/session/" + path, {**initial, **extras})
        self.assertEqual(post("run", clientNode="client", clientPort="eth0",
                              transactionId=101, leaseSeconds=60)[1]["leaseCount"], 1)
        code, down = post("link-fault", linkId="to-server", disabled=True)
        self.assertEqual(code, 200)
        self.assertEqual(down["faultedLinks"], ["to-server"])
        self.assertEqual(post("advance", seconds=30)[1]["clockSeconds"], 30)
        code, t1 = post("renew", clientNode="client", clientPort="eth0",
                        transactionId=102)
        self.assertEqual(code, 200)
        self.assertEqual(t1["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(t1["leases"][0]["expiresAtSeconds"], 60)
        self.assertEqual(post("advance", seconds=23)[1]["clockSeconds"], 53)
        code, t2 = post("renew", clientNode="client", clientPort="eth0",
                        transactionId=103)
        self.assertEqual(code, 200)
        self.assertEqual(t2["result"]["phase"], "REBINDING")
        self.assertEqual(t2["result"]["status"], "REQUEST_NOT_RECEIVED")
        self.assertEqual(post("advance", seconds=7)[1]["leaseCount"], 0)
        code, up = post("link-fault", linkId="to-server", disabled=False)
        self.assertEqual(code, 200)
        self.assertEqual(up["faultedLinks"], [])
        code, recovered = post("run", clientNode="client-2", clientPort="eth0",
                               transactionId=104, leaseSeconds=60)
        self.assertEqual(code, 200)
        self.assertEqual(recovered["result"]["status"], "ACK_RECEIVED")
        self.assertEqual(recovered["result"]["lease"]["ipv4"], "192.0.2.70")
        self.assertEqual(file.read_bytes(), baseline)
        self.assertEqual(ProjectStore(self.root).read("baseline")["project"], project)
        self.assertEqual([f.name for f in self.root.glob("*.yadilab")], ["baseline.yadilab"])

    def test_http_rejects_invalid_fault_payloads_and_modified_project(self):
        project = clients()
        code, started = self.post("/api/dhcp/session/start", {
            "project": project, "serverNode": "server", "serverPort": "eth0",
            "poolStart": "192.0.2.70", "poolEnd": "192.0.2.71"})
        self.assertEqual(code, 200)
        sid = started["sessionId"]
        valid = {"sessionId": sid, "project": project,
                 "linkId": "to-server", "disabled": True}
        changed = copy.deepcopy(project)
        changed["links"][0]["enabled"] = False
        for payload in (
            {**valid, "disabled": 1}, {**valid, "disabled": "true"},
            {**valid, "linkId": "bogus"}, {**valid, "project": changed},
            {**valid, "extra": 1}, {k:v for k,v in valid.items() if k!="linkId"},
            {**valid, "sessionId": "unknown"},
        ):
            with self.subTest(payload=str(payload)[:80]):
                code, data = self.post("/api/dhcp/session/link-fault", payload)
                self.assertEqual(code, 422)
                self.assertEqual(data["error"], "INVALID_PROJECT")
                self.assertEqual(self.server.dhcp_sessions._get(sid).state()["faultedLinks"], [])
        self.assertEqual(self.server.dhcp_sessions._get(sid).state()["operationCount"], 0)
