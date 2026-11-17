"""Independent VLAN/802.1Q tests against explicit real document links."""
import copy
import unittest

from network_core.ethernet import EthernetFabric
from network_core.ethernet_frame import EthernetFrame
from network_core.model import ProjectValidationError, blank_project
from test_ethernet import A, B, C, UNKNOWN, node, link, star

BROADCAST = "FF:FF:FF:FF:FF:FF"


def access(vlan):
    return {"mode": "access", "vlan": vlan}


def trunk(*allowed):
    return {"mode": "trunk", "allowedVlans": list(allowed)}


def star_vlans():
    return {("sw", "p1"): access(10),
            ("sw", "p2"): access(10),
            ("sw", "p3"): access(20)}


def two_switches():
    p = blank_project("Two explicitly wired VLAN segments")
    p["nodes"] = [
        node("a", "host", ["eth0"]),
        node("s1", "switch", ["h", "t", "x"]),
        node("b", "host", ["eth0"]),
        node("s2", "switch", ["t", "h", "x"]),
        node("c", "host", ["eth0"]),
        node("d", "host", ["eth0"]),
    ]
    p["links"] = [
        link("la", "a", "eth0", "s1", "h"),
        link("lt", "s1", "t", "s2", "t"),
        link("lb", "s2", "h", "b", "eth0"),
        link("lc", "c", "eth0", "s1", "x"),
        link("ld", "s2", "x", "d", "eth0"),
    ]
    ports = {
        ("s1", "h"): access(10), ("s1", "t"): trunk(10, 20),
        ("s1", "x"): access(20), ("s2", "h"): access(10),
        ("s2", "t"): trunk(10, 20), ("s2", "x"): access(20),
    }
    return p, ports


class Dot1QCodecTests(unittest.TestCase):
    def test_exact_single_tag_header_and_padding(self):
        f = EthernetFrame(B, A, 0x0800, b"abc", vlan_id=37)
        raw = f.serialize()
        self.assertEqual(len(raw), 60)
        self.assertEqual(raw[:12], bytes.fromhex(B.replace(":", "") + A.replace(":", "")))
        self.assertEqual(raw[12:18], bytes.fromhex("8100 0025 0800"))
        self.assertEqual(raw[18:21], b"abc")
        self.assertEqual(raw[21:], bytes(39))
        parsed = EthernetFrame.parse(raw)
        self.assertEqual(parsed.vlan_id, 37)
        self.assertEqual(parsed.ether_type, 0x0800)
        self.assertEqual(parsed.payload, b"abc" + bytes(39))
        self.assertEqual(parsed.serialize(), raw)

    def test_maximum_tagged_wire_length(self):
        payload = bytes(range(256)) * 5 + bytes(range(220))
        f = EthernetFrame(B, A, 0x88B5, payload, vlan_id=4094)
        raw = f.serialize()
        self.assertEqual(len(raw), 1518)
        self.assertEqual(EthernetFrame.parse(raw), f)
        with self.assertRaises(ProjectValidationError):
            EthernetFrame.parse(raw + b"x")

    def test_invalid_or_unsupported_tags_fail_closed(self):
        for vlan in (0, 4095, -1, True, "10", 10.5, []):
            with self.subTest(vlan=vlan), self.assertRaises(ProjectValidationError):
                EthernetFrame(B, A, 0x0800, b"", vlan_id=vlan)
        raw = EthernetFrame(B, A, 0x0800, bytes(42), vlan_id=10).serialize()
        for tci in (0x0000, 0x0FFF, 0x100A, 0x200A, 0x800A):
            with self.subTest(tci=tci), self.assertRaises(ProjectValidationError):
                EthernetFrame.parse(raw[:14] + tci.to_bytes(2, "big") + raw[16:])
        for inner in (0x8100, 0x88A8, 0x9100, 1500):
            with self.subTest(inner=inner), self.assertRaises(ProjectValidationError):
                EthernetFrame.parse(raw[:16] + inner.to_bytes(2, "big") + raw[18:])
        with self.assertRaises(ProjectValidationError):
            EthernetFrame.parse(EthernetFrame(B, A, 0x0800, bytes(1500)).serialize() + b"x")

    def test_tagged_host_injection_rejected_without_learning(self):
        fabric = EthernetFabric(star(), interface_macs={("a", "eth0"): A},
                                vlan_ports=star_vlans())
        frame = EthernetFrame(B, A, 0x88B5, b"", vlan_id=10)
        with self.assertRaisesRegex(ProjectValidationError, "must be untagged"):
            fabric.inject_frame("a", "eth0", frame)
        self.assertEqual(fabric.mac_table("sw", 10), {})


