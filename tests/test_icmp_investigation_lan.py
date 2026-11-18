"""Two declared hosts and one switch: connected ICMP investigation."""
from copy import deepcopy
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from network_core.icmp_investigation import IcmpInvestigation, LAN_KINDS, _candidates
from network_core.icmp_ping import EchoExchange
from network_core.model import ProjectValidationError, blank_project, validate_project
from network_core.storage import ProjectStore
from network_core.troubleshooting import compare_fault
from test_ethernet import link, node


def lan_lab(second_vlan=True):
    project = blank_project("Two hosts on a declared switch")
    project["nodes"] = [node("a", "host", ["eth0"]),
                        node("sw", "switch", ["a", "b", "spare"]),
                        node("b", "host", ["eth0"])]
    project["links"] = [link("la", "a", "eth0", "sw", "a"),
                        link("lb", "sw", "b", "b", "eth0")]
    project["nodes"][0]["ports"][0].update(
        ipv4="192.168.10.10/24", mac="02:00:00:00:10:0A")
    project["nodes"][2]["ports"][0].update(
        ipv4="192.168.10.20/24", mac="02:00:00:00:10:14")
    for port in project["nodes"][1]["ports"]:
        port["vlan"] = {"mode": "access", "vlan":
                        20 if second_vlan and port["id"] == "spare" else 10}
    return validate_project(project)


