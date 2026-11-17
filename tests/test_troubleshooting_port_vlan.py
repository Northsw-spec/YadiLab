"""Controlled port/VLAN fault injection over existing real L2/L3/ICMP engine."""
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.model import ProjectValidationError, blank_project, validate_project
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from network_core.troubleshooting import compare_fault
from test_ethernet import node, link
from test_icmp_echo import routed_reply_lab
from test_ipv4_forwarding import lab, getport


def run(fault, project=None, target="203.0.113.20", ttl=5):
    return compare_fault(
        routed_reply_lab() if project is None else project,
        "a", "eth0", target, ttl, 113, 7, fault)


def trunk_lab():
    """Two explicitly declared switches, tagged VLAN 10 and two host NICs."""
    p = blank_project("Two-switch tagged trunk")
    p["nodes"] = [
        node("a", "host", ["eth0"]),
        node("sw1", "switch", ["a", "trunk"]),
        node("sw2", "switch", ["trunk", "b"]),
        node("b", "host", ["eth0"]),
    ]
    p["links"] = [
        link("from-a", "a", "eth0", "sw1", "a"),
        link("between-switches", "sw1", "trunk", "sw2", "trunk"),
        link("to-b", "sw2", "b", "b", "eth0"),
    ]
    getport(p, "a", "eth0").update(ipv4="192.0.2.10/24", mac="02:00:00:00:00:0A")
    getport(p, "b", "eth0").update(ipv4="192.0.2.20/24", mac="02:00:00:00:00:0B")
    getport(p, "sw1", "a")["vlan"] = {"mode": "access", "vlan": 10}
    getport(p, "sw2", "b")["vlan"] = {"mode": "access", "vlan": 10}
    for switch in ("sw1", "sw2"):
        getport(p, switch, "trunk")["vlan"] = {
            "mode": "trunk", "allowedVlans": [10, 20]}
    return validate_project(p)


