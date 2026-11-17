"""ARP over explicit VLANs: independent broadcast-domain and return-wire tests.

Uses the same EthernetFabric and wiring as standard ARP and VLAN tests.
No separate forwarding graph is allowed.
"""
import copy
import tempfile
import unittest
from pathlib import Path

from network_core.arp import ArpSession
from network_core.model import ProjectValidationError
from network_core.storage import ProjectStore
from test_arp import bindings, network
from test_ethernet import A, B, C
from test_vlan import star_vlans, two_switches, trunk


D = "02:00:00:00:00:0D"


def two_switch_arp():
    project, ports = two_switches()
    nodes = {n["id"]: n for n in project["nodes"]}
    for node_id, ip in (("a", "192.0.2.10/24"), ("b", "192.0.2.20/24"),
                        ("c", "192.0.2.30/24"), ("d", "192.0.2.40/24")):
        nodes[node_id]["ports"][0]["ipv4"] = ip
    macs = {("a", "eth0"): A, ("b", "eth0"): B,
            ("c", "eth0"): C, ("d", "eth0"): D}
    return project, ports, macs


class VlanArpTests(unittest.TestCase):
    def test_request_and_reply_in_same_access_vlan(self):
        session = ArpSession(network(), interface_macs=bindings(),
                             vlan_ports=star_vlans())
        result = session.resolve("a", "eth0", "192.0.2.20")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["resolvedMac"], B)
        self.assertEqual([t["linkId"] for t in result["requestTransmissions"]], ["la", "lb"])
        self.assertEqual([t["linkId"] for t in result["replyTransmissions"]], ["lb", "la"])
        self.assertEqual(result["requestVlanDrops"], [])
        self.assertEqual(result["replyVlanDrops"], [])
        self.assertEqual(session.arp_table("a", "eth0"), {"192.0.2.20": B})
        self.assertEqual(session.fabric.mac_table("sw", 10), {A: "p1", B: "p2"})
        self.assertEqual(session.fabric.mac_table("sw", 20), {})

    def test_same_ipv4_subnet_is_not_a_vlans_crossing(self):
        session = ArpSession(network(), interface_macs=bindings(),
                             vlan_ports=star_vlans())
        # Host c shares IPv4 /24 with a/b but is on VLAN 20.
        r = session.resolve("a", "eth0", "192.0.2.30")
        self.assertEqual(r["status"], "NO_REPLY")
        self.assertIsNone(r["resolvedMac"])
        self.assertEqual([t["linkId"] for t in r["requestTransmissions"]], ["la", "lb"])
        self.assertEqual(r["replyTransmissions"], [])
        self.assertEqual(session.arp_table("a", "eth0"), {})
        self.assertEqual(session.fabric.mac_table("sw", 20), {})
        # And the reverse direction cannot leak across VLANs either.
        other = session.resolve("c", "eth0", "192.0.2.10")
        self.assertEqual(other["status"], "NO_REPLY")
        self.assertEqual([t["linkId"] for t in other["requestTransmissions"]], ["lc"])
        self.assertEqual(session.arp_table("c", "eth0"), {})
        self.assertEqual(session.fabric.mac_table("sw", 20), {C: "p3"})

    def test_mac_missing_in_other_vlan_is_no_reply_not_unknown(self):
        macs = bindings()
        del macs[("c", "eth0")]
        session = ArpSession(network(), interface_macs=macs,
                             vlan_ports=star_vlans())
        self.assertEqual(session.resolve("a", "eth0", "192.0.2.30")["status"],
                         "NO_REPLY")
        self.assertEqual(session.arp_table("a", "eth0"), {})
        # Missing MAC in a reachable, same-VLAN responder is UNKNOWN.
        macs = bindings()
        del macs[("b", "eth0")]
        session = ArpSession(network(), interface_macs=macs,
                             vlan_ports=star_vlans())
        self.assertEqual(session.resolve("a", "eth0", "192.0.2.20")["status"],
                         "UNKNOWN")
        self.assertEqual(session.arp_table("a", "eth0"), {})

    def test_valid_arp_over_two_switch_trunk_and_vlan_isolated_learning(self):
        project, ports, macs = two_switch_arp()
        original = copy.deepcopy(project)
        session = ArpSession(project, interface_macs=macs, vlan_ports=ports)
        reply = session.resolve("a", "eth0", "192.0.2.20")
        self.assertEqual(reply["status"], "RESOLVED")
        self.assertEqual([t["linkId"] for t in reply["requestTransmissions"]],
                         ["la", "lt", "lb"])
        self.assertEqual([t["linkId"] for t in reply["replyTransmissions"]],
                         ["lb", "lt", "la"])
        self.assertEqual([t["tagged"] for t in reply["requestTransmissions"]],
                         [False, True, False])
        self.assertEqual(reply["requestTransmissions"][1]["vlanId"], 10)
        self.assertEqual(reply["replyTransmissions"][1]["vlanId"], 10)
        self.assertEqual(session.fabric.mac_table("s1", 10), {A: "h", B: "t"})
        self.assertEqual(session.fabric.mac_table("s2", 10), {A: "t", B: "h"})
        self.assertEqual(session.fabric.mac_table("s1", 20), {})
        self.assertEqual(project, original)

        second = session.resolve("c", "eth0", "192.0.2.40")
        self.assertEqual(second["status"], "RESOLVED")
        self.assertEqual([t["linkId"] for t in second["requestTransmissions"]],
                         ["lc", "lt", "ld"])
        self.assertEqual([t["linkId"] for t in second["replyTransmissions"]],
                         ["ld", "lt", "lc"])
        self.assertEqual(second["requestTransmissions"][1]["vlanId"], 20)
        self.assertEqual(session.fabric.mac_table("s1", 20), {C: "x", D: "t"})
        self.assertEqual(session.fabric.mac_table("s2", 20), {C: "t", D: "x"})
        self.assertEqual(session.arp_table("c", "eth0"), {"192.0.2.40": D})
        # VLAN 10 must not resolve host d on VLAN 20.
        self.assertEqual(session.resolve("a", "eth0", "192.0.2.40")["status"],
                         "NO_REPLY")
        self.assertNotIn("192.0.2.40", session.arp_table("a", "eth0"))

    def test_trunk_allowlist_failure_is_observable_without_fake_cache(self):
        project, ports, macs = two_switch_arp()
        ports[("s2", "t")] = trunk(20)
        session = ArpSession(project, interface_macs=macs, vlan_ports=ports)
        result = session.resolve("a", "eth0", "192.0.2.20")
        self.assertEqual(result["status"], "NO_REPLY")
        self.assertIsNone(result["resolvedMac"])
        self.assertEqual([x["linkId"] for x in result["requestTransmissions"]],
                         ["la", "lt"])
        self.assertEqual(result["replyTransmissions"], [])
        self.assertEqual(result["requestVlanDrops"],
                         [{"switch": "s2", "port": "t",
                           "reason": "TRUNK_NOT_ALLOWED", "vlanId": 10}])
        self.assertEqual(result["replyVlanDrops"], [])
        self.assertEqual(session.fabric.mac_table("s1", 10), {A: "h"})
        self.assertEqual(session.fabric.mac_table("s2", 10), {})
        self.assertEqual(session.arp_table("a", "eth0"), {})
        # Fixing the trunk requires a new session; no stale failure/cache persists.
        ports[("s2", "t")] = trunk(10, 20)
        fresh = ArpSession(project, interface_macs=macs, vlan_ports=ports)
        self.assertEqual(fresh.resolve("a", "eth0", "192.0.2.20")["status"],
                         "RESOLVED")

    def test_missing_trunk_membership_and_misconfigured_ports_rejected(self):
        project, ports, macs = two_switch_arp()
        for alteration in ("missing", "invalid", "wrong-port"):
            with self.subTest(alteration=alteration):
                broken = copy.deepcopy(ports)
                if alteration == "missing":
                    del broken[("s1", "t")]
                elif alteration == "invalid":
                    broken[("s1", "t")] = trunk(0)
                else:
                    broken[("s1", "typo")] = broken.pop(("s1", "t"))
                with self.assertRaises(ProjectValidationError):
                    ArpSession(project, interface_macs=macs, vlan_ports=broken)
        with self.assertRaisesRegex(ProjectValidationError, "missing configuration"):
            ArpSession(project, interface_macs=macs, vlan_ports={})
        with self.assertRaises(ProjectValidationError):
            ArpSession(project, interface_macs=macs, vlan_ports=[])

    def test_disabled_trunk_or_source_port_never_returns_success(self):
        project, ports, macs = two_switch_arp()
        project["links"][1]["enabled"] = False
        session = ArpSession(project, interface_macs=macs, vlan_ports=ports)
        result = session.resolve("a", "eth0", "192.0.2.20")
        self.assertEqual(result["status"], "NO_REPLY")
        self.assertEqual([t["linkId"] for t in result["requestTransmissions"]],
                         ["la"])
        self.assertEqual(session.arp_table("a", "eth0"), {})
        project["nodes"][0]["ports"][0]["enabled"] = False
        session = ArpSession(project, interface_macs=macs, vlan_ports=ports)
        result = session.resolve("a", "eth0", "192.0.2.20")
        self.assertEqual(result["status"], "NO_ACTIVE_LINK")
        self.assertEqual(result["requestVlanDrops"], [])
        self.assertEqual(result["replyVlanDrops"], [])
        self.assertEqual(session.arp_table("a", "eth0"), {})

    def test_arp_cache_hit_is_session_only_and_carries_no_new_transmissions(self):
        session = ArpSession(network(), interface_macs=bindings(),
                             vlan_ports=star_vlans())
        session.resolve("a", "eth0", "192.0.2.20")
        cached = session.resolve("a", "eth0", "192.0.2.20")
        self.assertEqual(cached["status"], "CACHE_HIT")
        self.assertEqual(cached["requestTransmissions"], [])
        self.assertEqual(cached["replyTransmissions"], [])
        self.assertEqual(cached["requestVlanDrops"], [])
        self.assertEqual(cached["replyVlanDrops"], [])
        self.assertEqual(ArpSession(network(), interface_macs=bindings(),
                                     vlan_ports=star_vlans()).arp_table("a", "eth0"), {})

    def test_persisted_explicit_macs_work_without_persisting_vlans_or_arp_cache(self):
        project = network()
        for index, mac in ((0, A), (2, B), (3, C)):
            project["nodes"][index]["ports"][0]["mac"] = mac
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp))
            store.save("network", project)
            loaded = ProjectStore(Path(tmp)).read("network")["project"]
            session = ArpSession(loaded, vlan_ports=star_vlans())
            self.assertEqual(session.resolve("a", "eth0", "192.0.2.20")["status"],
                             "RESOLVED")
            stored = ProjectStore(Path(tmp)).read("network")["project"]
            self.assertEqual(stored, loaded)
            self.assertFalse(any("vlan" in port for n in stored["nodes"]
                                 for port in n["ports"]))
            fresh = ArpSession(stored, vlan_ports=star_vlans())
            self.assertEqual(fresh.arp_table("a", "eth0"), {})
            self.assertEqual(fresh.fabric.mac_table("sw", 10), {})
            self.assertEqual(fresh.resolve("a", "eth0", "192.0.2.30")["status"],
                             "NO_REPLY")

    def test_duplicate_ip_is_still_fail_closed_even_across_vlans(self):
        project = network()
        project["nodes"][3]["ports"][0]["ipv4"] = "192.0.2.20/24"
        with self.assertRaisesRegex(ProjectValidationError, "duplicate declared"):
            ArpSession(project, interface_macs=bindings(), vlan_ports=star_vlans())

    def test_legacy_unsegmented_behavior_and_output_still_intact(self):
        session = ArpSession(network(), interface_macs=bindings())
        result = session.resolve("a", "eth0", "192.0.2.30")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual([t["linkId"] for t in result["requestTransmissions"]],
                         ["la", "lb", "lc"])
        self.assertNotIn("requestVlanDrops", result)
        self.assertNotIn("replyVlanDrops", result)
        self.assertEqual(session.fabric.mac_table("sw"), {A: "p1", C: "p3"})


if __name__ == "__main__":
    unittest.main()
