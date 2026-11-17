"""Explicit schema 1.3 IPv4 static routes and strict longest-prefix resolution."""
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
from network_core.routing import ConnectedRoutingTable
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_connected_routing import routing_lab


def static_lab():
    p = routing_lab()
    p["schemaVersion"] = "1.3"
    p["nodes"][0]["staticRoutes"] = [
        {"id":"route-a", "destination":"203.0.113.0/24",
         "nextHop":"10.1.0.2","outPort":"wide"},
        {"id":"route-default", "destination":"0.0.0.0/0",
         "nextHop":"10.1.0.3","outPort":"wide"},
    ]
    return p


class StaticRouteModelTests(unittest.TestCase):
    def test_version_13_explicit_route_roundtrip_and_no_unintended_fields(self):
        p=static_lab()
        original=copy.deepcopy(p)
        validated=validate_project(p)
        self.assertEqual(validated,original)
        self.assertEqual(p,original)
        self.assertNotIn("staticRoutes",validated["nodes"][1])
        self.assertNotIn("staticRoutes",validated["nodes"][2])
        self.assertEqual([v["id"] for v in validated["nodes"][0]["staticRoutes"]],
                         ["route-a","route-default"])

    def test_old_schemas_reject_static_routes_instead_of_discarding(self):
        for version in ("1.0","1.1","1.2"):
            with self.subTest(version=version):
                p=static_lab()
                p["schemaVersion"]=version
                with self.assertRaisesRegex(ProjectValidationError,"unsupported fields"):
                    validate_project(p)
                p["nodes"][0].pop("staticRoutes")
                self.assertEqual(validate_project(p)["schemaVersion"],version)

    def test_longest_prefix_static_and_connected(self):
        p=static_lab()
        table=ConnectedRoutingTable(p,"r")
        self.assertEqual(table.lookup("203.0.113.88")["selectedRoute"],
                         {"routeId":"route-a","destination":"203.0.113.0/24",
                          "type":"STATIC","outInterface":{"node":"r","port":"wide"},
                          "sourceIpv4":"10.1.0.1","nextHop":"10.1.0.2"})
        self.assertEqual(table.lookup("8.8.8.8")["selectedRoute"]["routeId"],
                         "route-default")
        self.assertEqual(table.lookup("10.20.30.8")["selectedRoute"]["type"],
                         "CONNECTED")
        self.assertEqual(table.lookup("10.20.30.8")["selectedRoute"]["destination"],
                         "10.20.30.0/24")
        p["nodes"][0]["staticRoutes"].append(
            {"id":"route-specific","destination":"10.20.30.128/25",
             "nextHop":"10.1.0.2","outPort":"wide"})
        result=ConnectedRoutingTable(p,"r").lookup("10.20.30.200")
        self.assertEqual(result["selectedRoute"]["routeId"],"route-specific")
        self.assertEqual(result["selectedRoute"]["type"],"STATIC")
        self.assertEqual(result["selectedRoute"]["destination"],"10.20.30.128/25")

    def test_equally_specific_static_routes_not_chosen_by_order(self):
        p=static_lab()
        p["nodes"][0]["staticRoutes"].append(
            {"id":"route-b","destination":"203.0.113.0/24",
             "nextHop":"10.20.0.2","outPort":"middle"})
        result=ConnectedRoutingTable(p,"r").lookup("203.0.113.8")
        self.assertEqual(result["status"],"AMBIGUOUS")
        self.assertIsNone(result["selectedRoute"])
        self.assertEqual({r["routeId"] for r in result["candidates"]},
                         {"route-a","route-b"})
        p["nodes"][0]["staticRoutes"].reverse()
        self.assertEqual(ConnectedRoutingTable(p,"r").lookup("203.0.113.8")["status"],
                         "AMBIGUOUS")

    def test_equal_prefix_connected_and_static_also_ambiguous(self):
        p=static_lab()
        p["nodes"][0]["staticRoutes"].append(
            {"id":"same","destination":"10.20.0.0/16",
             "nextHop":"10.1.0.2","outPort":"wide"})
        result=ConnectedRoutingTable(p,"r").lookup("10.20.40.5")
        self.assertEqual(result["status"],"AMBIGUOUS")
        self.assertEqual({r["type"] for r in result["candidates"]},
                         {"CONNECTED","STATIC"})
        self.assertIsNone(result["selectedRoute"])

    def test_disabled_output_port_suppresses_route_without_erasing_source(self):
        p=static_lab()
        saved=copy.deepcopy(p)
        p["nodes"][0]["ports"][0]["enabled"]=False
        table=ConnectedRoutingTable(p,"r")
        self.assertEqual(table.lookup("203.0.113.33")["status"],"NO_ROUTE")
        self.assertEqual(table.lookup("8.8.8.8")["status"],"NO_ROUTE")
        self.assertEqual(len(table.routes()),2)
        self.assertEqual(validate_project(p)["nodes"][0]["staticRoutes"],
                         saved["nodes"][0]["staticRoutes"])
        p["nodes"][0]["ports"][0]["enabled"]=True
        self.assertEqual(ConnectedRoutingTable(p,"r").lookup("203.0.113.33")["status"],
                         "MATCH")

    def test_unplugged_cable_is_not_a_route_or_a_reachability_result(self):
        p=static_lab()
        p["links"]=[]
        result=ConnectedRoutingTable(p,"r").lookup("203.0.113.10")
        self.assertEqual(result["status"],"MATCH")
        self.assertEqual(result["selectedRoute"]["nextHop"],"10.1.0.2")
        self.assertIn("not resolved",result["meaning"])
        self.assertNotIn("transmissions",result)
        self.assertNotIn("arpTable",result)
        self.assertEqual(p["links"],[])

    def test_onlink_next_hop_checked_without_resolving_it(self):
        p=static_lab()
        route=p["nodes"][0]["staticRoutes"][0]
        for address in ("10.1.0.1","172.16.0.1","10.255.255.255",
                        "10.0.0.0","0.0.0.0","255.255.255.255",
                        "224.1.1.1","2001:db8::1","bad-ip",42,None,True):
            with self.subTest(nextHop=address):
                case=copy.deepcopy(p)
                case["nodes"][0]["staticRoutes"][0]["nextHop"]=address
                with self.assertRaises(ProjectValidationError):
                    validate_project(case)
        self.assertEqual(route["nextHop"],"10.1.0.2")

    def test_strict_prefix_and_route_identity_validation(self):
        for field,value in (
            ("destination","192.0.2.10/24"), # host bits not a network prefix
            ("destination","2001:db8::/32"),
            ("destination","bad"),
            ("destination","192.0.2.0/33"),
            ("destination",None),
            ("outPort","missing"),
            ("outPort",None),
            ("id","bad id"),
            ("id",None),
        ):
            with self.subTest(field=field,value=value):
                case=static_lab()
                case["nodes"][0]["staticRoutes"][0][field]=value
                with self.assertRaises(ProjectValidationError):
                    validate_project(case)
        p=static_lab()
        p["nodes"][0]["staticRoutes"][1]["id"]="route-a"
        with self.assertRaisesRegex(ProjectValidationError,"duplicate static route ID"):
            validate_project(p)
        p=static_lab()
        p["nodes"][0]["staticRoutes"].append({
            **p["nodes"][0]["staticRoutes"][0],"id":"route-other"})
        with self.assertRaisesRegex(ProjectValidationError,"duplicate identical"):
            validate_project(p)

    def test_bad_static_route_shape_or_switch_owner_is_rejected(self):
        for wrong in (None,{},{"id":"x"},[],"string"):
            with self.subTest(wrong=wrong):
                p=static_lab()
                p["nodes"][0]["staticRoutes"]=wrong
                with self.assertRaises(ProjectValidationError):
                    validate_project(p)
        p=static_lab()
        p["nodes"][0]["staticRoutes"][0]["unknown"]="not allowed"
        with self.assertRaisesRegex(ProjectValidationError,"unsupported fields"):
            validate_project(p)
        p=static_lab()
        p["nodes"][2]["staticRoutes"]=[]
        with self.assertRaisesRegex(ProjectValidationError,"layer-2 switch"):
            validate_project(p)
        p=static_lab()
        p["nodes"][0]["staticRoutes"][0]["outPort"]="off"
        # An enabled status is not required for declaration, but next-hop must
        # still be on the explicitly declared output subnet.
        with self.assertRaisesRegex(ProjectValidationError,"subnet"):
            validate_project(p)

    def test_port_ipv4_cannot_be_removed_while_referenced_by_static_route(self):
        p=static_lab()
        p["nodes"][0]["ports"][0]["ipv4"]=None
        with self.assertRaisesRegex(ProjectValidationError,"output interface needs"):
            validate_project(p)
        p=static_lab()
        p["nodes"][0]["ports"][0]["ipv4"]="172.16.0.1/24"
        with self.assertRaisesRegex(ProjectValidationError,"subnet"):
            validate_project(p)

    def test_same_static_route_id_can_exist_on_different_devices(self):
        p=static_lab()
        host=p["nodes"][1]
        host["staticRoutes"]=[{"id":"route-a","destination":"198.51.100.0/24",
                               "nextHop":"192.0.2.1","outPort":"eth0"}]
        self.assertEqual(len(validate_project(p)["nodes"][1]["staticRoutes"]),1)
        self.assertEqual(ConnectedRoutingTable(p,"h").lookup("198.51.100.7")
                         ["selectedRoute"]["nextHop"],"192.0.2.1")

    def test_valid_31_next_hop_and_reject_32_self_gateway(self):
        p=static_lab()
        p["nodes"][0]["ports"][0]["ipv4"]="192.0.2.10/31"
        for route in p["nodes"][0]["staticRoutes"]:
            route["nextHop"]="192.0.2.11"
        self.assertEqual(ConnectedRoutingTable(p,"r").lookup("203.0.113.7")
                         ["selectedRoute"]["nextHop"],"192.0.2.11")
        p["nodes"][0]["ports"][0]["ipv4"]="192.0.2.10/32"
        with self.assertRaisesRegex(ProjectValidationError,"subnet"):
            validate_project(p)

    def test_routes_are_copies_and_project_is_not_mutated(self):
        p=static_lab()
        original=copy.deepcopy(p)
        table=ConnectedRoutingTable(p,"r")
        records=table.routes()
        route=next(r for r in records if r["type"]=="STATIC")
        route["outInterface"]["port"]="fake"
        route["nextHop"]="192.0.2.4"
        result=table.lookup("203.0.113.10")
        result["selectedRoute"]["outInterface"]["port"]="wrong"
        self.assertEqual(table.lookup("203.0.113.10")
                         ["selectedRoute"]["outInterface"]["port"],"wide")
        self.assertEqual(p,original)


