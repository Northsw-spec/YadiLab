"""Connected IPv4 routes: deterministic longest-prefix lookup, never packet delivery."""
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
from test_ethernet import link, node
from test_model import example


def routing_lab():
    p = blank_project("Explicit connected routes")
    router = node("r", "router", ["wide", "middle", "narrow", "off"])
    for port, address in zip(router["ports"],
                             ("10.1.0.1/8", "10.20.0.1/16",
                              "10.20.30.1/24", "198.51.100.1/24")):
        port["ipv4"] = address
    router["ports"][-1]["enabled"] = False
    host = node("h", "host", ["eth0"])
    host["ports"][0]["ipv4"] = "192.0.2.10/24"
    sw = node("sw", "switch", ["gi1", "gi2"])
    p["nodes"] = [router, host, sw]
    # A physical link is explicitly present only at the wide interface;
    # the routing table must not infer physical connectivity for others.
    p["links"] = [link("wire", "r", "wide", "sw", "gi1")]
    return p


class ConnectedRoutingTests(unittest.TestCase):
    def test_three_overlapping_prefixes_select_longest(self):
        p = routing_lab()
        original = copy.deepcopy(p)
        table = ConnectedRoutingTable(p, "r")
        self.assertEqual([r["destination"] for r in table.routes()],
                         ["10.20.30.0/24", "10.20.0.0/16", "10.0.0.0/8"])
        for dest, prefix, port in (
            ("10.20.30.200", "10.20.30.0/24", "narrow"),
            ("10.20.99.1", "10.20.0.0/16", "middle"),
            ("10.99.2.2", "10.0.0.0/8", "wide"),
        ):
            with self.subTest(dest=dest):
                result = table.lookup(dest)
                self.assertEqual(result["status"], "MATCH")
                self.assertEqual(result["selectedRoute"]["destination"], prefix)
                self.assertEqual(result["selectedRoute"]["outInterface"],
                                 {"node":"r","port":port})
                self.assertIsNone(result["selectedRoute"]["nextHop"])
                self.assertEqual(len(result["candidates"]), 1)
                self.assertIn("No packet", result["meaning"])
        self.assertEqual(p, original)

    def test_no_route_is_not_fake_ping_failure(self):
        result = ConnectedRoutingTable(routing_lab(), "r").lookup("203.0.113.5")
        self.assertEqual(result["status"], "NO_ROUTE")
        self.assertIsNone(result["selectedRoute"])
        self.assertEqual(result["candidates"], [])
        self.assertIn("No configured", result["meaning"])

    def test_equal_specificity_is_ambiguous_no_order_tie_break(self):
        p = routing_lab()
        r = next(n for n in p["nodes"] if n["id"]=="r")
        r["ports"][1]["ipv4"] = "10.20.30.2/24"
        selected = ConnectedRoutingTable(p,"r").lookup("10.20.30.50")
        self.assertEqual(selected["status"], "AMBIGUOUS")
        self.assertIsNone(selected["selectedRoute"])
        self.assertEqual([c["outInterface"]["port"] for c in selected["candidates"]],
                         ["middle","narrow"])
        self.assertEqual(len(selected["routes"]), 3)
        self.assertIn("no interface", selected["meaning"])
        # Physical wiring does not provide a route tie-breaker.
        p["links"] = [link("wire2","r","narrow","sw","gi1")]
        again = ConnectedRoutingTable(p,"r").lookup("10.20.30.50")
        self.assertEqual(again["status"], "AMBIGUOUS")

    def test_disabled_port_not_connected_route(self):
        p = routing_lab()
        self.assertEqual(ConnectedRoutingTable(p,"r").lookup("198.51.100.50")["status"],
                         "NO_ROUTE")
        p["nodes"][0]["ports"][-1]["enabled"] = True
        self.assertEqual(ConnectedRoutingTable(p,"r").lookup("198.51.100.50")["status"],
                         "MATCH")
        p["nodes"][0]["ports"][-1]["ipv4"] = None
        self.assertEqual(ConnectedRoutingTable(p,"r").lookup("198.51.100.50")["status"],
                         "NO_ROUTE")

    def test_link_fault_or_no_cable_never_inferred_as_ip_delivery(self):
        p = routing_lab()
        table = ConnectedRoutingTable(p, "r")
        matched = table.lookup("10.20.30.200")
        self.assertEqual(matched["status"], "MATCH")
        self.assertNotIn("transmissions", matched)
        self.assertNotIn("ping", matched)
        p["links"][0]["enabled"] = False
        self.assertEqual(ConnectedRoutingTable(p,"r").lookup("10.20.30.200")["status"],
                         "MATCH")
        p["links"] = []
        self.assertEqual(ConnectedRoutingTable(p,"r").lookup("10.20.30.200")["status"],
                         "MATCH")
        # A routing-table match is configured knowledge, not proof of a link.

    def test_each_node_has_own_table_no_switch_implicit_routing(self):
        p = routing_lab()
        self.assertEqual([r["destination"] for r in ConnectedRoutingTable(p,"h").routes()],
                         ["192.0.2.0/24"])
        self.assertEqual(ConnectedRoutingTable(p,"h").lookup("10.20.30.4")["status"],
                         "NO_ROUTE")
        with self.assertRaisesRegex(ProjectValidationError, "layer-2 switch"):
            ConnectedRoutingTable(p,"sw")
        with self.assertRaisesRegex(ProjectValidationError, "undeclared source"):
            ConnectedRoutingTable(p,"not-a-node")
        with self.assertRaises(ProjectValidationError):
            ConnectedRoutingTable(p,True)

    def test_ipv4_exact_host_prefix_31_and_default_prefix(self):
        p = routing_lab()
        r = p["nodes"][0]
        r["ports"][0]["ipv4"] = "0.0.0.1/0"
        r["ports"][1]["ipv4"] = "192.0.2.10/31"
        r["ports"][2]["ipv4"] = "192.0.2.13/32"
        table = ConnectedRoutingTable(p,"r")
        self.assertEqual(table.lookup("192.0.2.13")["selectedRoute"]["destination"],
                         "192.0.2.13/32")
        self.assertEqual(table.lookup("192.0.2.11")["selectedRoute"]["destination"],
                         "192.0.2.10/31")
        self.assertEqual(table.lookup("203.0.113.50")["selectedRoute"]["destination"],
                         "0.0.0.0/0")
        self.assertIsNone(table.lookup("203.0.113.50")["selectedRoute"]["nextHop"])

    def test_fails_closed_on_invalid_address_without_normalization_guess(self):
        t = ConnectedRoutingTable(routing_lab(),"r")
        for value in ("", "10.20.30.1/24", "2001:db8::1", "10.20.30",
                      "256.0.0.1", "010.20.30.1", None, 42, True, [], {}):
            with self.subTest(value=value), self.assertRaises(ProjectValidationError):
                t.lookup(value)

    def test_returned_route_objects_are_detached_from_model(self):
        p = routing_lab()
        table = ConnectedRoutingTable(p,"r")
        records = table.routes()
        records[0]["outInterface"]["port"] = "forged"
        records[0]["destination"] = "0.0.0.0/0"
        found = table.lookup("10.20.30.50")
        found["selectedRoute"]["outInterface"]["port"] = "fake"
        self.assertEqual(table.lookup("10.20.30.50")["selectedRoute"]["outInterface"]["port"],
                         "narrow")
        self.assertEqual(p["nodes"][0]["ports"][2]["ipv4"], "10.20.30.1/24")

    def test_legacy_versions_unchanged_and_round_trip(self):
        p = example()
        for version in ("1.0","1.1","1.2"):
            with self.subTest(version=version):
                p["schemaVersion"] = version
                original = copy.deepcopy(p)
                self.assertEqual(ConnectedRoutingTable(p,"pc-a").routes()[0]["destination"],
                                 "192.0.2.0/24")
                self.assertEqual(validate_project(p), original)
                self.assertEqual(p,original)

    def test_table_scales_across_many_declared_ports_without_fixed_fixture(self):
        p=blank_project("Large interface list")
        n=node("router","router",[f"p{i}" for i in range(100)])
        for i,port in enumerate(n["ports"]):
            port["ipv4"] = f"10.{i}.0.1/16"
        p["nodes"]=[n]
        table=ConnectedRoutingTable(p,"router")
        self.assertEqual(len(table.routes()),100)
        for i in (0, 17, 56, 99):
            result=table.lookup(f"10.{i}.42.77")
            self.assertEqual(result["status"],"MATCH")
            self.assertEqual(result["selectedRoute"]["outInterface"]["port"],f"p{i}")


