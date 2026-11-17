"""Real HTTP and deterministic model regression for bounded live Layer-2 sessions."""
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.simulation import MAX_OPERATIONS, MAX_SESSIONS, SimulationRegistry
from network_core.storage import ProjectStore
from test_ethernet import A, B, C
from test_vlan import trunk
from test_vlan_persistence import get_port, persisted_topology

BROADCAST = "FF:FF:FF:FF:FF:FF"


class SimulationSessionModelTests(unittest.TestCase):
    def test_same_engine_retains_mac_learning_from_arp_and_ethernet(self):
        registry = SimulationRegistry()
        p = persisted_topology()
        original = copy.deepcopy(p)
        started = registry.start(p)
        sid = started["sessionId"]
        self.assertEqual(started["operationCount"], 0)
        self.assertEqual(started["macTables"], [])
        first = registry.run(sid, p, "arp", "a", "eth0", "192.0.2.20")
        self.assertEqual(first["result"]["status"], "RESOLVED")
        self.assertEqual(first["arpTable"], {"192.0.2.20": B})
        self.assertEqual(first["operationCount"], 1)
        self.assertEqual(first["macTables"], [
            {"switchId":"s1","vlanId":10,"entries":{A:"h",B:"t"}},
            {"switchId":"s2","vlanId":10,"entries":{A:"t",B:"h"}},
        ])
        # A second ARP uses actual session cache: zero new transmissions.
        second = registry.run(sid, p, "arp", "a", "eth0", "192.0.2.20")
        self.assertEqual(second["result"]["status"], "CACHE_HIT")
        self.assertEqual(second["result"]["requestTransmissions"], [])
        self.assertEqual(second["result"]["replyTransmissions"], [])
        self.assertEqual(second["operationCount"], 2)
        frame = registry.run(sid, p, "ethernet", "a", "eth0", B)
        self.assertEqual(frame["result"]["status"], "SIMULATED")
        self.assertEqual([x["linkId"] for x in frame["result"]["transmissions"]],
                         ["la", "lt", "lb"])
        self.assertEqual([x["action"] for x in frame["result"]["switchDecisions"]],
                         ["FORWARD_UNICAST", "FORWARD_UNICAST"])
        self.assertEqual(frame["operationCount"], 3)
        self.assertEqual(frame["arpTable"], {"192.0.2.20": B})
        self.assertEqual(p, original)
        self.assertEqual(registry.stop(sid), {"status":"STOPPED"})
        with self.assertRaisesRegex(ProjectValidationError, "unknown or expired"):
            registry.run(sid, p, "arp", "a", "eth0", "192.0.2.20")

    def test_ethernet_before_arp_learns_only_real_ingress_and_no_arp(self):
        registry = SimulationRegistry()
        p = persisted_topology()
        sid = registry.start(p)["sessionId"]
        frame = registry.run(sid, p, "ethernet", "a", "eth0", BROADCAST)
        self.assertEqual(frame["operation"], "ethernet")
        self.assertEqual(frame["result"]["frame"]["etherType"], 0x88B5)
        self.assertEqual([x["linkId"] for x in frame["result"]["transmissions"]],
                         ["la", "lt", "lb"])
        self.assertEqual(frame["arpTable"], {})
        self.assertEqual(frame["macTables"], [
            {"switchId":"s1","vlanId":10,"entries":{A:"h"}},
            {"switchId":"s2","vlanId":10,"entries":{A:"t"}},
        ])
        resolved = registry.run(sid, p, "arp", "a", "eth0", "192.0.2.20")
        self.assertEqual(resolved["result"]["status"], "RESOLVED")
        self.assertEqual(resolved["arpTable"], {"192.0.2.20": B})

    def test_vlan_isolation_and_drop_do_not_invent_success(self):
        registry = SimulationRegistry()
        p = persisted_topology()
        get_port(p, "s2", "t")["vlan"] = trunk(20)
        sid = registry.start(p)["sessionId"]
        failed = registry.run(sid, p, "arp", "a", "eth0", "192.0.2.20")
        self.assertEqual(failed["result"]["status"], "NO_REPLY")
        self.assertEqual(failed["result"]["requestVlanDrops"], [
            {"switch":"s2","port":"t","reason":"TRUNK_NOT_ALLOWED","vlanId":10}
        ])
        self.assertEqual(failed["arpTable"], {})
        frame = registry.run(sid, p, "ethernet", "a", "eth0", BROADCAST)
        self.assertEqual(frame["result"]["status"], "SIMULATED")
        self.assertEqual(frame["result"]["vlanDrops"][0]["reason"], "TRUNK_NOT_ALLOWED")
        self.assertEqual(frame["result"]["endpointArrivals"], [])
        self.assertEqual(frame["arpTable"], {})

    def test_reset_clears_all_arp_and_mac_state_but_preserves_project(self):
        r = SimulationRegistry()
        p = persisted_topology()
        sid = r.start(p)["sessionId"]
        r.run(sid, p, "arp", "a", "eth0", "192.0.2.20")
        cleared = r.reset(sid, p)
        self.assertEqual(cleared["sessionId"], sid)
        self.assertEqual(cleared["operationCount"], 0)
        self.assertEqual(cleared["macTables"], [])
        again = r.run(sid, p, "arp", "a", "eth0", "192.0.2.20")
        self.assertEqual(again["result"]["status"], "RESOLVED")
        self.assertEqual(again["operationCount"], 1)

    def test_registry_isolation_between_two_clients(self):
        r = SimulationRegistry()
        p = persisted_topology()
        first = r.start(p)["sessionId"]
        second = r.start(p)["sessionId"]
        self.assertNotEqual(first, second)
        r.run(first, p, "arp", "a", "eth0", "192.0.2.20")
        clean = r.run(second, p, "ethernet", "a", "eth0", BROADCAST)
        self.assertEqual(clean["arpTable"], {})
        self.assertEqual(clean["macTables"][0]["entries"], {A:"h"})
        self.assertEqual(r.run(first,p,"arp","a","eth0","192.0.2.20")["result"]["status"],"CACHE_HIT")
        r.stop(first)
        self.assertEqual(r.run(second,p,"arp","a","eth0","192.0.2.20")["result"]["status"],"RESOLVED")

    def test_strict_unchanged_project_snapshot_prevents_stale_operation(self):
        r = SimulationRegistry()
        p = persisted_topology()
        sid = r.start(p)["sessionId"]
        changed = copy.deepcopy(p)
        get_port(changed,"s1","h")["vlan"] = {"mode":"access","vlan":20}
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            r.run(sid, changed, "arp", "a", "eth0", "192.0.2.20")
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            r.reset(sid, changed)
        unchanged = r.run(sid, p, "arp", "a", "eth0", "192.0.2.20")
        self.assertEqual(unchanged["operationCount"], 1)
        self.assertEqual(unchanged["result"]["status"], "RESOLVED")
        # No string-order sensitivity in the canonical project.
        rearranged = json.loads(json.dumps(p, sort_keys=True))
        self.assertEqual(r.run(sid, rearranged, "arp", "a", "eth0",
                               "192.0.2.20")["result"]["status"], "CACHE_HIT")

    def test_reject_bad_operation_addresses_and_missing_macs_without_count(self):
        r = SimulationRegistry()
        p = persisted_topology()
        sid = r.start(p)["sessionId"]
        for operation, source_node, source_port, target in (
            ("bogus","a","eth0","192.0.2.20"),
            ("ethernet","ghost","e",B),
            ("ethernet","a","eth0","invalid"),
            ("arp","a","eth0","not-ip"),
            ("arp","a","eth0","198.51.100.1"),
        ):
            with self.subTest(operation=operation,target=target), self.assertRaises(ProjectValidationError):
                r.run(sid,p,operation,source_node,source_port,target)
        self.assertEqual(r.reset(sid,p)["operationCount"],0)

    def test_capacity_limits_and_explicit_cleanup(self):
        r = SimulationRegistry()
        p = persisted_topology()
        ids = [r.start(p)["sessionId"] for _ in range(MAX_SESSIONS)]
        self.assertEqual(len(set(ids)), MAX_SESSIONS)
        with self.assertRaisesRegex(ProjectValidationError, "too many active"):
            r.start(p)
        r.stop(ids.pop())
        self.assertTrue(r.start(p)["sessionId"])
        with self.assertRaisesRegex(ProjectValidationError, "unknown or expired"):
            r.stop("not-an-id")

    def test_operation_limit_refuses_before_extra_frame_without_fake_success(self):
        r=SimulationRegistry()
        p=persisted_topology()
        sid=r.start(p)["sessionId"]
        for _ in range(MAX_OPERATIONS):
            result=r.run(sid,p,"arp","a","eth0","192.0.2.20")
        self.assertEqual(result["operationCount"],MAX_OPERATIONS)
        with self.assertRaisesRegex(ProjectValidationError,"operation limit"):
            r.run(sid,p,"ethernet","a","eth0",B)
        self.assertEqual(r.reset(sid,p)["operationCount"],0)
        self.assertEqual(r.run(sid,p,"arp","a","eth0","192.0.2.20")["result"]["status"],"RESOLVED")


class SimulationSessionHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)
        self.server = LabHTTPServer(("127.0.0.1",0), ProjectStore(self.dir))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)
        self.temp.cleanup()

    def request(self, path, payload):
        req=Request(self.base+path,data=json.dumps(payload).encode(),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=7) as response:
                return response.status,json.loads(response.read())
        except HTTPError as error:
            return error.code,json.loads(error.read())

    def test_real_post_start_multiple_ops_reset_stop_no_disk_mutations(self):
        p=persisted_topology()
        saved=self.server.store.save("lab",p)
        raw=(self.dir/"lab.yadilab").read_bytes()
        code,start=self.request("/api/simulation/start",{"project":p})
        self.assertEqual(code,200)
        sid=start["sessionId"]
        self.assertTrue(start["ephemeral"])
        self.assertEqual(start["macTables"],[])
        def run(op,target):
            return self.request("/api/simulation/run",{
                "project":p,"sessionId":sid,"operation":op,
                "sourceNode":"a","sourcePort":"eth0","target":target})
        code,first=run("arp","192.0.2.20")
        self.assertEqual(code,200)
        self.assertEqual(first["result"]["status"],"RESOLVED")
        code,second=run("arp","192.0.2.20")
        self.assertEqual(second["result"]["status"],"CACHE_HIT")
        code,third=run("ethernet",B)
        self.assertEqual(third["result"]["status"],"SIMULATED")
        self.assertEqual(third["operationCount"],3)
        self.assertEqual(third["arpTable"],{"192.0.2.20":B})
        code,cleared=self.request("/api/simulation/reset",{"sessionId":sid,"project":p})
        self.assertEqual(code,200)
        self.assertEqual(cleared["operationCount"],0)
        self.assertEqual(cleared["macTables"],[])
        code,fresh=run("arp","192.0.2.20")
        self.assertEqual(fresh["result"]["status"],"RESOLVED")
        code,stopped=self.request("/api/simulation/stop",{"sessionId":sid})
        self.assertEqual(code,200)
        self.assertEqual(stopped,{"status":"STOPPED"})
        self.assertEqual(run("arp","192.0.2.20")[0],422)
        self.assertEqual(raw,(self.dir/"lab.yadilab").read_bytes())
        self.assertEqual(saved["sha256"],hashlib.sha256(raw).hexdigest())

    def test_mismatched_project_and_unknown_id_rejected_over_http(self):
        p=persisted_topology()
        sid=self.request("/api/simulation/start",{"project":p})[1]["sessionId"]
        changed=copy.deepcopy(p)
        changed["links"][0]["enabled"]=False
        code,error=self.request("/api/simulation/run",{
            "sessionId":sid,"project":changed,"operation":"arp",
            "sourceNode":"a","sourcePort":"eth0","target":"192.0.2.20"})
        self.assertEqual(code,422)
        self.assertIn("project changed",error["message"])
        code,error=self.request("/api/simulation/reset",{"sessionId":sid,"project":changed})
        self.assertEqual(code,422)
        self.assertIn("project changed",error["message"])
        self.assertEqual(self.request("/api/simulation/run",{
            "sessionId":"unknown","project":p,"operation":"arp",
            "sourceNode":"a","sourcePort":"eth0","target":"192.0.2.20"})[0],422)
        self.assertEqual(list(self.dir.glob("*.yadilab")),[])

    def test_invalid_shapes_never_mutate_registry(self):
        p=persisted_topology()
        bad=[
            ("/api/simulation/start",{"project":p,"file":"x"}),
            ("/api/simulation/start",{}),
            ("/api/simulation/reset",{}),
            ("/api/simulation/stop",{"sessionId":"x","extra":1}),
            ("/api/simulation/run",{"project":p}),
            ("/api/simulation/run",{"sessionId":[],"project":p,"operation":"arp",
                                      "sourceNode":"a","sourcePort":"eth0","target":"192.0.2.20"}),
        ]
        for path,payload in bad:
            with self.subTest(path=path,payload=str(payload)[:50]):
                code,result=self.request(path,payload)
                self.assertEqual(code,422)
                self.assertEqual(result["error"],"INVALID_PROJECT")
        self.assertEqual(list(self.dir.glob("*.yadilab")),[])

    def test_server_restart_loses_sessions_not_persisted_documentation(self):
        p=persisted_topology()
        sid=self.request("/api/simulation/start",{"project":p})[1]["sessionId"]
        self.server.store.save("saved",p)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)
        self.server = LabHTTPServer(("127.0.0.1",0),ProjectStore(self.dir))
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_port}"
        code,error=self.request("/api/simulation/reset",{"sessionId":sid,"project":p})
        self.assertEqual(code,422)
        self.assertIn("unknown or expired",error["message"])
        self.assertEqual(self.server.store.read("saved")["project"],p)


if __name__=="__main__":
    unittest.main()