class StaticRouteStorageHTTPTests(unittest.TestCase):
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
        self.thread.join(timeout=4)
        self.temp.cleanup()

    def request(self,path,body):
        req=Request(self.base+path,data=json.dumps(body).encode(),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=7) as response:
                return response.status,json.loads(response.read())
        except HTTPError as err:
            return err.code,json.loads(err.read())

    def test_http_lpm_returns_explicit_gateway_and_out_port(self):
        p=static_lab()
        code,data=self.request("/api/routing/connected",{
            "project":p,"nodeId":"r","destinationIpv4":"203.0.113.10"})
        self.assertEqual(code,200)
        self.assertEqual(data["status"],"MATCH")
        self.assertEqual(data["selectedRoute"]["type"],"STATIC")
        self.assertEqual(data["selectedRoute"]["nextHop"],"10.1.0.2")
        self.assertEqual(data["selectedRoute"]["outInterface"],{"node":"r","port":"wide"})
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_real_atomic_save_open_old_files_and_server_restart(self):
        p=static_lab()
        old=copy.deepcopy(p)
        old["schemaVersion"]="1.2"
        del old["nodes"][0]["staticRoutes"]
        self.server.store.save("legacy",old)
        saved=self.server.store.save("routes",p)
        raw=(self.root/"routes.yadilab").read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        self.assertEqual(saved["sha256"],sha)
        self.assertEqual(json.loads(raw)["schemaVersion"],"1.3")
        self.assertEqual(json.loads(raw)["nodes"][0]["staticRoutes"],p["nodes"][0]["staticRoutes"])
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)
        self.server=LabHTTPServer(("127.0.0.1",0),ProjectStore(self.root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_port}"
        reopened=self.server.store.read("routes")
        self.assertEqual(reopened["sha256"],sha)
        self.assertEqual(reopened["project"],p)
        self.assertEqual(self.server.store.read("legacy")["project"],old)
        self.assertEqual(ConnectedRoutingTable(reopened["project"],"r")
                         .lookup("203.0.113.50")["selectedRoute"]["nextHop"],"10.1.0.2")
        self.assertEqual((self.root/"routes.yadilab").read_bytes(),raw)

    def test_failed_save_does_not_change_file(self):
        p=static_lab()
        saved=self.server.store.save("routes",p)
        raw=(self.root/"routes.yadilab").read_bytes()
        broken=copy.deepcopy(p)
        broken["nodes"][0]["staticRoutes"][0]["nextHop"]="172.16.0.1"
        with self.assertRaises(ProjectValidationError):
            self.server.store.save("routes",broken,expected_sha256=saved["sha256"])
        self.assertEqual((self.root/"routes.yadilab").read_bytes(),raw)
        code,error=self.request("/api/validate",broken)
        self.assertEqual(code,422)
        self.assertEqual(error["error"],"INVALID_PROJECT")
        self.assertEqual((self.root/"routes.yadilab").read_bytes(),raw)


if __name__=="__main__":
    unittest.main()