class ConnectedRoutingHTTPTests(unittest.TestCase):
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

    def request(self,payload):
        req=Request(self.base+"/api/routing/connected",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=5) as response:
                return response.status,json.loads(response.read())
        except HTTPError as err:
            return err.code,json.loads(err.read())

    def test_real_http_most_specific_route_and_no_writes(self):
        p=routing_lab()
        original=copy.deepcopy(p)
        code,d=self.request({"project":p,"nodeId":"r","destinationIpv4":"10.20.30.5"})
        self.assertEqual(code,200)
        self.assertEqual(d["status"],"MATCH")
        self.assertEqual(d["selectedRoute"]["outInterface"],{"node":"r","port":"narrow"})
        self.assertEqual(len(d["routes"]),3)
        self.assertEqual(p,original)
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_real_http_no_route_and_ambiguous_not_success(self):
        p=routing_lab()
        self.assertEqual(self.request({"project":p,"nodeId":"r",
                                       "destinationIpv4":"203.0.113.100"})[1]["status"],
                         "NO_ROUTE")
        p["nodes"][0]["ports"][1]["ipv4"]="10.20.30.2/24"
        code,d=self.request({"project":p,"nodeId":"r","destinationIpv4":"10.20.30.5"})
        self.assertEqual(code,200)
        self.assertEqual(d["status"],"AMBIGUOUS")
        self.assertIsNone(d["selectedRoute"])
        self.assertEqual(len(d["candidates"]),2)

    def test_invalid_http_input_rejected_without_persisting(self):
        p=routing_lab()
        bad=[
            {"project":p,"nodeId":"r"},
            {"project":p,"nodeId":"r","destinationIpv4":"10.20.30.5","extra":42},
            {"project":p,"nodeId":"sw","destinationIpv4":"10.20.30.5"},
            {"project":p,"nodeId":"ghost","destinationIpv4":"10.20.30.5"},
            {"project":p,"nodeId":"r","destinationIpv4":"2001:db8::1"},
            {"project":p,"nodeId":"r","destinationIpv4":"10.20.30.5/24"},
            {"project":p,"nodeId":None,"destinationIpv4":"10.20.30.5"},
            ["not","a","query"],
        ]
        for payload in bad:
            with self.subTest(payload=str(payload)[:90]):
                code,d=self.request(payload)
                self.assertEqual(code,422)
                self.assertEqual(d["error"],"INVALID_PROJECT")
        self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_http_lookup_does_not_change_saved_bytes_or_sha(self):
        p=routing_lab()
        saved=self.server.store.save("route-lab",p)
        raw=(self.root/"route-lab.yadilab").read_bytes()
        self.assertEqual(saved["sha256"],hashlib.sha256(raw).hexdigest())
        for _ in range(3):
            code,d=self.request({"project":p,"nodeId":"r",
                                 "destinationIpv4":"10.20.30.33"})
            self.assertEqual(code,200)
            self.assertEqual(d["status"],"MATCH")
        self.assertEqual((self.root/"route-lab.yadilab").read_bytes(),raw)
        self.assertEqual(self.server.store.read("route-lab")["sha256"],saved["sha256"])


if __name__ == "__main__":
    unittest.main()
