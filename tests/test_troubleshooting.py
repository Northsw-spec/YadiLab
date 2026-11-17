"""Controlled link-off / link-restored troubleshooting without project mutation."""
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.icmp_ping import EchoExchange
from network_core.model import ProjectValidationError, validate_project
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from network_core.troubleshooting import compare_link_fault
from test_ethernet import link, node
from test_icmp_echo import routed_reply_lab
from test_ipv4_forwarding import lab


def compare(p=None, link_id="la", dest="203.0.113.20", ttl=5):
    return compare_link_fault(
        p if p is not None else routed_reply_lab(),
        "a", "eth0", dest, ttl, 101, 4, link_id)


class TroubleshootingTests(unittest.TestCase):
    def test_known_good_broken_restored_three_independent_echo_trials(self):
        project=routed_reply_lab()
        before=copy.deepcopy(project)
        result=compare(project)
        self.assertEqual(result["status"], "FAULT_CONFIRMED")
        self.assertTrue(result["verifiedFault"])
        self.assertTrue(result["verifiedRecovery"])
        self.assertEqual(result["baseline"]["status"],"REPLIED")
        self.assertEqual(result["faulted"]["status"],"REQUEST_FAILED")
        self.assertEqual(result["faulted"]["request"]["status"],"ARP_FAILED")
        self.assertEqual(result["faulted"]["request"]["steps"][0]["arp"]["status"],"NO_ACTIVE_LINK")
        self.assertEqual(result["restored"]["status"],"REPLIED")
        self.assertEqual(result["repair"],{
            "action":"RE_ENABLE_LINK","linkId":"la",
            "expectedEnabled":True,"scope":"PREVIEW_ONLY"})
        self.assertEqual(result["fault"],{
            "type":"LINK_DISABLED","linkId":"la",
            "fromEnabled":True,"toEnabled":False})
        self.assertIn("la",result["observedLinkIds"]["baseline"])
        self.assertIn("la",result["observedLinkIds"]["restored"])
        self.assertNotIn("la",result["observedLinkIds"]["faulted"])
        self.assertFalse(result["projectChanged"])
        self.assertTrue(result["ephemeral"])
        self.assertEqual(project,before)
        self.assertTrue(next(l for l in project["links"] if l["id"]=="la")["enabled"])

    def test_specific_far_end_link_and_vlan_trunk_do_fail_when_disconnected(self):
        for lid in ("lr1","lr2","lb"):
            with self.subTest(lid=lid):
                p=routed_reply_lab()
                result=compare(p,lid)
                self.assertEqual(result["status"],"FAULT_CONFIRMED")
                self.assertEqual(result["fault"]["linkId"],lid)
                self.assertEqual(result["baseline"]["status"],"REPLIED")
                self.assertEqual(result["restored"]["status"],"REPLIED")
                self.assertNotEqual(result["faulted"]["status"],"REPLIED")
                self.assertIn(lid,result["observedLinkIds"]["baseline"])
                self.assertIn(lid,result["observedLinkIds"]["restored"])
                self.assertTrue(next(l for l in p["links"] if l["id"]==lid)["enabled"])

    def test_unrelated_link_fails_to_prove_problem(self):
        p=routed_reply_lab()
        p["nodes"].extend([node("x","host",["p"]),node("y","host",["p"])])
        p["links"].append(link("unused","x","p","y","p"))
        source=copy.deepcopy(p)
        result=compare(p,"unused")
        self.assertEqual(result["status"],"NO_OBSERVED_IMPACT")
        self.assertFalse(result["verifiedFault"])
        self.assertFalse(result["verifiedRecovery"])
        self.assertEqual(result["faulted"]["status"],"REPLIED")
        self.assertEqual(result["restored"]["status"],"REPLIED")
        self.assertNotIn("unused",result["observedLinkIds"]["baseline"])
        self.assertNotIn("unused",result["observedLinkIds"]["faulted"])
        self.assertEqual(p,source)

    def test_baseline_already_broken_is_not_injected_link_root_cause(self):
        p=lab()  # forwarding works, no explicit reverse route
        result=compare(p)
        self.assertEqual(result["status"],"BASELINE_NOT_REPLIED")
        self.assertFalse(result["verifiedFault"])
        self.assertEqual(result["baseline"]["status"],"REPLY_FAILED")
        self.assertEqual(result["baseline"]["request"]["status"],"DELIVERED")
        self.assertEqual(result["baseline"]["reply"]["status"],"NO_ROUTE")
        self.assertEqual(result["restored"]["status"],"REPLY_FAILED")
        self.assertFalse(result["verifiedRecovery"])
        self.assertTrue(next(l for l in p["links"] if l["id"]=="la")["enabled"])

    def test_previously_disabled_link_is_invalid_fault_target(self):
        p=routed_reply_lab()
        p["links"][0]["enabled"]=False
        original=copy.deepcopy(p)
        with self.assertRaisesRegex(ProjectValidationError,"already disabled"):
            compare(p)
        self.assertEqual(p,original)

    def test_unknown_and_nonstring_link_fail_closed(self):
        p=routed_reply_lab()
        for wrong in ("not-a-real-link","",None,7,True,[],{}):
            with self.subTest(id=wrong),self.assertRaises(ProjectValidationError):
                compare(p,wrong)

    def test_invalid_echo_inputs_do_not_create_success(self):
        p=routed_reply_lab()
        for source,port,target,ttl in (
            ("nobody","eth0","203.0.113.20",4),
            ("a","missing","203.0.113.20",4),
            ("a","eth0","2001:db8::1",4),
            ("a","eth0","203.0.113.20",0),
            ("a","eth0","203.0.113.20",True),
            ("a","eth0","192.0.2.10",5),
        ):
            with self.subTest(source=source,port=port,target=target,ttl=ttl):
                with self.assertRaises(ProjectValidationError):
                    compare_link_fault(p,source,port,target,ttl,1,1,"la")

    def test_tracing_link_identifiers_derived_from_actual_transmissions(self):
        r=compare()
        baseline=r["observedLinkIds"]["baseline"]
        self.assertEqual(baseline,["la","lb","lr1","lr2"])
        self.assertEqual(r["observedLinkIds"]["restored"],baseline)
        self.assertEqual(r["observedLinkIds"]["faulted"],[])

    def test_legacy_schema_preservation_and_no_auto_migration(self):
        p=routed_reply_lab()
        p["schemaVersion"]="1.2"
        for n in p["nodes"]:
            n.pop("staticRoutes",None)
        # Version 1.2 remains valid with no implicit static route or upgrade.
        original=copy.deepcopy(p)
        self.assertEqual(validate_project(p)["schemaVersion"],"1.2")
        result=compare(p)
        self.assertEqual(result["status"],"BASELINE_NOT_REPLIED")
        self.assertEqual(result["baseline"]["request"]["status"],"NO_ROUTE")
        self.assertEqual(result["restored"]["request"]["status"],"NO_ROUTE")
        self.assertEqual(p,original)


class TroubleshootingHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.server=LabHTTPServer(("127.0.0.1",0),ProjectStore(self.root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def body(self,p=None,link_id="la"):
        return {"project":p if p is not None else routed_reply_lab(),
                "sourceNode":"a","sourcePort":"eth0",
                "destinationIpv4":"203.0.113.20",
                "ttl":5,"identifier":101,"sequence":4,"linkId":link_id}

    def request(self,payload):
        req=Request(self.base+"/api/troubleshoot/link",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=10) as response:
                return response.status,json.loads(response.read())
        except HTTPError as error:
            return error.code,json.loads(error.read())

    def test_http_three_live_echo_traces_and_exact_link_fault(self):
        p=routed_reply_lab()
        original=copy.deepcopy(p)
        code,result=self.request(self.body(p))
        self.assertEqual(code,200)
        self.assertEqual(result["status"],"FAULT_CONFIRMED")
        self.assertEqual(result["baseline"]["status"],"REPLIED")
        self.assertEqual(result["faulted"]["request"]["status"],"ARP_FAILED")
        self.assertEqual(result["restored"]["status"],"REPLIED")
        self.assertEqual(result["repair"]["scope"],"PREVIEW_ONLY")
        self.assertEqual(p,original)
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_http_422_bad_shapes_disabled_and_unknown_link(self):
        base=self.body()
        disabled=routed_reply_lab()
        disabled["links"][0]["enabled"]=False
        cases=[
            {k:v for k,v in base.items() if k!="linkId"},
            {**base,"extra":1},
            {**base,"linkId":"nonexistent"},
            {**base,"linkId":None},
            {**base,"ttl":0},
            {**base,"identifier":True},
            {**base,"project":disabled},
            ["not","a","request"]
        ]
        for payload in cases:
            with self.subTest(payload=str(payload)[:90]):
                code,result=self.request(payload)
                self.assertEqual(code,422)
                self.assertEqual(result["error"],"INVALID_PROJECT")

    def test_http_saved_file_sha_unchanged_for_preview_and_repetitions(self):
        p=routed_reply_lab()
        saved=self.server.store.save("lab",p)
        raw=(self.root/"lab.yadilab").read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        self.assertEqual(saved["sha256"],sha)
        for _ in range(3):
            code,result=self.request(self.body(p))
            self.assertEqual(code,200)
            self.assertEqual(result["status"],"FAULT_CONFIRMED")
            self.assertEqual(result["baseline"]["request"]["steps"][0]["arp"]["status"],"RESOLVED")
        self.assertEqual((self.root/"lab.yadilab").read_bytes(),raw)
        self.assertEqual(self.server.store.read("lab")["sha256"],sha)


if __name__=="__main__":
    unittest.main()