class LanInvestigationTests(unittest.TestCase):
    def test_connected_echo_arp_and_all_reversible_lan_faults(self):
        project = lan_lab()
        baseline = EchoExchange(project).ping("a", "eth0", "192.168.10.20", 5, 101, 1)
        self.assertEqual(baseline["status"], "REPLIED")
        self.assertTrue(baseline["replyMatched"])
        self.assertEqual([x["node"] for x in baseline["request"]["steps"]], ["a"])
        self.assertEqual([x["node"] for x in baseline["reply"]["steps"]], ["b"])
        for direction in ("request", "reply"):
            step = baseline[direction]["steps"][0]
            self.assertEqual(step["route"]["type"], "CONNECTED")
            self.assertEqual(step["arp"]["status"], "RESOLVED")
            self.assertEqual(len(step["arp"]["requestTransmissions"]), 2)
            self.assertEqual(len(step["ipv4Transmissions"]), 2)
        self.assertEqual(project["nodes"][0].get("staticRoutes", []), [])
        for kind in LAN_KINDS:
            with self.subTest(kind=kind):
                case = IcmpInvestigation(project, "a", "eth0", "192.168.10.20", 5,
                                         _test_kind=kind)
                before = deepcopy(case.project)
                self.assertNotIn(kind, json.dumps(case.state()))
                ping = case.probe("ping", {})["observation"]
                self.assertNotEqual(ping["status"], "REPLIED")
                self.assertFalse(ping["replyMatched"])
                if kind == "IPV4_PREFIX_MISMATCH":
                    self.assertEqual(ping["requestStatus"], "NO_ROUTE")
                    self.assertEqual(ping["requestSteps"], [])
                else:
                    self.assertEqual(ping["requestStatus"], "ARP_FAILED")
                    self.assertIn(ping["requestSteps"][0]["arpStatus"],
                                  ("NO_REPLY", "NO_ACTIVE_LINK"))
                route = case.probe("route", {"nodeId": "a",
                                             "destinationIpv4": "192.168.10.20"})["observation"]
                self.assertEqual(route["status"],
                                 "NO_ROUTE" if kind == "IPV4_PREFIX_MISMATCH" else "MATCH")
                if kind != "IPV4_PREFIX_MISMATCH":
                    self.assertEqual(route["selectedRoute"]["type"], "CONNECTED")
                self.assertEqual(route["documentedStaticRoutes"], [])
                case.probe("address", {})
                self.assertFalse(case.diagnose(next(k for k in LAN_KINDS if k != kind))["correct"])
                self.assertNotIn(kind, json.dumps(case.state()))
                self.assertTrue(case.diagnose(kind)["correct"])
                fixed = case.repair()
                self.assertEqual(fixed["status"], "RECOVERED")
                self.assertEqual(fixed["faultCategory"], kind)
                self.assertEqual(fixed["restoredEchoStatus"], "REPLIED")
                self.assertTrue(fixed["replyMatched"])
                self.assertIn("matchande Echo Reply", fixed["report"]["verification"])
                self.assertIn("NO_ROUTE" if kind == "IPV4_PREFIX_MISMATCH" else "ARP",
                              fixed["report"]["evidence"])
                if kind == "IPV4_PREFIX_MISMATCH":
                    self.assertNotIn("ARP", fixed["report"]["evidence"])
                    self.assertIn("Värdadressen var oförändrad", fixed["report"]["rootCause"])
                self.assertEqual(case.project, before)

    def test_normal_lan_selection_can_choose_more_than_cable_faults(self):
        project = lan_lab()
        with patch("network_core.icmp_investigation.secrets.randbelow",
                   side_effect=lambda count: count - 1):
            case = IcmpInvestigation(project, "a", "eth0", "192.168.10.20", 5)
        self.assertEqual(case._kind, "VLAN_MISMATCH")
        self.assertNotIn("VLAN_MISMATCH", json.dumps(case.state()))
        with patch("network_core.icmp_investigation.secrets.randbelow",
                   return_value=0):
            first = IcmpInvestigation(project, "a", "eth0", "192.168.10.20", 5)
        self.assertEqual(first._kind, "CABLE_DOWN")

    def test_candidate_rejection_and_unchanged_save_open_bytes(self):
        project = lan_lab(second_vlan=False)
        baseline = EchoExchange(project).ping("a", "eth0", "192.168.10.20", 5, 1, 1)
        self.assertFalse(any(kind == "VLAN_MISMATCH"
                             for kind, _ in _candidates(project, baseline)))
        with self.assertRaisesRegex(ProjectValidationError, "category is not verified"):
            IcmpInvestigation(project, "a", "eth0", "192.168.10.20", 5,
                              _test_kind="VLAN_MISMATCH")
        ineffective_prefix = compare_fault(project, "a", "eth0", "192.168.10.20", 5, 1, 1,
                                           {"type": "IPV4_PREFIX_CHANGED", "nodeId": "a",
                                            "portId": "eth0", "newPrefix": 25})
        self.assertEqual(ineffective_prefix["status"], "NO_OBSERVED_IMPACT")
        self.assertEqual(ineffective_prefix["faulted"]["status"], "REPLIED")
        ineffective = compare_fault(project, "a", "eth0", "192.168.10.20", 5, 1, 1,
                                    {"type": "PORT_DISABLED", "nodeId": "sw",
                                     "portId": "spare"})
        self.assertEqual(ineffective["status"], "NO_OBSERVED_IMPACT")
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory))
            store.save("lan", project)
            original = store.path("lan").read_bytes()
            reopened = store.read("lan")["project"]
            case = IcmpInvestigation(reopened, "a", "eth0", "192.168.10.20", 5,
                                     _test_kind="IPV4_PREFIX_MISMATCH")
            self.assertEqual(case._kind, "IPV4_PREFIX_MISMATCH")
            case.probe("ping", {})
            case.probe("route", {"nodeId": "a", "destinationIpv4": "192.168.10.20"})
            case.probe("port", {"nodeId": "a", "portId": "eth0"})
            case.diagnose("IPV4_PREFIX_MISMATCH")
            case.repair()
            self.assertEqual(store.path("lan").read_bytes(), original)
            self.assertEqual(store.read("lan")["project"], project)

    def test_destination_prefix_breaks_only_return_route(self):
        project = lan_lab()
        project["nodes"] = [project["nodes"][2], project["nodes"][1], project["nodes"][0]]
        project = validate_project(project)
        case = IcmpInvestigation(project, "a", "eth0", "192.168.10.20", 5,
                                 _test_kind="IPV4_PREFIX_MISMATCH")
        self.assertEqual((case._fault["nodeId"], case._fault["newPrefix"]), ("b", 28))
        self.assertEqual(case._faulted["nodes"][0]["ports"][0]["ipv4"], "192.168.10.20/28")
        changed_ports = [(node["id"], port["id"]) for original, node in
                         zip(case.project["nodes"], case._faulted["nodes"])
                         for old, port in zip(original["ports"], node["ports"])
                         if old != port]
        self.assertEqual(changed_ports, [("b", "eth0")])
        self.assertEqual(case._faulted["links"], case.project["links"])
        ping = case.probe("ping", {})["observation"]
        self.assertEqual(ping["requestStatus"], "DELIVERED")
        self.assertEqual(ping["replyStatus"], "NO_ROUTE")
        self.assertEqual(ping["requestSteps"][0]["arpStatus"], "RESOLVED")
        self.assertEqual(ping["replySteps"], [])
        forward = case.probe("route", {"nodeId": "a",
                                         "destinationIpv4": "192.168.10.20"})["observation"]
        reverse = case.probe("route", {"nodeId": "b",
                                         "destinationIpv4": "192.168.10.10"})["observation"]
        self.assertEqual(forward["status"], "MATCH")
        self.assertEqual(reverse["status"], "NO_ROUTE")
        self.assertFalse(ping["replyMatched"])
        case.probe("port", {"nodeId": "b", "portId": "eth0"})
        self.assertTrue(case.diagnose("IPV4_PREFIX_MISMATCH")["correct"])
        fixed = case.repair()
        self.assertEqual(fixed["status"], "RECOVERED")
        self.assertIn("NO_ROUTE", fixed["report"]["evidence"])
        self.assertNotIn("ARP för", fixed["report"]["evidence"])
        self.assertEqual(fixed["repair"]["expectedIpv4"], "192.168.10.20/24")
        self.assertEqual(case.project, project)
