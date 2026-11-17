"""Independent Ethernet II format and session-binding tests.

Tests check exact Ethernet header bytes, 802.3 rejection, padding behavior,
explicit source identity, and no mutation of canonical project data.
"""
import copy
import unittest

from network_core.ethernet import EthernetFabric
from network_core.ethernet_frame import EthernetFrame
from network_core.model import ProjectValidationError
from test_ethernet import A, B, UNKNOWN, star


class EthernetFrameTests(unittest.TestCase):
    def frame(self, *, payload=b"abcd", ether_type=0x88B5, source=A, destination=B):
        return EthernetFrame(destination, source, ether_type, payload)

    def test_exact_header_and_minimum_padding(self):
        frame = self.frame(payload=b"ABCD")
        raw = frame.serialize()
        self.assertEqual(len(raw), 60)
        self.assertEqual(raw[:6], bytes.fromhex(B.replace(":", "")))
        self.assertEqual(raw[6:12], bytes.fromhex(A.replace(":", "")))
        self.assertEqual(raw[12:14], b"\x88\xb5")
        self.assertEqual(raw[14:18], b"ABCD")
        self.assertEqual(raw[18:], b"\x00" * 42)

    def test_full_size_payload_and_roundtrip(self):
        data = bytes(range(256)) * 5 + bytes(range(220))
        self.assertEqual(len(data), 1500)
        frame = self.frame(payload=data, ether_type=0x0800)
        raw = frame.serialize()
        self.assertEqual(len(raw), 1514)
        self.assertEqual(EthernetFrame.parse(raw), frame)

    def test_parse_keeps_padding_as_opaque_payload(self):
        frame = self.frame(payload=b"123")
        parsed = EthernetFrame.parse(frame.serialize())
        self.assertEqual(len(parsed.payload), 46)
        self.assertEqual(parsed.payload, b"123" + b"\x00" * 43)
        self.assertEqual(parsed.serialize(), frame.serialize())

    def test_uppercase_normalization(self):
        frame = self.frame(source=A.lower(), destination=B.lower())
        self.assertEqual((frame.source, frame.destination), (A, B))
        self.assertEqual(EthernetFrame.parse(frame.serialize()).source, A)

    def test_source_must_be_valid_unicast(self):
        for src in ("ff:ff:ff:ff:ff:ff", "01:00:5E:00:00:01", "00:00:00:00:00:00", "foo", None, 4):
            with self.subTest(src=src), self.assertRaises(ProjectValidationError):
                self.frame(source=src)

    def test_destination_must_be_supported(self):
        frame = self.frame(destination="ff:ff:ff:ff:ff:ff")
        self.assertEqual(frame.destination, "FF:FF:FF:FF:FF:FF")
        for dest in ("01:00:5e:00:00:01", "bad", None):
            with self.subTest(dest=dest), self.assertRaises(ProjectValidationError):
                self.frame(destination=dest)

    def test_ether_type_rejects_lengths_reserved_values_and_vlan(self):
        for value in (0x0000, 1500, 1501, 1535, 65536, 0x8100, 0x88A8, 0x9100, "0x0800", True):
            with self.subTest(value=value), self.assertRaises(ProjectValidationError):
                self.frame(ether_type=value)

    def test_raw_parser_rejects_8023_length_and_vlan_tag(self):
        raw = bytearray(self.frame(payload=b"." * 46).serialize())
        for raw_type in (b"\x05\xdc", b"\x81\x00", b"\x88\xa8"):
            with self.subTest(raw_type=raw_type), self.assertRaises(ProjectValidationError):
                EthernetFrame.parse(bytes(raw[:12]) + raw_type + bytes(raw[14:]))

    def test_rejects_nonbytes_payload_and_oversize(self):
        for data in (bytearray(b"a"), "text", None, memoryview(b"ok"), b"0" * 1501):
            with self.subTest(type=str(type(data))), self.assertRaises(ProjectValidationError):
                self.frame(payload=data)
        self.assertEqual(len(self.frame(payload=b"").serialize()), 60)

    def test_raw_must_be_bytes_and_exact_unfcs_length(self):
        for raw in (None, "", bytearray(b"\x00" * 60), b"\x00" * 59, b"\x00" * 1515):
            with self.subTest(raw=type(raw).__name__), self.assertRaises(ProjectValidationError):
                EthernetFrame.parse(raw)


