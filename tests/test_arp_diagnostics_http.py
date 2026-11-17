"""Real loopback HTTP tests for single-shot ARP diagnostics, no simulated results."""
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from network_core.ethernet import EthernetFabric
from test_ethernet import A, B
from test_arp import network, bindings
from test_vlan_persistence import persisted_topology, get_port
from test_vlan import access, trunk


class ArpDiagnosticsHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.server = LabHTTPServer(("127.0.0.1", 0), ProjectStore(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/api/diagnostics/arp"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)
        self.temporary.cleanup()

    def request(self, document):
        raw = json.dumps(document).encode()
        req = Request(self.url, data=raw, headers={"Content-Type":"application/json"})
        try:
            with urlopen(req, timeout=7) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    @staticmethod
    def query(project, target="192.0.2.20", node="a", port="eth0"):
        return {"project": project, "sourceNode": node,
                "sourcePort": port, "targetIpv4": target}

    def test_real_http_persisted_vlan_two_switch_arp_and_learned_tables(self):
        p = persisted_topology()
        original = copy.deepcopy(p)
        code, data = self.request(self.query(p))
        self.assertEqual(code, 200)
        self.assertTrue(data["ephemeral"])
        r = data["result"]
        self.assertEqual(r["status"], "RESOLVED")
        self.assertEqual(r["resolvedMac"], B)
        self.assertEqual([x["linkId"] for x in r["requestTransmissions"]], ["la", "lt", "lb"])
        self.assertEqual([x["linkId"] for x in r["replyTransmissions"]], ["lb", "lt", "la"])
        self.assertTrue(r["requestTransmissions"][1]["tagged"])
        self.assertEqual(r["requestTransmissions"][1]["vlanId"], 10)
        self.assertEqual(data["arpTable"], {"192.0.2.20": B})
        self.assertEqual(data["macTables"], [
            {"switchId": "s1", "vlanId": 10, "entries": {A: "h", B: "t"}},
            {"switchId": "s2", "vlanId": 10, "entries": {A: "t", B: "h"}},
        ])
        self.assertEqual(p, original)
        self.assertEqual(list(self.root.glob("*.yadilab")), [])

    def test_vlan_isolation_returns_no_reply_and_real_mac_learning_only(self):
        p = persisted_topology()
        code, d = self.request(self.query(p, target="192.0.2.40"))
        self.assertEqual(code, 200)
        self.assertEqual(d["result"]["status"], "NO_REPLY")
        self.assertEqual(d["result"]["replyTransmissions"], [])
        self.assertEqual(d["arpTable"], {})
        self.assertEqual(d["macTables"], [
            {"switchId":"s1","vlanId":10,"entries":{A:"h"}},
            {"switchId":"s2","vlanId":10,"entries":{A:"t"}},
        ])
        self.assertNotIn("192.0.2.40", json.dumps(d["arpTable"]))

    def test_trunk_drop_is_reported_not_falsely_resolved(self):
        p = persisted_topology()
        get_port(p, "s2", "t")["vlan"] = trunk(20)
        code, d = self.request(self.query(p))
        self.assertEqual(code, 200)
        self.assertEqual(d["result"]["status"], "NO_REPLY")
        self.assertEqual(d["result"]["requestVlanDrops"], [{
            "switch":"s2", "port":"t", "reason":"TRUNK_NOT_ALLOWED", "vlanId":10,
        }])
        self.assertEqual(d["arpTable"], {})
        self.assertEqual(d["macTables"], [
            {"switchId":"s1","vlanId":10,"entries":{A:"h"}},
        ])

    def test_link_fault_is_not_reported_as_arp_success(self):
        p = persisted_topology()
        p["links"][1]["enabled"] = False
        code, d = self.request(self.query(p))
        self.assertEqual(code, 200)
        self.assertEqual(d["result"]["status"], "NO_REPLY")
        self.assertEqual([x["linkId"] for x in d["result"]["requestTransmissions"]], ["la"])
        self.assertEqual(d["arpTable"], {})
        p["links"][0]["enabled"] = False
        code, d = self.request(self.query(p))
        self.assertEqual(code, 200)
        self.assertEqual(d["result"]["status"], "NO_ACTIVE_LINK")
        self.assertEqual(d["macTables"], [])

    def test_each_http_request_has_new_empty_tables_without_cache_hit(self):
        p = persisted_topology()
        for _ in range(2):
            code, d = self.request(self.query(p))
            self.assertEqual(code, 200)
            self.assertEqual(d["result"]["status"], "RESOLVED")
            self.assertNotEqual(d["result"]["requestTransmissions"], [])
        self.assertEqual(list(self.root.glob("*.yadilab")), [])

    def test_legacy_without_explicit_macs_fails_not_assigns_new_identity(self):
        p = network()
        code, error = self.request(self.query(p))
        self.assertEqual(code, 422)
        self.assertIn("explicit IPv4 and MAC", error["message"])
        self.assertEqual(error["error"], "INVALID_PROJECT")
        self.assertEqual(list(self.root.glob("*.yadilab")), [])

    def test_wrong_input_fields_and_invalid_ip_are_rejected(self):
        p = persisted_topology()
        for bad in [
            {"project": p, "sourceNode": "a", "sourcePort": "eth0"},
            {**self.query(p), "filename": "unexpected"},
            self.query(p, node="ghost"),
            self.query(p, target="not-an-ip"),
            self.query(p, target="198.51.100.20"),
            self.query(p, port="ghost"),
            ["not", "a", "request"],
        ]:
            with self.subTest(bad=str(bad)[:120]):
                code, error = self.request(bad)
                self.assertEqual(code, 422)
                self.assertEqual(error["error"], "INVALID_PROJECT")
        self.assertEqual(list(self.root.glob("*.yadilab")), [])

    def test_diagnostics_never_modify_saved_project_file_or_hash(self):
        p = persisted_topology()
        first = self.server.store.save("network", p)
        raw = (self.root / "network.yadilab").read_bytes()
        self.assertEqual(first["sha256"], hashlib.sha256(raw).hexdigest())
        code, d = self.request(self.query(p))
        self.assertEqual(code, 200)
        self.assertEqual(d["result"]["status"], "RESOLVED")
        self.assertEqual((self.root / "network.yadilab").read_bytes(), raw)
        self.assertEqual(self.server.store.read("network")["sha256"], first["sha256"])

    def test_mac_snapshots_are_detached_from_learned_state(self):
        fabric = EthernetFabric(persisted_topology())
        self.assertEqual(fabric.learned_mac_tables(), [])
        fabric.inject("a", "eth0", A, "FF:FF:FF:FF:FF:FF")
        snap = fabric.learned_mac_tables()
        snap[0]["entries"].clear()
        self.assertEqual(fabric.mac_table("s1", 10), {A: "h"})
        self.assertEqual(fabric.mac_table("s2", 10), {A: "t"})

    def test_legacy_unsegmented_mac_table_has_null_vlan(self):
        p = network()
        f = EthernetFabric(p, interface_macs=bindings())
        f.inject("a", "eth0", A, "FF:FF:FF:FF:FF:FF")
        self.assertEqual(f.learned_mac_tables(), [
            {"switchId":"sw", "vlanId":None, "entries":{A:"p1"}},
        ])
        self.assertEqual(f.mac_table("sw"), {A:"p1"})


if __name__ == "__main__":
    unittest.main()
