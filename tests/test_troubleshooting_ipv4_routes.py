"""Read-only IPv4 prefix and explicit static-route troubleshooting faults."""
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.model import ProjectValidationError, validate_project
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from network_core.troubleshooting import compare_fault
from test_icmp_echo import routed_reply_lab
from test_ipv4_forwarding import getport, lab


def run(fault, project=None, target="203.0.113.20"):
    return compare_fault(
        routed_reply_lab() if project is None else project,
        "a", "eth0", target, 5, 41, 9, fault)


class IPv4RouteFaultTests(unittest.TestCase):
    def test_router_ipv4_prefix_change_real_no_route_then_restored(self):
        p = routed_reply_lab()
        original = copy.deepcopy(p)
        r = run({"type":"IPV4_PREFIX_CHANGED", "nodeId":"r",
                 "portId":"lan", "newPrefix":30}, p)
        self.assertEqual(r["status"], "FAULT_CONFIRMED")
        self.assertEqual(r["baseline"]["status"], "REPLIED")
        self.assertEqual(r["faulted"]["status"], "REQUEST_FAILED")
        self.assertEqual(r["faulted"]["request"]["status"], "NO_ROUTE")
        self.assertEqual([hop["node"] for hop in r["faulted"]["request"]["steps"]], ["a"])
        self.assertEqual(r["restored"]["status"], "REPLIED")
        self.assertEqual(r["fault"], {
            "type":"IPV4_PREFIX_CHANGED", "nodeId":"r", "portId":"lan",
            "fromIpv4":"203.0.113.1/24", "toIpv4":"203.0.113.1/30"})
        self.assertEqual(r["repair"], {
            "action":"RESTORE_IPV4", "nodeId":"r", "portId":"lan",
            "expectedIpv4":"203.0.113.1/24", "scope":"PREVIEW_ONLY"})
        self.assertTrue(r["verifiedFault"])
        self.assertTrue(r["verifiedRecovery"])
        self.assertFalse(r["projectChanged"])
        self.assertEqual(p, original)

    def test_prefix_changed_but_peer_still_on_link_no_impact(self):
        p = routed_reply_lab()
        r = run({"type":"IPV4_PREFIX_CHANGED", "nodeId":"r",
                 "portId":"lan", "newPrefix":25}, p)
        self.assertEqual(r["status"], "NO_OBSERVED_IMPACT")
        self.assertEqual([r[k]["status"] for k in ("baseline","faulted","restored")],
                         ["REPLIED","REPLIED","REPLIED"])
        self.assertFalse(r["verifiedFault"])
        self.assertFalse(r["verifiedRecovery"])

    def test_static_route_removal_disables_forward_path_not_fake_ping(self):
        p = routed_reply_lab()
        original = copy.deepcopy(p)
        r = run({"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"via-router"},p)
        self.assertEqual(r["status"],"FAULT_CONFIRMED")
        self.assertEqual(r["baseline"]["status"],"REPLIED")
        self.assertEqual(r["faulted"]["status"],"REQUEST_FAILED")
        self.assertEqual(r["faulted"]["request"]["status"],"NO_ROUTE")
        self.assertEqual(r["faulted"]["request"]["steps"],[])
        self.assertEqual(r["restored"]["status"],"REPLIED")
        self.assertEqual(r["repair"]["action"],"RESTORE_STATIC_ROUTE")
        self.assertEqual(r["repair"]["expectedRoute"],original["nodes"][0]["staticRoutes"][0])
        self.assertEqual(r["fault"]["removedRoute"],original["nodes"][0]["staticRoutes"][0])
        self.assertEqual(p,original)

    def test_static_route_removal_on_reverse_side_breaks_reply_not_request(self):
        p = routed_reply_lab()
        r = run({"type":"STATIC_ROUTE_REMOVED","nodeId":"b","routeId":"return-to-a"},p)
        self.assertEqual(r["status"],"FAULT_CONFIRMED")
        self.assertEqual(r["faulted"]["request"]["status"],"DELIVERED")
        self.assertEqual(r["faulted"]["status"],"REPLY_FAILED")
        self.assertEqual(r["faulted"]["reply"]["status"],"NO_ROUTE")
        self.assertEqual(r["restored"]["status"],"REPLIED")

    def test_static_next_hop_misconfiguration_fails_actual_arp_then_restores(self):
        p=routed_reply_lab()
        original=copy.deepcopy(p)
        r=run({"type":"STATIC_NEXT_HOP_CHANGED", "nodeId":"a",
               "routeId":"via-router","newNextHop":"192.0.2.254"},p)
        self.assertEqual(r["status"],"FAULT_CONFIRMED")
        self.assertEqual(r["faulted"]["request"]["status"],"ARP_FAILED")
        self.assertEqual(r["faulted"]["request"]["steps"][0]["arp"]["status"],"NO_REPLY")
        self.assertEqual(r["faulted"]["request"]["steps"][0]["ipv4Transmissions"],[])
        self.assertEqual(r["restored"]["status"],"REPLIED")
        self.assertEqual(r["fault"]["fromNextHop"],"192.0.2.1")
        self.assertEqual(r["fault"]["toNextHop"],"192.0.2.254")
        self.assertEqual(r["repair"], {
            "action":"RESTORE_NEXT_HOP", "nodeId":"a","routeId":"via-router",
            "expectedNextHop":"192.0.2.1","scope":"PREVIEW_ONLY"})
        self.assertEqual(p,original)

    def test_static_next_hop_but_baseline_already_broken_no_root_cause(self):
        p=lab()
        r=run({"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"via-router"},p)
        self.assertEqual(r["status"],"BASELINE_NOT_REPLIED")
        self.assertEqual(r["baseline"]["status"],"REPLY_FAILED")
        self.assertEqual(r["baseline"]["reply"]["status"],"NO_ROUTE")
        self.assertFalse(r["verifiedFault"])
        self.assertFalse(r["verifiedRecovery"])

    def test_invalid_prefix_input_rejected_without_project_mutation(self):
        p=routed_reply_lab()
        original=copy.deepcopy(p)
        failures=[
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":24},
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":0},
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":33},
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":True},
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":"30"},
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"sw-left","portId":"a","newPrefix":30},
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"missing","newPrefix":30},
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":30,"unused":1},
        ]
        for bad in failures:
            with self.subTest(bad=bad),self.assertRaises(ProjectValidationError):
                run(bad,p)
        self.assertEqual(p,original)

    def test_prefix_that_invalidates_static_route_does_not_silently_drop_route(self):
        p=routed_reply_lab()
        original=copy.deepcopy(p)
        # source a has a static route via 192.0.2.1; /30 would make it off-link.
        with self.assertRaisesRegex(ProjectValidationError,"next-hop"):
            run({"type":"IPV4_PREFIX_CHANGED", "nodeId":"a",
                 "portId":"eth0", "newPrefix":30},p)
        self.assertEqual(p,original)

    def test_invalid_routes_and_next_hops_fail_closed(self):
        p=routed_reply_lab()
        wrong=[
            {"type":"STATIC_ROUTE_REMOVED","nodeId":"r","routeId":"not-declared"},
            {"type":"STATIC_ROUTE_REMOVED","nodeId":"missing","routeId":"via-router"},
            {"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"nonexistent"},
            {"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":None},
            {"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"via-router","extra":1},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":"192.0.2.1"},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":"198.51.100.5"},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":"192.0.2.10"},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":"192.0.2.0"},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":"bad"},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":True},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":None},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":"192.0.2.254","extra":"no"},
        ]
        for bad in wrong:
            with self.subTest(bad=bad),self.assertRaises(ProjectValidationError):
                run(bad,p)

    def test_stable_route_id_order_restoration_when_many_routes(self):
        p=routed_reply_lab()
        a=next(n for n in p["nodes"] if n["id"]=="a")
        a["staticRoutes"].insert(0,{
            "id":"unrelated","destination":"198.51.100.0/24",
            "nextHop":"192.0.2.1","outPort":"eth0"})
        original=copy.deepcopy(p)
        r=run({"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"via-router"},p)
        self.assertEqual(r["status"],"FAULT_CONFIRMED")
        self.assertEqual(r["restored"]["status"],"REPLIED")
        self.assertEqual(p,original)

    def test_legacy_no_routes_rejected_as_missing_not_auto_migrated(self):
        p=routed_reply_lab()
        p["schemaVersion"]="1.2"
        for node in p["nodes"]:
            node.pop("staticRoutes",None)
        original=copy.deepcopy(p)
        self.assertEqual(validate_project(p)["schemaVersion"],"1.2")
        with self.assertRaises(ProjectValidationError):
            run({"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"via-router"},p)
        self.assertEqual(p,original)


class IPv4FaultHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.server=LabHTTPServer(("127.0.0.1",0),ProjectStore(self.root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown();self.server.server_close()
        self.thread.join(timeout=5);self.tmp.cleanup()

    def post(self,body):
        req=Request(self.base+"/api/troubleshoot/fault",
                    data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=10) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as exc:
            return exc.code,json.loads(exc.read())

    def body(self,fault,p=None):
        return {"project":p if p is not None else routed_reply_lab(),
                "sourceNode":"a","sourcePort":"eth0","destinationIpv4":"203.0.113.20",
                "ttl":5,"identifier":3,"sequence":5,"fault":fault}

    def test_http_three_new_faults_and_exact_recovery(self):
        faults=[
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":30},
            {"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"via-router"},
            {"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router",
             "newNextHop":"192.0.2.254"},
        ]
        for fault in faults:
            with self.subTest(fault=fault):
                code,d=self.post(self.body(fault))
                self.assertEqual(code,200)
                self.assertEqual(d["status"],"FAULT_CONFIRMED")
                self.assertEqual(d["baseline"]["status"],"REPLIED")
                self.assertNotEqual(d["faulted"]["status"],"REPLIED")
                self.assertEqual(d["restored"]["status"],"REPLIED")
                self.assertTrue(d["verifiedRecovery"])
                self.assertEqual(d["repair"]["scope"],"PREVIEW_ONLY")
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_http_bad_requests_are_422(self):
        base=self.body({"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"via-router"})
        bad=[
            {k:v for k,v in base.items() if k!="fault"},
            {**base,"extra":1},
            {**base,"fault":{"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"missing"}},
            {**base,"fault":{"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":True}},
            {**base,"fault":{"type":"IPV4_PREFIX_CHANGED","nodeId":"a","portId":"eth0","newPrefix":30}},
            {**base,"fault":{"type":"STATIC_NEXT_HOP_CHANGED","nodeId":"a","routeId":"via-router","newNextHop":"8.8.8.8"}},
            {**base,"ttl":0},
            ["not","a","valid","request"],
        ]
        for item in bad:
            with self.subTest(item=str(item)[:80]):
                code,reply=self.post(item)
                self.assertEqual(code,422)
                self.assertEqual(reply["error"],"INVALID_PROJECT")

    def test_http_saved_bytes_sha_not_modified(self):
        p=routed_reply_lab()
        raw_result=self.server.store.save("net",p)
        raw=(self.root/"net.yadilab").read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        self.assertEqual(raw_result["sha256"],sha)
        source=copy.deepcopy(p)
        for fault in [
            {"type":"STATIC_ROUTE_REMOVED","nodeId":"a","routeId":"via-router"},
            {"type":"IPV4_PREFIX_CHANGED","nodeId":"r","portId":"lan","newPrefix":30},
        ]:
            for _ in range(2):
                code,result=self.post(self.body(fault,p))
                self.assertEqual(code,200)
                self.assertEqual(result["status"],"FAULT_CONFIRMED")
                self.assertEqual(result["baseline"]["request"]["steps"][0]["arp"]["status"],"RESOLVED")
        self.assertEqual(p,source)
        self.assertEqual(raw,(self.root/"net.yadilab").read_bytes())
        self.assertEqual(self.server.store.read("net")["sha256"],sha)


if __name__=="__main__":
    unittest.main()