class VLANForwardingTests(unittest.TestCase):
    def test_access_broadcast_does_not_leak_to_other_vlan(self):
        fabric = EthernetFabric(star(), vlan_ports=star_vlans())
        r = fabric.inject("a", "eth0", A, BROADCAST)
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual([x["linkId"] for x in r["transmissions"]], ["la", "lb"])
        self.assertEqual([x["node"] for x in r["endpointArrivals"]], ["b"])
        self.assertEqual(r["switchDecisions"][0]["vlanId"], 10)
        self.assertEqual(fabric.mac_table("sw", 10), {A: "p1"})
        self.assertEqual(fabric.mac_table("sw", 20), {})
        fabric.inject("c", "eth0", C, BROADCAST)
        self.assertEqual(fabric.mac_table("sw", 20), {C: "p3"})

    def test_same_mac_can_be_learned_independently_per_vlan(self):
        fabric = EthernetFabric(star(), vlan_ports=star_vlans())
        fabric.inject("a", "eth0", A, UNKNOWN)
        fabric.inject("c", "eth0", A, UNKNOWN)
        self.assertEqual(fabric.mac_table("sw", 10), {A: "p1"})
        self.assertEqual(fabric.mac_table("sw", 20), {A: "p3"})
        r = fabric.inject("b", "eth0", B, A)
        self.assertEqual([x["node"] for x in r["endpointArrivals"]], ["a"])
        snapshot = fabric.mac_table("sw", 20)
        snapshot.clear()
        self.assertEqual(fabric.mac_table("sw", 20), {A: "p3"})
        with self.assertRaises(ProjectValidationError):
            fabric.mac_table("sw")
        with self.assertRaises(ProjectValidationError):
            fabric.mac_table("sw", True)

    def test_trunk_tagging_and_access_untagged_on_both_sides(self):
        p, ports = two_switches()
        original = copy.deepcopy(p)
        fabric = EthernetFabric(p, vlan_ports=ports)
        r = fabric.inject("a", "eth0", A, BROADCAST)
        self.assertEqual([x["linkId"] for x in r["transmissions"]], ["la", "lt", "lb"])
        self.assertEqual([x["tagged"] for x in r["transmissions"]], [False, True, False])
        self.assertEqual([x["vlanId"] for x in r["transmissions"]], [None, 10, 10])
        self.assertEqual([x["node"] for x in r["endpointArrivals"]], ["b"])
        self.assertEqual(fabric.mac_table("s1", 10), {A: "h"})
        self.assertEqual(fabric.mac_table("s2", 10), {A: "t"})
        self.assertEqual(fabric.mac_table("s1", 20), {})
        c = fabric.inject("c", "eth0", C, BROADCAST)
        self.assertEqual([x["linkId"] for x in c["transmissions"]], ["lc", "lt", "ld"])
        self.assertEqual([x["node"] for x in c["endpointArrivals"]], ["d"])
        self.assertEqual(c["transmissions"][1]["vlanId"], 20)
        self.assertEqual(p, original)

    def test_known_unicast_uses_vlan_specific_learning(self):
        p, ports = two_switches()
        fabric = EthernetFabric(p, vlan_ports=ports)
        fabric.inject("b", "eth0", B, A)
        r = fabric.inject("a", "eth0", A, B)
        self.assertEqual([x["linkId"] for x in r["transmissions"]], ["la", "lt", "lb"])
        self.assertEqual([x["node"] for x in r["endpointArrivals"]], ["b"])
        self.assertEqual([x["action"] for x in r["switchDecisions"]],
                         ["FORWARD_UNICAST", "FORWARD_UNICAST"])

    def test_mismatched_trunk_allow_list_drops_without_learning(self):
        p, ports = two_switches()
        ports[("s2", "t")] = trunk(20)
        fabric = EthernetFabric(p, vlan_ports=ports)
        r = fabric.inject("a", "eth0", A, BROADCAST)
        self.assertEqual([x["linkId"] for x in r["transmissions"]], ["la", "lt"])
        self.assertEqual(r["endpointArrivals"], [])
        self.assertEqual(r["vlanDrops"],
                         [{"switch": "s2", "port": "t", "reason": "TRUNK_NOT_ALLOWED", "vlanId": 10}])
        self.assertEqual(fabric.mac_table("s1", 10), {A: "h"})
        self.assertEqual(fabric.mac_table("s2", 10), {})

    def test_deactivated_link_or_port_is_not_transmitted(self):
        p, ports = two_switches()
        p["links"][1]["enabled"] = False
        r = EthernetFabric(p, vlan_ports=ports).inject("a", "eth0", A, BROADCAST)
        self.assertEqual([x["linkId"] for x in r["transmissions"]], ["la"])
        self.assertEqual(r["endpointArrivals"], [])
        p["nodes"][1]["ports"][0]["enabled"] = False
        fabric = EthernetFabric(p, vlan_ports=ports)
        self.assertEqual(fabric.inject("a", "eth0", A, BROADCAST)["status"], "NO_ACTIVE_LINK")
        self.assertEqual(fabric.mac_table("s1", 10), {})

    def test_no_vlan_config_is_ever_inferred_and_no_project_mutation(self):
        p, ports = two_switches()
        original = copy.deepcopy(p)
        with self.assertRaisesRegex(ProjectValidationError, "missing configuration"):
            EthernetFabric(p, vlan_ports={})
        fabric = EthernetFabric(p, vlan_ports=ports)
        ports[("s1", "h")]["vlan"] = 999
        fabric.inject("a", "eth0", A, BROADCAST)
        self.assertEqual(fabric.mac_table("s1", 10), {A: "h"})
        self.assertEqual(p, original)
        self.assertTrue(all("vlan" not in port for n in p["nodes"] for port in n["ports"]))

    def test_invalid_access_trunk_and_port_identifiers_are_rejected(self):
        p, cfg = two_switches()
        bad = [
            {("s1", "h"): access(0)},
            {("s1", "h"): access(4095)},
            {("s1", "h"): access(True)},
            {("s1", "h"): access("10")},
            {("s1", "t"): trunk(10, 10)},
            {("s1", "t"): trunk()},
            {("s1", "t"): trunk(0)},
            {("s1", "t"): {"mode": "trunk", "allowedVlans": "10"}},
            {("s1", "h"): {"mode": "access", "vlan": 10, "native": 10}},
            {("s1", "h"): {"mode": "native"}},
            {("a", "eth0"): access(10)},
            {("s1", "missing"): access(10)},
            {"s1/h": access(10)},
            {("s1", "h"): None},
        ]
        for change in bad:
            with self.subTest(change=change):
                incorrect = copy.deepcopy(cfg)
                incorrect.update(change)
                with self.assertRaises(ProjectValidationError):
                    EthernetFabric(p, vlan_ports=incorrect)
        with self.assertRaises(ProjectValidationError):
            EthernetFabric(p, vlan_ports=[])

    def test_host_trunk_and_incompatible_switch_link_fail(self):
        p, cfg = two_switches()
        wrong = copy.deepcopy(cfg)
        wrong[("s1", "h")] = trunk(10)
        with self.assertRaisesRegex(ProjectValidationError, "endpoint links"):
            EthernetFabric(p, vlan_ports=wrong)
        wrong = copy.deepcopy(cfg)
        wrong[("s1", "t")] = access(10)
        with self.assertRaisesRegex(ProjectValidationError, "incompatible"):
            EthernetFabric(p, vlan_ports=wrong)
        wrong = copy.deepcopy(cfg)
        wrong[("s1", "t")] = access(10)
        wrong[("s2", "t")] = access(20)
        with self.assertRaisesRegex(ProjectValidationError, "incompatible"):
            EthernetFabric(p, vlan_ports=wrong)

    def test_legacy_without_vlan_ports_remains_unchanged(self):
        f = EthernetFabric(star())
        f.inject("a", "eth0", A, B)
        self.assertEqual(f.mac_table("sw"), {A: "p1"})
        with self.assertRaisesRegex(ProjectValidationError, "no VLAN session"):
            f.mac_table("sw", 10)


if __name__ == "__main__":
    unittest.main()
