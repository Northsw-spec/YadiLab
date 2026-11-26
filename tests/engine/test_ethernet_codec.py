import unittest
from binascii import crc32
from dataclasses import replace
from ipaddress import IPv4Address

from core.engine.config import ConfigError
from core.engine.ethernet.codec import (
    ARP_TYPE, BROADCAST, ZERO_MAC, ARPMessage, ARPOperation, EthernetFrame, WireError, WireErrorCode,
)
from core.engine.ethernet.config import AccessPort, HostSettings, LinkTiming
from poc1_fixture import A, A_IP, A_MAC, B_IP, B_MAC, REPLY, REQUEST, scenario


class EthernetCodecTests(unittest.TestCase):
    def test_exact_wire_headers_padding_and_little_endian_fcs(self):
        packet = ARPMessage(ARPOperation.REQUEST, A_MAC, IPv4Address(A_IP).packed,
                            ZERO_MAC, IPv4Address(B_IP).packed)
        frame = EthernetFrame(BROADCAST, A_MAC, ARP_TYPE, packet.encode())
        self.assertEqual(frame.encode(), REQUEST)
        self.assertEqual(REQUEST[:14], bytes.fromhex("ffffffffffff02000000000a0806"))
        self.assertEqual(REQUEST[42:60], bytes(18))
        self.assertEqual(REQUEST[-4:], bytes.fromhex("f341ec0e"))
        decoded = EthernetFrame.decode(REQUEST)
        self.assertEqual((decoded.destination, decoded.source, decoded.ethertype), (BROADCAST, A_MAC, 0x0806))
        self.assertEqual(decoded.encode(), REQUEST)
        full = EthernetFrame(A_MAC, B_MAC, 0x88B5, bytes(1500))
        self.assertEqual(len(full.encode()), 1518)
        self.assertEqual(EthernetFrame.decode(full.encode()), full)

    def assert_wire_error(self, code, call, *args):
        with self.assertRaises(WireError) as exc:
            call(*args)
        self.assertIs(exc.exception.code, code)

    def test_frame_size_mac_crc_and_encapsulation_rejections(self):
        self.assert_wire_error(WireErrorCode.INVALID_FCS, EthernetFrame.decode,
                               REQUEST[:-1] + bytes([REQUEST[-1] ^ 1]))
        for wire in (REQUEST[:-1], b"x" * 1519):
            self.assert_wire_error(WireErrorCode.INVALID_FRAME, EthernetFrame.decode, wire)
        for mac in (ZERO_MAC, BROADCAST, b"short", "02:00:00:00:00:0a"):
            self.assert_wire_error(WireErrorCode.INVALID_FRAME, EthernetFrame, A_MAC, mac, 0x806, b"")
        self.assert_wire_error(WireErrorCode.INVALID_FRAME, EthernetFrame, b"", A_MAC, 0x806, b"")
        self.assert_wire_error(WireErrorCode.INVALID_FRAME, EthernetFrame, B_MAC, A_MAC, 65536, b"")
        for field in (46, 1501, 0x8100, 0x88A8):
            body = REQUEST[:12] + field.to_bytes(2, "big") + REQUEST[14:-4]
            raw = body + crc32(body).to_bytes(4, "little")
            self.assert_wire_error(WireErrorCode.UNSUPPORTED_FORMAT, EthernetFrame.decode, raw)

    def test_arp_request_and_reply_vectors_and_padding(self):
        self.assertEqual(REQUEST[14:42].hex(),
                         "000108000604000102000000000ac0a80a0a000000000000c0a80a14")
        self.assertEqual(REPLY[14:42].hex(),
                         "000108000604000202000000000bc0a80a1402000000000ac0a80a0a")
        reply = ARPMessage(ARPOperation.REPLY, B_MAC, IPv4Address(B_IP).packed,
                           A_MAC, IPv4Address(A_IP).packed)
        self.assertEqual(EthernetFrame(A_MAC, B_MAC, ARP_TYPE, reply.encode()).encode(), REPLY)
        self.assertEqual(REPLY[-4:], bytes.fromhex("16c3bc33"))
        self.assertEqual(ARPMessage.decode(REPLY[14:42] + b"x" * 18), reply)
        self.assertEqual(ARPMessage.decode(REPLY[14:42]), reply)

    def test_arp_requires_ethernet_ipv4_header_and_supported_opcode(self):
        arp = REQUEST[14:42]
        for index, value, error in (
            (1, 2, WireErrorCode.UNSUPPORTED_ARP), (2, 0x86, WireErrorCode.UNSUPPORTED_ARP),
            (4, 5, WireErrorCode.INVALID_ARP), (5, 6, WireErrorCode.INVALID_ARP),
            (7, 3, WireErrorCode.UNSUPPORTED_ARP),
        ):
            with self.subTest(index=index):
                self.assert_wire_error(error, ARPMessage.decode, arp[:index] + bytes([value]) + arp[index + 1:])
        for data in (arp[:-1], arp + bytes(19)):
            self.assert_wire_error(WireErrorCode.INVALID_ARP, ARPMessage.decode, data)


class EthernetConfigTests(unittest.TestCase):
    def test_rejects_invalid_link_rate_propagation_and_port_settings(self):
        for rate, delay in ((0, 0), (-1, 0), (True, 0), (100, -1), (100, 1 << 63), (1 << 63, 0)):
            with self.subTest(rate=rate, delay=delay), self.assertRaises(ConfigError):
                LinkTiming("link", rate, delay)
        for vlan, budget in ((0, 1), (4095, 1), (10, 0), ("trunk", 1)):
            with self.subTest(vlan=vlan, budget=budget), self.assertRaises(ConfigError):
                AccessPort(A, vlan, budget)

    def test_explicit_settings_require_real_unique_endpoints_and_addresses(self):
        model = scenario().config
        with self.assertRaisesRegex(ConfigError, "access settings"):
            replace(model, ports=model.ports[:-1])
        with self.assertRaisesRegex(ConfigError, "link timing"):
            replace(model, links=model.links[:-1])
        for address in ("192.168.10.10", "192.168.10.0/24", "224.0.0.1/24", "::1/64"):
            with self.subTest(address=address), self.assertRaises(ConfigError):
                HostSettings(A, A_MAC, address, 1, 1, 10)
        with self.assertRaises(ConfigError):
            HostSettings(A, BROADCAST, A_IP + "/24", 1, 1, 10)
