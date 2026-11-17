"""Behavioral tests for MAC-only forwarding on canonical physical links."""
import copy
import unittest

from network_core.ethernet import EthernetFabric
from network_core.model import ProjectValidationError, blank_project

A = "02:00:00:00:00:0A"
B = "02:00:00:00:00:0B"
C = "02:00:00:00:00:0C"
UNKNOWN = "02:00:00:00:00:DD"
BROADCAST = "ff:ff:ff:ff:ff:ff"


def node(id, kind, ports):
    return {"id": id, "label": id, "kind": kind,
            "x": 0, "y": 0, "zoneId": None,
            "ports": [{"id": port, "name": port, "ipv4": None, "enabled": True}
                      for port in ports]}


def link(id, n1, p1, n2, p2):
    return {"id": id, "a": {"node": n1, "port": p1},
            "b": {"node": n2, "port": p2}, "enabled": True}


def star():
    p = blank_project("Star")
    p["nodes"] = [node("a", "host", ["eth0"]),
                  node("sw", "switch", ["p1", "p2", "p3"]),
                  node("b", "host", ["eth0"]),
                  node("c", "host", ["eth0"])]
    p["links"] = [link("la", "a", "eth0", "sw", "p1"),
                  link("lb", "b", "eth0", "sw", "p2"),
                  link("lc", "c", "eth0", "sw", "p3")]
    return p