class ExplicitNicIdentityTests(unittest.TestCase):
    def make(self, bindings=None):
        return EthernetFabric(star(), interface_macs=bindings)

    def frame(self, source=A, destination=UNKNOWN):
        return EthernetFrame(destination, source, 0x88B5, b"hello")

    def test_configured_source_forwards_and_learns(self):
        e = self.make({("a", "eth0"): A})
        result = e.inject_frame("a", "eth0", self.frame())
        self.assertEqual(result["status"], "SIMULATED")
        self.assertEqual([x["linkId"] for x in result["transmissions"]], ["la", "lb", "lc"])
        self.assertEqual(e.mac_table("sw"), {A: "p1"})
        self.assertEqual(result["frame"], {"source": A, "destination": UNKNOWN,
                                           "etherType": 0x88B5, "lengthWithoutFcs": 60})

    def test_unbound_source_does_not_transmit_or_learn(self):
        e = self.make()
        with self.assertRaisesRegex(ProjectValidationError, "no explicit MAC binding"):
            e.inject_frame("a", "eth0", self.frame())
        self.assertEqual(e.mac_table("sw"), {})

    def test_wrong_source_mac_cannot_spoof_configured_interface(self):
        e = self.make({("a", "eth0"): A})
        with self.assertRaisesRegex(ProjectValidationError, "does not match"):
            e.inject_frame("a", "eth0", self.frame(source=B))
        self.assertEqual(e.mac_table("sw"), {})

    def test_undeclared_bindings_and_switch_binding_rejected(self):
        for assignments in ({("phantom", "p"): A}, {("a", "fake"): A},
                            {("sw", "p1"): A}, {"a/eth0": A}, [A]):
            with self.subTest(assignments=str(assignments)), self.assertRaises(ProjectValidationError):
                self.make(assignments)

    def test_duplicate_bound_addresses_rejected_even_with_mixed_case(self):
        with self.assertRaisesRegex(ProjectValidationError, "duplicate interface MAC"):
            self.make({("a", "eth0"): A, ("b", "eth0"): A.lower()})

    def test_invalid_binding_mac_rejected(self):
        for addr in (None, "abc", "01:00:5E:00:00:01", "00:00:00:00:00:00"):
            with self.subTest(addr=addr), self.assertRaises(ProjectValidationError):
                self.make({("a", "eth0"): addr})

    def test_binding_snapshots_not_mutable_alias_and_project_unchanged(self):
        p = star()
        original = copy.deepcopy(p)
        source = {("a", "eth0"): A}
        e = EthernetFabric(p, interface_macs=source)
        source[("a", "eth0")] = B
        snapshot = e.bound_macs()
        snapshot[("a", "eth0")] = B
        self.assertEqual(e.bound_macs(), {("a", "eth0"): A})
        e.inject_frame("a", "eth0", self.frame())
        self.assertEqual(p, original)

    def test_different_sessions_require_explicit_bindings(self):
        self.make({("a", "eth0"): A}).inject_frame("a", "eth0", self.frame())
        other = self.make()
        with self.assertRaises(ProjectValidationError):
            other.inject_frame("a", "eth0", self.frame())
        self.assertEqual(other.mac_table("sw"), {})

    def test_injected_frame_remains_opaque_even_when_ethertype_is_arp(self):
        e = self.make({("a", "eth0"): A})
        arp_bytes = b"\xff" * 28
        frame = EthernetFrame(B, A, 0x0806, arp_bytes)
        result = e.inject_frame("a", "eth0", frame)
        self.assertEqual(result["frame"]["etherType"], 0x0806)
        self.assertNotIn("arp", result)
        self.assertNotIn("ip", result)
        self.assertEqual(e.mac_table("sw"), {A: "p1"})

    def test_no_active_link_remains_non_transmission(self):
        p = star()
        p["links"][0]["enabled"] = False
        e = EthernetFabric(p, interface_macs={("a", "eth0"): A})
        r = e.inject_frame("a", "eth0", self.frame())
        self.assertEqual(r["status"], "NO_ACTIVE_LINK")
        self.assertEqual(r["transmissions"], [])
        self.assertEqual(e.mac_table("sw"), {})


if __name__ == "__main__":
    unittest.main()
