"""Hidden routed-ping fault training using actual Echo/IPv4/ARP/L2 proofs."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.icmp_investigation import (
    IcmpInvestigation, IcmpInvestigationRegistry, KINDS, _candidates,
)
from network_core.icmp_ping import EchoExchange
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_icmp_echo import routed_reply_lab


def scenario(kind):
    return IcmpInvestigation(
        routed_reply_lab(), "a", "eth0", "203.0.113.20", 5, _test_kind=kind)


class IcmpInvestigationTests(unittest.TestCase):
    def test_each_hidden_cause_proven_by_failure_and_restored_echo(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                case = scenario(kind)
                before = deepcopy(case.project)
                state = case.state()
                self.assertNotIn(kind, json.dumps(state))
                self.assertNotIn("fault", json.dumps(state))
                self.assertEqual(state["dhcpAddressOrigin"], "UNKNOWN")
                self.assertEqual(state["dhcpCheck"], "NOT_VERIFIED")
                self.assertFalse(state["canDiagnose"])
                source = case.probe("address", {})["observation"]
                self.assertEqual(source["documentedIpv4"], "192.0.2.10/24")
                self.assertEqual(source["origin"], "UNKNOWN")
                self.assertEqual(source["dhcpStatus"], "NOT_VERIFIED")
                ping = case.probe("ping", {})["observation"]
                self.assertNotEqual(ping["status"], "REPLIED")
                self.assertFalse(ping["replyMatched"])
                self.assertEqual(ping["source"], "SIMULATED")
                self.assertTrue(ping["requestStatus"])
                route = case.probe(
                    "route", {"nodeId": "a", "destinationIpv4": "203.0.113.20"}
                )["observation"]
                self.assertIn(route["status"], ("MATCH", "NO_ROUTE"))
                self.assertEqual(route["source"], "SIMULATED_CONFIG")
                link = case.probe("link", {"linkId": "la"})["observation"]
                self.assertTrue(link["documentedEnabled"])
                self.assertIn(link["observedEnabled"], (True, False))
                port = case.probe("port", {"nodeId": "sw-left", "portId": "a"})["observation"]
                self.assertTrue(port["documentedEnabled"])
                self.assertIsNone(port["documentedIpv4"])
                self.assertIsNone(port["observedIpv4"])
                self.assertEqual(port["source"], "SIMULATED_CONFIG")
                vlan = case.probe("vlan", {"nodeId": "sw-left", "portId": "a"})["observation"]
                self.assertEqual(vlan["documentedVlan"], {"mode": "access", "vlan": 10})
                self.assertEqual(vlan["source"], "SIMULATED_CONFIG")
                self.assertTrue(case.state()["canDiagnose"])
                wrong = next(x for x in KINDS if x != kind)
                rejected = case.diagnose(wrong)
                self.assertFalse(rejected["correct"])
                self.assertNotIn(kind, json.dumps(rejected))
                with self.assertRaisesRegex(ProjectValidationError, "correct diagnosis"):
                    case.repair()
                approved = case.diagnose(kind)
                self.assertTrue(approved["correct"])
                restored = case.repair()
                self.assertEqual(restored["status"], "RECOVERED")
                self.assertNotEqual(restored["failedEchoStatus"], "REPLIED")
                self.assertEqual(restored["restoredEchoStatus"], "REPLIED")
                self.assertTrue(restored["replyMatched"])
                self.assertEqual(restored["faultCategory"], kind)
                self.assertEqual(restored["repair"]["scope"], "PREVIEW_ONLY")
                self.assertEqual(case.project, before)
                self.assertEqual(case.state()["dhcpCheck"], "NOT_VERIFIED")
                with self.assertRaisesRegex(ProjectValidationError, "already repaired"):
                    case.probe("ping", {})
                with self.assertRaisesRegex(ProjectValidationError, "already repaired"):
                    case.repair()

    def test_hidden_switch_port_shutdown_measured_and_recovered(self):
        case = scenario("PORT_SHUTDOWN")
        fault = case._fault
        self.assertEqual(fault["type"], "PORT_DISABLED")
        measured = case.probe("port", {
            "nodeId": fault["nodeId"], "portId": fault["portId"],
        })["observation"]
        self.assertEqual(measured["source"], "SIMULATED_CONFIG")
        self.assertTrue(measured["documentedEnabled"])
        self.assertFalse(measured["observedEnabled"])
        self.assertNotIn("PORT_SHUTDOWN", json.dumps(case.state()))
        self.assertNotEqual(case.probe("ping", {})["observation"]["status"], "REPLIED")
        case.probe("route", {"nodeId": "a", "destinationIpv4": "203.0.113.20"})
        self.assertTrue(case.state()["canDiagnose"])
        self.assertTrue(case.diagnose("PORT_SHUTDOWN")["correct"])
        restored = case.repair()
        self.assertEqual(restored["status"], "RECOVERED")
        self.assertEqual(restored["repair"]["action"], "RE_ENABLE_PORT")
        self.assertEqual(restored["repair"]["scope"], "PREVIEW_ONLY")
        self.assertTrue(restored["replyMatched"])

    def test_hidden_ipv4_prefix_fault_uses_documented_peer_and_real_echo(self):
        case = scenario("IPV4_PREFIX_MISMATCH")
        fault = case._fault
        self.assertEqual(fault["type"], "IPV4_PREFIX_CHANGED")
        self.assertEqual(fault["nodeId"], "r")
        self.assertIn(fault["portId"], ("wan", "lan"))
        observed = case.probe("port", {
            "nodeId": fault["nodeId"], "portId": fault["portId"],
        })["observation"]
        self.assertEqual(observed["source"], "SIMULATED_CONFIG")
        self.assertTrue(observed["documentedEnabled"])
        self.assertEqual(observed["documentedIpv4"].split("/")[0],
                         observed["observedIpv4"].split("/")[0])
        self.assertNotEqual(observed["documentedIpv4"], observed["observedIpv4"])
        self.assertNotIn("IPV4_PREFIX_MISMATCH", json.dumps(case.state()))
        original = deepcopy(case.project)
        failed = case.probe("ping", {})["observation"]
        self.assertNotEqual(failed["status"], "REPLIED")
        self.assertFalse(failed["replyMatched"])
        case.probe("route", {"nodeId": "r", "destinationIpv4": "203.0.113.20"})
        self.assertTrue(case.state()["canDiagnose"])
        self.assertFalse(case.diagnose("STATIC_ROUTE_MISSING")["correct"])
        self.assertTrue(case.diagnose("IPV4_PREFIX_MISMATCH")["correct"])
        recovery = case.repair()
        self.assertEqual(recovery["status"], "RECOVERED")
        self.assertEqual(recovery["repair"]["action"], "RESTORE_IPV4")
        self.assertEqual(recovery["repair"]["expectedIpv4"],
                         observed["documentedIpv4"])
        self.assertEqual(recovery["repair"]["scope"], "PREVIEW_ONLY")
        self.assertTrue(recovery["replyMatched"])
        self.assertEqual(case.project, original)

    def test_hidden_static_next_hop_must_fail_arp_and_recover_exact_route(self):
        case = scenario("STATIC_NEXT_HOP_UNREACHABLE")
        before = deepcopy(case.project)
        fault = case._fault
        self.assertEqual(fault["type"], "STATIC_NEXT_HOP_CHANGED")
        self.assertIn((fault["nodeId"], fault["routeId"]),
                      {("a", "via-router"), ("b", "return-to-a")})
        destination = ("203.0.113.20" if fault["nodeId"] == "a"
                       else "192.0.2.10")
        route = case.probe("route", {
            "nodeId": fault["nodeId"], "destinationIpv4": destination,
        })["observation"]
        self.assertEqual(route["status"], "MATCH")
        selected = route["selectedRoute"]
        self.assertEqual(selected["routeId"], fault["routeId"])
        documented = next(r for r in route["documentedStaticRoutes"]
                          if r["id"] == fault["routeId"])
        self.assertNotEqual(selected["nextHop"], documented["nextHop"])
        self.assertEqual(selected["nextHop"], fault["newNextHop"])
        self.assertEqual(selected["destination"], documented["destination"])
        self.assertNotIn("STATIC_NEXT_HOP_UNREACHABLE", json.dumps(case.state()))
        ping = case.probe("ping", {})["observation"]
        self.assertNotEqual(ping["status"], "REPLIED")
        self.assertFalse(ping["replyMatched"])
        self.assertIn("ARP_FAILED", (ping["requestStatus"], ping["replyStatus"]))
        steps = ping["requestSteps"] + ping["replySteps"]
        self.assertTrue(any(step["arpStatus"] == "NO_REPLY" for step in steps))
        case.probe("address", {})
        self.assertTrue(case.state()["canDiagnose"])
        self.assertFalse(case.diagnose("STATIC_ROUTE_MISSING")["correct"])
        self.assertTrue(case.diagnose("STATIC_NEXT_HOP_UNREACHABLE")["correct"])
        result = case.repair()
        self.assertEqual(result["status"], "RECOVERED")
        self.assertEqual(result["restoredEchoStatus"], "REPLIED")
        self.assertTrue(result["replyMatched"])
        self.assertEqual(result["repair"]["action"], "RESTORE_NEXT_HOP")
        self.assertEqual(result["repair"]["expectedNextHop"], documented["nextHop"])
        self.assertEqual(result["repair"]["scope"], "PREVIEW_ONLY")
        self.assertEqual(case.project, before)

    def test_next_hop_candidates_reject_unused_routes_and_configured_peers(self):
        project = routed_reply_lab()
        next(n for n in project["nodes"] if n["id"] == "r")["staticRoutes"] = [{
            "id": "unrelated", "destination": "198.51.100.0/24",
            "nextHop": "192.0.2.10", "outPort": "wan",
        }]
        baseline = EchoExchange(project).ping(
            "a", "eth0", "203.0.113.20", 5, 101, 1)
        self.assertEqual(baseline["status"], "REPLIED")
        candidates = [fault for kind, fault in _candidates(project, baseline)
                      if kind == "STATIC_NEXT_HOP_UNREACHABLE"]
        self.assertTrue(candidates)
        self.assertFalse(any(f["nodeId"] == "r" for f in candidates))
        allocated = {port["ipv4"].split("/")[0]
                     for node in project["nodes"] for port in node["ports"]
                     if port["ipv4"] is not None}
        for fault in candidates:
            self.assertNotIn(fault["newNextHop"], allocated)
            original = next(route for node in project["nodes"]
                            if node["id"] == fault["nodeId"]
                            for route in node["staticRoutes"]
                            if route["id"] == fault["routeId"])
            self.assertNotEqual(fault["newNextHop"], original["nextHop"])

    def test_lookup_reverse_route_proves_reply_failure_not_fake_ping_pass(self):
        case = scenario("STATIC_ROUTE_MISSING")
        fault = case._fault
        self.assertEqual(fault["type"], "STATIC_ROUTE_REMOVED")
        reply = case.probe("ping", {})["observation"]
        self.assertNotEqual(reply["status"], "REPLIED")
        self.assertFalse(reply["replyMatched"])
        self.assertTrue(reply["requestStatus"])
        dst = case.probe(
            "route", {"nodeId": "b", "destinationIpv4": "192.0.2.10"}
        )["observation"]
        self.assertEqual(dst["destinationIpv4"], "192.0.2.10")
        self.assertIn(dst["status"], ("MATCH", "NO_ROUTE"))
        self.assertFalse(case.state()["canDiagnose"])
        case.probe("address", {})
        self.assertTrue(case.state()["canDiagnose"])

    def test_invalid_inputs_no_probe_recorded_or_canonical_mutation(self):
        case = scenario("CABLE_DOWN")
        original = case.state()
        original_project = deepcopy(case.project)
        bad = [
            ("ping", {"extra": 1}),
            ("address", {"portId": "eth0"}),
            ("route", {}),
            ("route", {"nodeId": "missing", "destinationIpv4": "203.0.113.20"}),
            ("route", {"nodeId": "a", "destinationIpv4": "8.8.8.8"}),
            ("route", {"nodeId": "sw-left", "destinationIpv4": "203.0.113.20"}),
            ("route", {"nodeId": "a", "destinationIpv4": "203.0.113.20", "extra": 1}),
            ("link", {"linkId": "wrong"}),
            ("link", {"linkId": True}),
            ("port", {"nodeId": "missing", "portId": "a"}),
            ("port", {"nodeId": "sw-left"}),
            ("port", {"nodeId": True, "portId": "a"}),
            ("port", {"nodeId": "sw-left", "portId": "missing"}),
            ("port", {"nodeId": "sw-left", "portId": "a", "extra": 1}),
            ("port", {"nodeId": "r", "portId": "missing"}),
            ("port", {"nodeId": "r", "portId": None}),
            ("vlan", {"nodeId": "a", "portId": "eth0"}),
            ("vlan", {"nodeId": "sw-left", "portId": "missing"}),
            ("vlan", {"nodeId": "sw-left"}),
            ("bad", {}),
            (True, {}),
        ]
        for kind, target in bad:
            with self.subTest(kind=kind, target=target), self.assertRaises(ProjectValidationError):
                case.probe(kind, target)
            self.assertEqual(case.state(), original)
            self.assertEqual(case.project, original_project)
        with self.assertRaisesRegex(ProjectValidationError, "real ping"):
            case.diagnose("CABLE_DOWN")
        with self.assertRaisesRegex(ProjectValidationError, "correct diagnosis"):
            case.repair()

    def test_failed_baseline_not_admitted_and_no_fake_connected_reachability(self):
        project = routed_reply_lab()
        next(n for n in project["nodes"] if n["id"] == "b")["staticRoutes"].clear()
        with self.assertRaisesRegex(ProjectValidationError, "initial routed Echo"):
            IcmpInvestigation(project, "a", "eth0", "203.0.113.20", 5)
        for ttl in (1, 0, 256, True, "5"):
            with self.subTest(ttl=ttl), self.assertRaises(ProjectValidationError):
                IcmpInvestigation(routed_reply_lab(), "a", "eth0", "203.0.113.20", ttl)
        with self.assertRaises(ProjectValidationError):
            IcmpInvestigation(routed_reply_lab(), "a", "eth0", "not-ip", 5)

    def test_no_eligible_fault_refuses_exercise(self):
        p = routed_reply_lab()
        p["links"] = [x for x in p["links"] if x["id"] == "la"]
        with self.assertRaises(ProjectValidationError):
            IcmpInvestigation(p, "a", "eth0", "203.0.113.20", 5)

    def test_no_cause_leak_and_guess_limit(self):
        case = scenario("STATIC_ROUTE_MISSING")
        for name, target in (
            ("ping", {}), ("address", {}),
            ("route", {"nodeId": "a", "destinationIpv4": "203.0.113.20"}),
        ):
            case.probe(name, target)
        for _ in range(3):
            result = case.diagnose("CABLE_DOWN")
            self.assertFalse(result["correct"])
            self.assertNotIn("STATIC_ROUTE_MISSING", json.dumps(result))
        with self.assertRaisesRegex(ProjectValidationError, "maximum guesses"):
            case.diagnose("STATIC_ROUTE_MISSING")

    def test_project_bound_opaque_multi_session_and_restart_semantics(self):
        p = routed_reply_lab()
        registry = IcmpInvestigationRegistry()
        with patch("network_core.icmp_investigation.secrets.randbelow", return_value=0):
            first = registry.start(p, "a", "eth0", "203.0.113.20", 5)
            second = registry.start(p, "a", "eth0", "203.0.113.20", 5)
        self.assertNotEqual(first["sessionId"], second["sessionId"])
        self.assertNotIn("fault", json.dumps(first))
        self.assertNotIn("fault", json.dumps(second))
        changed = deepcopy(p)
        changed["links"][0]["enabled"] = False
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            registry.probe(first["sessionId"], changed, "ping", {})
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            registry.diagnose(first["sessionId"], changed, "CABLE_DOWN")
        with self.assertRaisesRegex(ProjectValidationError, "project changed"):
            registry.repair(first["sessionId"], changed)
        self.assertEqual(registry.probe(first["sessionId"], p, "address", {})
                         ["observation"]["dhcpStatus"], "NOT_VERIFIED")
        self.assertEqual(registry.probe(second["sessionId"], p, "ping", {})
                         ["observation"]["replyMatched"], False)
        self.assertEqual(registry.stop(first["sessionId"]), {"status": "STOPPED"})
        with self.assertRaisesRegex(ProjectValidationError, "unknown or expired"):
            registry.probe(first["sessionId"], p, "ping", {})


class IcmpInvestigationHttpTests(unittest.TestCase):
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

    def post(self, route, body):
        request = Request(self.url + "/api/icmp/investigation/" + route,
                          data=json.dumps(body).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_real_http_observations_repair_and_byte_identical_project(self):
        p = routed_reply_lab()
        self.store.save("original", p)
        path = self.root / "original.yadilab"
        raw = path.read_bytes()
        with patch("network_core.icmp_investigation.secrets.randbelow", return_value=0):
            status, opened = self.post("start", {
                "project": p, "sourceNode": "a", "sourcePort": "eth0",
                "destinationIpv4": "203.0.113.20", "ttl": 5,
            })
        self.assertEqual(status, 200)
        self.assertNotIn("fault", json.dumps(opened))
        sid = opened["sessionId"]
        base = {"sessionId": sid, "project": p}
        def call(route, **fields):
            return self.post(route, {**base, **fields})
        status, address = call("probe", probe="address", target={})
        self.assertEqual(status, 200)
        self.assertEqual(address["observation"]["dhcpStatus"], "NOT_VERIFIED")
        self.assertEqual(call("probe", probe="ping", target={})[1]
                         ["observation"]["replyMatched"], False)
        status, routing = call("probe", probe="route", target={
            "nodeId": "a", "destinationIpv4": "203.0.113.20",
        })
        self.assertEqual(status, 200)
        self.assertEqual(routing["observation"]["documentedStaticRoutes"],
                         p["nodes"][0]["staticRoutes"])
        self.assertEqual(routing["observation"]["selectedRoute"]["nextHop"],
                         "192.0.2.1")
        status, port_status = call("probe", probe="port", target={
            "nodeId": "sw-left", "portId": "a",
        })
        self.assertEqual(status, 200)
        self.assertTrue(port_status["observation"]["documentedEnabled"])
        self.assertEqual(port_status["observation"]["source"], "SIMULATED_CONFIG")
        status, router_ipv4 = call("probe", probe="port", target={
            "nodeId": "r", "portId": "lan",
        })
        self.assertEqual(status, 200)
        self.assertEqual(router_ipv4["observation"]["documentedIpv4"],
                         "203.0.113.1/24")
        self.assertEqual(router_ipv4["observation"]["source"], "SIMULATED_CONFIG")
        self.assertEqual(call("repair")[0], 422)
        self.assertEqual(call("diagnose", diagnosis="STATIC_ROUTE_MISSING")[1]["correct"],
                         False)
        status, confirmed = call("diagnose", diagnosis="CABLE_DOWN")
        self.assertEqual(status, 200)
        self.assertTrue(confirmed["correct"])
        status, restored = call("repair")
        self.assertEqual(status, 200)
        self.assertEqual(restored["status"], "RECOVERED")
        self.assertEqual(restored["restoredEchoStatus"], "REPLIED")
        self.assertTrue(restored["replyMatched"])
        self.assertEqual(restored["faultCategory"], "CABLE_DOWN")
        self.assertEqual(path.read_bytes(), raw)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                         hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.store.read("original")["project"], p)

    def test_http_exact_shapes_invalid_project_and_server_restart(self):
        p = routed_reply_lab()
        status, started = self.post("start", {
            "project": p, "sourceNode": "a", "sourcePort": "eth0",
            "destinationIpv4": "203.0.113.20", "ttl": 5,
        })
        self.assertEqual(status, 200)
        sid = started["sessionId"]
        base = {"sessionId": sid, "project": p, "probe": "address", "target": {}}
        changed = deepcopy(p)
        changed["links"][0]["enabled"] = False
        tests = [
            ("start", {"project": p, "sourceNode": "a", "sourcePort": "eth0",
                       "destinationIpv4": "203.0.113.20", "ttl": 5, "extra": 1}),
            ("start", {"project": p, "sourceNode": "a", "sourcePort": "eth0",
                       "destinationIpv4": "203.0.113.20", "ttl": True}),
            ("probe", {**base, "extra": 1}),
            ("probe", {**base, "probe": "unsupported"}),
            ("probe", {**base, "project": changed}),
            ("probe", {**base, "sessionId": "not-a-session"}),
            ("diagnose", {"sessionId": sid, "project": p, "diagnosis": None}),
            ("repair", {"sessionId": sid, "project": p, "extra": True}),
        ]
        for route, payload in tests:
            with self.subTest(route=route):
                code, error = self.post(route, payload)
                self.assertEqual(code, 422)
                self.assertEqual(error["error"], "INVALID_PROJECT")
        self.assertEqual(self.server.icmp_investigations._get(sid).state()["observations"], 0)
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.server = LabHTTPServer(("127.0.0.1", 0), ProjectStore(self.root))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        code, error = self.post("probe", base)
        self.assertEqual(code, 422)
        self.assertIn("unknown or expired", error["message"])