class EthernetTests(unittest.TestCase):
    def test_unknown_unicast_floods_and_learns_source(self):
        e = EthernetFabric(star())
        result = e.inject("a", "eth0", A, UNKNOWN)
        self.assertEqual(result["status"], "SIMULATED")
        self.assertEqual([t["linkId"] for t in result["transmissions"]], ["la", "lb", "lc"])
        self.assertEqual([a["node"] for a in result["endpointArrivals"]], ["b", "c"])
        self.assertEqual(result["switchDecisions"][0]["action"], "FLOOD")
        self.assertEqual(e.mac_table("sw"), {A: "p1"})

    def test_broadcast_floods_all_other_active_ports(self):
        result = EthernetFabric(star()).inject("a", "eth0", A, BROADCAST)
        self.assertEqual([a["node"] for a in result["endpointArrivals"]], ["b", "c"])
        self.assertEqual(result["switchDecisions"][0]["action"], "FLOOD")

    def test_mac_normalization_and_broadcast_case(self):
        e = EthernetFabric(star())
        r = e.inject("a", "eth0", "02:aa:bb:cc:dd:ee", BROADCAST)
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual(e.mac_table("sw"), {"02:AA:BB:CC:DD:EE": "p1"})

    def test_transit_link_down_stops_forwarding(self):
        p = blank_project("Disconnected")
        p["nodes"] = [node("a", "host", ["eth0"]),
                      node("s1", "switch", ["h", "wire"]),
                      node("s2", "switch", ["wire", "h"]),
                      node("b", "host", ["eth0"])]
        p["links"] = [link("l1", "a", "eth0", "s1", "h"),
                      link("l2", "s1", "wire", "s2", "wire"),
                      link("l3", "s2", "h", "b", "eth0")]
        p["links"][1]["enabled"] = False
        r = EthernetFabric(p).inject("a", "eth0", A, UNKNOWN)
        self.assertEqual([x["linkId"] for x in r["transmissions"]], ["l1"])
        self.assertEqual(r["endpointArrivals"], [])

    def test_unicast_uses_learned_destination_port(self):
        e = EthernetFabric(star())
        e.inject("b", "eth0", B, A)
        r = e.inject("a", "eth0", A, B)
        self.assertEqual([t["linkId"] for t in r["transmissions"]], ["la", "lb"])
        self.assertEqual([x["node"] for x in r["endpointArrivals"]], ["b"])
        self.assertEqual(r["switchDecisions"][0]["action"], "FORWARD_UNICAST")
        self.assertEqual(e.mac_table("sw"), {A: "p1", B: "p2"})

    def test_known_destination_on_ingress_is_filtered(self):
        e = EthernetFabric(star())
        r = e.inject("a", "eth0", A, A)
        self.assertEqual([t["linkId"] for t in r["transmissions"]], ["la"])
        self.assertEqual(r["switchDecisions"][0]["action"], "FILTER_SAME_PORT")
        self.assertEqual(r["endpointArrivals"], [])

    def test_learning_moves_address_only_when_new_frame_arrives(self):
        e = EthernetFabric(star())
        e.inject("a", "eth0", A, UNKNOWN)
        e.inject("b", "eth0", A, UNKNOWN)
        self.assertEqual(e.mac_table("sw"), {A: "p2"})

    def test_returns_copies_of_table(self):
        e = EthernetFabric(star())
        e.inject("a", "eth0", A, B)
        snapshot = e.mac_table("sw")
        snapshot.clear()
        self.assertEqual(e.mac_table("sw"), {A: "p1"})

    def test_separate_sessions_have_no_implicit_state(self):
        p = star()
        e = EthernetFabric(p)
        e.inject("a", "eth0", A, B)
        self.assertEqual(EthernetFabric(p).mac_table("sw"), {})
        self.assertEqual(p["nodes"][0]["ports"][0]["ipv4"], None)

    def test_disabled_link_means_no_frame_at_peer(self):
        p = star()
        p["links"][2]["enabled"] = False
        e = EthernetFabric(p)
        r = e.inject("a", "eth0", A, UNKNOWN)
        self.assertEqual([t["linkId"] for t in r["transmissions"]], ["la", "lb"])
        self.assertEqual([x["node"] for x in r["endpointArrivals"]], ["b"])

    def test_disabled_port_cannot_receive_or_emit(self):
        p = star()
        p["nodes"][1]["ports"][1]["enabled"] = False
        r = EthernetFabric(p).inject("a", "eth0", A, BROADCAST)
        self.assertEqual([t["linkId"] for t in r["transmissions"]], ["la", "lc"])
        p["nodes"][0]["ports"][0]["enabled"] = False
        e = EthernetFabric(p)
        r = e.inject("a", "eth0", A, BROADCAST)
        self.assertEqual(r["status"], "NO_ACTIVE_LINK")
        self.assertEqual(r["transmissions"], [])
        self.assertEqual(e.mac_table("sw"), {})

    def test_no_inferred_cables_from_same_address_space(self):
        p = star()
        p["links"] = []
        p["nodes"][0]["ports"][0]["ipv4"] = "192.0.2.11/24"
        p["nodes"][2]["ports"][0]["ipv4"] = "192.0.2.12/24"
        r = EthernetFabric(p).inject("a", "eth0", A, B)
        self.assertEqual(r["status"], "NO_ACTIVE_LINK")
        self.assertEqual(r["transmissions"], [])

    def test_no_bridging_through_router(self):
        p = blank_project("Routing not modeled")
        p["nodes"] = [node("a", "host", ["eth0"]),
                      node("router", "router", ["wan", "lan"]),
                      node("b", "host", ["eth0"])]
        p["links"] = [link("l1", "a", "eth0", "router", "wan"),
                      link("l2", "router", "lan", "b", "eth0")]
        r = EthernetFabric(p).inject("a", "eth0", A, B)
        self.assertEqual([t["linkId"] for t in r["transmissions"]], ["l1"])
        self.assertEqual([x["node"] for x in r["endpointArrivals"]], ["router"])
        self.assertEqual(r["switchDecisions"], [])

    def test_switch_must_not_generate_unconfigured_frames(self):
        with self.assertRaisesRegex(ProjectValidationError, "non-switch"):
            EthernetFabric(star()).inject("sw", "p1", A, B)

    def test_undeclared_source_endpoint_rejected(self):
        for n, p in [("fictitious", "eth0"), ("a", "unknown"), (None, "eth0"), ("a", None)]:
            with self.subTest(node=n, port=p), self.assertRaisesRegex(ProjectValidationError, "undeclared"):
                EthernetFabric(star()).inject(n, p, A, B)

    def test_multicast_and_broadcast_as_source_rejected(self):
        for mac in ("01:00:5E:00:00:01", BROADCAST, "00:00:00:00:00:00"):
            with self.subTest(mac=mac), self.assertRaisesRegex(ProjectValidationError, "source MAC"):
                EthernetFabric(star()).inject("a", "eth0", mac, B)

    def test_multicast_destination_unsupported(self):
        with self.assertRaisesRegex(ProjectValidationError, "multicast"):
            EthernetFabric(star()).inject("a", "eth0", A, "01:00:5E:00:00:01")

    def test_mac_rejects_malformed_values_without_state_change(self):
        e = EthernetFabric(star())
        for mac in ("foo", "00:11:22:33:44", "00-11-22-33-44-55", "GG:00:00:00:00:01", None, 3):
            with self.subTest(mac=mac), self.assertRaises(ProjectValidationError):
                e.inject("a", "eth0", mac, B)
        self.assertEqual(e.mac_table("sw"), {})

    def test_switch_loop_rejected_instead_of_fabricating_stp(self):
        p = blank_project("Cycle")
        p["nodes"] = [node("a", "host", ["eth0"]),
                      node("s1", "switch", ["h", "x", "z"]),
                      node("s2", "switch", ["x", "y"]),
                      node("s3", "switch", ["y", "z"])]
        p["links"] = [link("la", "a", "eth0", "s1", "h"),
                      link("l1", "s1", "x", "s2", "x"),
                      link("l2", "s2", "y", "s3", "y"),
                      link("l3", "s3", "z", "s1", "z")]
        with self.assertRaisesRegex(ProjectValidationError, "switch loop unsupported"):
            EthernetFabric(p)

    def test_parallel_switch_links_rejected_as_loop(self):
        p = blank_project("Parallel")
        p["nodes"] = [node("s1", "switch", ["p1", "p2"]),
                      node("s2", "switch", ["p1", "p2"])]
        p["links"] = [link("l1", "s1", "p1", "s2", "p1"),
                      link("l2", "s1", "p2", "s2", "p2")]
        with self.assertRaisesRegex(ProjectValidationError, "switch loop unsupported"):
            EthernetFabric(p)

    def test_switch_chain_floods_only_explicit_connected_links(self):
        p = blank_project("Chain")
        p["nodes"] = [node("a", "host", ["eth0"]),
                      node("s1", "switch", ["h", "trunk"]),
                      node("s2", "switch", ["trunk", "h"]),
                      node("b", "host", ["eth0"])]
        p["links"] = [link("l1", "a", "eth0", "s1", "h"),
                      link("l2", "s1", "trunk", "s2", "trunk"),
                      link("l3", "s2", "h", "b", "eth0")]
        e = EthernetFabric(p)
        r = e.inject("a", "eth0", A, B)
        self.assertEqual([x["linkId"] for x in r["transmissions"]], ["l1", "l2", "l3"])
        self.assertEqual(e.mac_table("s1"), {A: "h"})
        self.assertEqual(e.mac_table("s2"), {A: "trunk"})
        r = e.inject("b", "eth0", B, A)
        self.assertEqual([x["linkId"] for x in r["transmissions"]], ["l3", "l2", "l1"])
        self.assertEqual([x["action"] for x in r["switchDecisions"]], ["FORWARD_UNICAST", "FORWARD_UNICAST"])

    def test_canonical_document_must_validate_before_simulating(self):
        p = star()
        p["links"][0]["b"]["port"] = "fictitious"
        with self.assertRaisesRegex(ProjectValidationError, "undeclared endpoint"):
            EthernetFabric(p)

    def test_simulation_cannot_change_source_project(self):
        p = star()
        before = copy.deepcopy(p)
        e = EthernetFabric(p)
        e.inject("a", "eth0", A, B)
        self.assertEqual(p, before)


if __name__ == "__main__":
    unittest.main()