class PortAndVlanFaultTests(unittest.TestCase):
    def test_host_and_switch_port_faults_prove_failure_then_restore(self):
        for device, port in (("sw-left", "a"),
                             ("r", "lan"), ("sw-right", "b"), ("b", "eth0")):
            with self.subTest(port=(device, port)):
                p = routed_reply_lab()
                original = copy.deepcopy(p)
                r = run({"type": "PORT_DISABLED", "nodeId": device, "portId": port}, p)
                self.assertEqual(r["status"], "FAULT_CONFIRMED")
                self.assertEqual(r["baseline"]["status"], "REPLIED")
                self.assertNotEqual(r["faulted"]["status"], "REPLIED")
                self.assertEqual(r["restored"]["status"], "REPLIED")
                self.assertEqual(r["fault"], {
                    "type": "PORT_DISABLED", "nodeId": device, "portId": port,
                    "fromEnabled": True, "toEnabled": False})
                self.assertEqual(r["repair"], {
                    "action": "RE_ENABLE_PORT", "nodeId": device, "portId": port,
                    "expectedEnabled": True, "scope": "PREVIEW_ONLY"})
                self.assertTrue(r["verifiedRecovery"])
                self.assertEqual(p, original)

    def test_source_port_shutdown_is_rejected_instead_of_fabricated_echo(self):
        p = routed_reply_lab()
        with self.assertRaisesRegex(ProjectValidationError, "source-port shutdown"):
            run({"type": "PORT_DISABLED", "nodeId": "a", "portId": "eth0"}, p)

    def test_access_vlan_mismatch_real_arp_failure_and_rollback(self):
        p = routed_reply_lab()
        before = copy.deepcopy(p)
        r = run({"type": "ACCESS_VLAN_CHANGED",
                 "nodeId": "sw-left", "portId": "a", "newVlan": 20}, p)
        self.assertEqual(r["status"], "FAULT_CONFIRMED")
        self.assertEqual(r["baseline"]["status"], "REPLIED")
        self.assertEqual(r["faulted"]["status"], "REQUEST_FAILED")
        self.assertEqual(r["faulted"]["request"]["status"], "ARP_FAILED")
        self.assertEqual(r["faulted"]["request"]["steps"][0]["arp"]["status"], "NO_REPLY")
        self.assertEqual(r["restored"]["status"], "REPLIED")
        self.assertEqual(r["repair"]["action"], "RESTORE_VLAN_CONFIG")
        self.assertEqual(r["repair"]["expectedVlan"], {"mode": "access", "vlan": 10})
        self.assertEqual(r["fault"]["fromVlan"], 10)
        self.assertEqual(r["fault"]["toVlan"], 20)
        self.assertEqual(p, before)

    def test_real_tagged_trunk_blocking_only_vlan_10_breaks_delivery(self):
        p = trunk_lab()
        original = copy.deepcopy(p)
        r = run({"type": "TRUNK_VLAN_BLOCKED",
                 "nodeId": "sw1", "portId": "trunk", "blockedVlan": 10},
                p, "192.0.2.20", 3)
        self.assertEqual(r["baseline"]["status"], "REPLIED")
        self.assertEqual(r["faulted"]["status"], "REQUEST_FAILED")
        self.assertEqual(r["faulted"]["request"]["status"], "ARP_FAILED")
        self.assertEqual(r["status"], "FAULT_CONFIRMED")
        self.assertEqual(r["restored"]["status"], "REPLIED")
        self.assertEqual(r["fault"]["remainingAllowedVlans"], [20])
        self.assertEqual(r["repair"]["expectedVlan"],
                         {"mode": "trunk", "allowedVlans": [10, 20]})
        self.assertIn("between-switches", r["observedLinkIds"]["baseline"])
        self.assertIn("between-switches", r["observedLinkIds"]["restored"])
        self.assertEqual(p, original)

    def test_unrelated_trunk_vlan_block_has_no_observed_impact(self):
        p = trunk_lab()
        r = run({"type": "TRUNK_VLAN_BLOCKED", "nodeId": "sw1",
                 "portId": "trunk", "blockedVlan": 20}, p, "192.0.2.20")
        self.assertEqual(r["status"], "NO_OBSERVED_IMPACT")
        self.assertFalse(r["verifiedFault"])
        self.assertFalse(r["verifiedRecovery"])
        self.assertEqual(r["baseline"]["status"], "REPLIED")
        self.assertEqual(r["faulted"]["status"], "REPLIED")
        self.assertEqual(r["restored"]["status"], "REPLIED")

    def test_already_broken_reference_never_claims_new_port_root_cause(self):
        p = lab()
        r = run({"type": "PORT_DISABLED", "nodeId": "sw-left", "portId": "a"}, p)
        self.assertEqual(r["status"], "BASELINE_NOT_REPLIED")
        self.assertEqual(r["baseline"]["status"], "REPLY_FAILED")
        self.assertFalse(r["verifiedRecovery"])

    def test_all_fault_options_require_explicit_enabled_correct_ports(self):
        p = routed_reply_lab()
        wrong = [
            {"type": "PORT_DISABLED", "nodeId": "missing", "portId": "a"},
            {"type": "PORT_DISABLED", "nodeId": "r", "portId": "missing"},
            {"type": "PORT_DISABLED", "nodeId": None, "portId": "wan"},
            {"type": "ACCESS_VLAN_CHANGED", "nodeId": "a", "portId": "eth0", "newVlan": 20},
            {"type": "TRUNK_VLAN_BLOCKED", "nodeId": "sw-left", "portId": "a", "blockedVlan": 10},
            {"type": "ACCESS_VLAN_CHANGED", "nodeId": "sw-left", "portId": "a", "newVlan": 10},
            {"type": "ACCESS_VLAN_CHANGED", "nodeId": "sw-left", "portId": "a", "newVlan": 0},
            {"type": "ACCESS_VLAN_CHANGED", "nodeId": "sw-left", "portId": "a", "newVlan": True},
            {"type": "ACCESS_VLAN_CHANGED", "nodeId": "sw-left", "portId": "a", "newVlan": "20"},
            {"type": "PORT_DISABLED", "nodeId": "a", "portId": "eth0", "extra": 1},
            {"type": "LINK_DISABLED", "linkId": "la", "extra": "ignored"},
            {"type": "UNKNOWN", "nodeId": "a", "portId": "eth0"},
            {}, None, [], "wrong",
        ]
        for fault in wrong:
            with self.subTest(fault=fault), self.assertRaises(ProjectValidationError):
                run(fault, p)
        getport(p, "a", "eth0")["enabled"] = False
        with self.assertRaisesRegex(ProjectValidationError, "already disabled"):
            run({"type": "PORT_DISABLED", "nodeId": "a", "portId": "eth0"}, p)

    def test_trunk_wrong_vlan_and_last_allowed_vlan_rejected(self):
        p = trunk_lab()
        for vlan in (0, 4095, True, "10", 30):
            with self.subTest(vlan=vlan), self.assertRaises(ProjectValidationError):
                run({"type": "TRUNK_VLAN_BLOCKED", "nodeId": "sw1",
                     "portId": "trunk", "blockedVlan": vlan}, p, "192.0.2.20")
        getport(p, "sw1", "trunk")["vlan"]["allowedVlans"] = [10]
        with self.assertRaisesRegex(ProjectValidationError, "last allowed"):
            run({"type": "TRUNK_VLAN_BLOCKED", "nodeId": "sw1",
                 "portId": "trunk", "blockedVlan": 10}, p, "192.0.2.20")

    def test_versioned_data_not_migrated_and_legacy_link_api_unchanged(self):
        p = routed_reply_lab()
        before = copy.deepcopy(p)
        r = run({"type": "LINK_DISABLED", "linkId": "la"}, p)
        self.assertEqual(r["status"], "FAULT_CONFIRMED")
        self.assertEqual(r["repair"]["action"], "RE_ENABLE_LINK")
        self.assertEqual(p, before)


class PortVlanHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.server = LabHTTPServer(("127.0.0.1", 0), ProjectStore(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def request(self, body):
        req = Request(self.base+"/api/troubleshoot/fault",
                      data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
        try:
            with urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read())
        except HTTPError as err:
            return err.code, json.loads(err.read())

    def body(self, fault, project=None, target="203.0.113.20"):
        return {
            "project": routed_reply_lab() if project is None else project,
            "sourceNode": "a", "sourcePort": "eth0",
            "destinationIpv4": target, "ttl": 5, "identifier": 113,
            "sequence": 7, "fault": fault}

    def test_real_http_port_and_access_vlan_recovery_and_trunk(self):
        cases = [
            self.body({"type":"PORT_DISABLED", "nodeId":"sw-left", "portId":"a"}),
            self.body({"type":"ACCESS_VLAN_CHANGED", "nodeId":"sw-left",
                       "portId":"a", "newVlan":20}),
            self.body({"type":"TRUNK_VLAN_BLOCKED", "nodeId":"sw1",
                       "portId":"trunk", "blockedVlan":10}, trunk_lab(), "192.0.2.20"),
        ]
        for request in cases:
            with self.subTest(fault=request["fault"]):
                code, result = self.request(request)
                self.assertEqual(code, 200)
                self.assertEqual(result["status"], "FAULT_CONFIRMED")
                self.assertEqual(result["baseline"]["status"], "REPLIED")
                self.assertNotEqual(result["faulted"]["status"], "REPLIED")
                self.assertEqual(result["restored"]["status"], "REPLIED")
                self.assertEqual(result["repair"]["scope"], "PREVIEW_ONLY")
                self.assertTrue(result["verifiedRecovery"])
        self.assertEqual(list(self.root.glob("*.yadilab")), [])

    def test_real_http_negative_requests_return_422(self):
        base = self.body({"type":"PORT_DISABLED", "nodeId":"a", "portId":"eth0"})
        for bad in (
            {k:v for k,v in base.items() if k != "fault"},
            {**base, "unknown": True},
            {**base, "fault": {"type":"PORT_DISABLED", "nodeId":"a", "portId":"wrong"}},
            {**base, "fault": {"type":"PORT_DISABLED", "nodeId":"a", "portId":"eth0"}},
            {**base, "fault": {"type":"ACCESS_VLAN_CHANGED",
                               "nodeId":"sw-left", "portId":"a", "newVlan":10}},
            {**base, "fault": {"type":"TRUNK_VLAN_BLOCKED",
                               "nodeId":"sw-left", "portId":"a", "blockedVlan":10}},
            {**base, "ttl": True},
            {**base, "destinationIpv4":"2001:db8::1"},
            ["not", "an", "HTTP", "request"],
        ):
            with self.subTest(body=str(bad)[:100]):
                code, result = self.request(bad)
                self.assertEqual(code, 422)
                self.assertEqual(result["error"], "INVALID_PROJECT")
        self.assertEqual(list(self.root.glob("*.yadilab")), [])

    def test_http_snapshot_and_file_sha_unchanged_across_repeated_faults(self):
        p = routed_reply_lab()
        raw_saved = self.server.store.save("baseline", p)
        raw = (self.root/"baseline.yadilab").read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        self.assertEqual(raw_saved["sha256"], sha)
        original = copy.deepcopy(p)
        for fault in (
            {"type":"PORT_DISABLED", "nodeId":"sw-left", "portId":"a"},
            {"type":"ACCESS_VLAN_CHANGED", "nodeId":"sw-left",
             "portId":"a", "newVlan":20},
        ):
            for _ in range(2):
                code, response = self.request(self.body(fault, p))
                self.assertEqual(code, 200)
                self.assertEqual(response["status"], "FAULT_CONFIRMED")
                self.assertEqual(response["baseline"]["request"]["steps"][0]["arp"]["status"],"RESOLVED")
        self.assertEqual((self.root/"baseline.yadilab").read_bytes(), raw)
        self.assertEqual(self.server.store.read("baseline")["sha256"], sha)
        self.assertEqual(p, original)


if __name__=="__main__":
    unittest.main()
