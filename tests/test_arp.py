"""Independent byte-level and wiring tests for explicit IPv4-over-Ethernet ARP."""
import copy
import unittest
from dataclasses import FrozenInstanceError

from network_core.arp import ArpMessage, ArpSession
from network_core.ethernet_frame import EthernetFrame
from network_core.model import ProjectValidationError
from test_ethernet import A, B, C, star


ZERO = "00:00:00:00:00:00"


def network():
    p = star()
    p['nodes'][0]['ports'][0]['ipv4'] = '192.0.2.10/24'
    p['nodes'][2]['ports'][0]['ipv4'] = '192.0.2.20/24'
    p['nodes'][3]['ports'][0]['ipv4'] = '192.0.2.30/24'
    return p


def bindings():
    return {('a', 'eth0'): A, ('b', 'eth0'): B, ('c', 'eth0'): C}


class ArpMessageTests(unittest.TestCase):
    def test_request_exact_rfc826_bytes(self):
        r = ArpMessage(1, A, '192.0.2.10', ZERO, '192.0.2.20')
        expected = (bytes.fromhex('0001 0800 06 04 0001') + bytes.fromhex('02000000000A')
                    + bytes([192, 0, 2, 10]) + bytes(6) + bytes([192, 0, 2, 20]))
        self.assertEqual(r.serialize(), expected)
        self.assertEqual(len(expected), 28)
        self.assertEqual(ArpMessage.parse(expected), r)
        self.assertEqual(r.to_frame().destination, 'FF:FF:FF:FF:FF:FF')
        self.assertEqual(r.to_frame().ether_type, 0x0806)

    def test_reply_exact_bytes_and_unicast_envelope(self):
        r = ArpMessage(2, B, '192.0.2.20', A, '192.0.2.10')
        self.assertEqual(r.serialize()[:8], bytes.fromhex('0001 0800 06 04 0002'))
        self.assertEqual(r.to_frame().destination, A)
        self.assertEqual(ArpMessage.parse(r.serialize()), r)
        self.assertEqual(ArpMessage.from_frame(EthernetFrame.parse(r.to_frame().serialize())), r)

    def test_request_frame_roundtrip_includes_zero_ethernet_padding(self):
        r = ArpMessage(1, A, '192.0.2.10', ZERO, '192.0.2.20')
        wire = r.to_frame().serialize()
        self.assertEqual(len(wire), 60)
        self.assertEqual(wire[42:], bytes(18))
        self.assertEqual(ArpMessage.from_frame(EthernetFrame.parse(wire)), r)

    def test_reject_wrong_arp_headers(self):
        good = ArpMessage(1, A, '192.0.2.10', ZERO, '192.0.2.20').serialize()
        for position, replacement in [(0, 2), (2, 0), (4, 4), (5, 16), (7, 3)]:
            bad = bytearray(good)
            bad[position] = replacement
            with self.subTest(position=position), self.assertRaises(ProjectValidationError):
                ArpMessage.parse(bytes(bad))

    def test_reject_non_bytes_and_wrong_payload_lengths(self):
        good = ArpMessage(1, A, '192.0.2.10', ZERO, '192.0.2.20').serialize()
        for payload in (None, good[:-1], good + b'\x00', bytearray(good)):
            with self.subTest(payload=payload), self.assertRaises(ProjectValidationError):
                ArpMessage.parse(payload)

    def test_reject_invalid_operations_and_macs(self):
        for opcode in (True, 0, 3, -1, '1'):
            with self.subTest(opcode=opcode), self.assertRaises(ProjectValidationError):
                ArpMessage(opcode, A, '192.0.2.10', ZERO, '192.0.2.20')
        with self.assertRaisesRegex(ProjectValidationError, 'target MAC'):
            ArpMessage(1, A, '192.0.2.10', B, '192.0.2.20')
        with self.assertRaises(ProjectValidationError):
            ArpMessage(2, B, '192.0.2.20', ZERO, '192.0.2.10')

    def test_reject_invalid_ip(self):
        for ip in ('garbage', '::1', '0.0.0.0', '224.0.0.1', '255.255.255.255', None):
            with self.subTest(ip=ip), self.assertRaises(ProjectValidationError):
                ArpMessage(1, A, ip, ZERO, '192.0.2.20')

    def test_reject_mismatched_ethernet_envelope_and_noncanonical_padding(self):
        r = ArpMessage(1, A, '192.0.2.10', ZERO, '192.0.2.20')
        for f in (EthernetFrame(B, A, 0x0806, r.serialize()),
                  EthernetFrame('FF:FF:FF:FF:FF:FF', B, 0x0806, r.serialize()),
                  EthernetFrame('FF:FF:FF:FF:FF:FF', A, 0x0800, r.serialize()),
                  EthernetFrame('FF:FF:FF:FF:FF:FF', A, 0x0806, r.serialize() + b'\x01')):
            with self.subTest(frame=f), self.assertRaises(ProjectValidationError):
                ArpMessage.from_frame(f)

    def test_message_is_immutable(self):
        r = ArpMessage(1, A, '192.0.2.10', ZERO, '192.0.2.20')
        with self.assertRaises(FrozenInstanceError):
            r.sender_mac = B


class ArpSessionTests(unittest.TestCase):
    def test_request_broadcast_then_learned_unicast_reply(self):
        session = ArpSession(network(), interface_macs=bindings())
        r = session.resolve('a', 'eth0', '192.0.2.20')
        self.assertEqual(r['status'], 'RESOLVED')
        self.assertEqual(r['resolvedMac'], B)
        self.assertEqual([x['linkId'] for x in r['requestTransmissions']], ['la', 'lb', 'lc'])
        self.assertEqual([x['linkId'] for x in r['replyTransmissions']], ['lb', 'la'])
        self.assertEqual(session.arp_table('a', 'eth0'), {'192.0.2.20': B})
        self.assertEqual(session.fabric.mac_table('sw'), {A: 'p1', B: 'p2'})

    def test_cache_hit_never_generates_new_frames(self):
        session = ArpSession(network(), interface_macs=bindings())
        session.resolve('a', 'eth0', '192.0.2.20')
        r = session.resolve('a', 'eth0', '192.0.2.20')
        self.assertEqual(r['status'], 'CACHE_HIT')
        self.assertEqual(r['requestTransmissions'], [])
        self.assertEqual(r['replyTransmissions'], [])

    def test_unknown_ip_returns_no_reply_but_does_not_invent_endpoint(self):
        session = ArpSession(network(), interface_macs=bindings())
        r = session.resolve('a', 'eth0', '192.0.2.200')
        self.assertEqual(r['status'], 'NO_REPLY')
        self.assertIsNone(r['resolvedMac'])
        self.assertEqual(session.arp_table('a', 'eth0'), {})

    def test_missing_mac_on_target_is_unknown_not_fabricated_reply(self):
        m = bindings(); m.pop(('b', 'eth0'))
        session = ArpSession(network(), interface_macs=m)
        self.assertEqual(session.resolve('a', 'eth0', '192.0.2.20')['status'], 'UNKNOWN')
        self.assertEqual(session.arp_table('a', 'eth0'), {})

    def test_disabled_target_cable_means_no_reply(self):
        p = network();p['links'][1]['enabled'] = False
        session = ArpSession(p, interface_macs=bindings())
        r = session.resolve('a', 'eth0', '192.0.2.20')
        self.assertEqual(r['status'], 'NO_REPLY')
        self.assertEqual([x['linkId'] for x in r['requestTransmissions']], ['la', 'lc'])

    def test_disabled_source_link_cannot_send_request(self):
        p = network();p['links'][0]['enabled'] = False
        session = ArpSession(p, interface_macs=bindings())
        self.assertEqual(session.resolve('a', 'eth0', '192.0.2.20')['status'], 'NO_ACTIVE_LINK')
        self.assertEqual(session.arp_table('a', 'eth0'), {})

    def test_no_cable_no_invented_exchange(self):
        p = network();p['links'] = []
        session = ArpSession(p, interface_macs=bindings())
        self.assertEqual(session.resolve('a', 'eth0', '192.0.2.20')['status'], 'NO_ACTIVE_LINK')

    def test_requires_explicit_source_mac_and_ipv4(self):
        macs = bindings();macs.pop(('a', 'eth0'))
        with self.assertRaises(ProjectValidationError):
            ArpSession(network(),interface_macs=macs).resolve('a', 'eth0', '192.0.2.20')
        p = network();p['nodes'][0]['ports'][0]['ipv4'] = None
        with self.assertRaises(ProjectValidationError):
            ArpSession(p,interface_macs=bindings()).resolve('a', 'eth0', '192.0.2.20')

    def test_reject_off_subnet_and_self_ip(self):
        session = ArpSession(network(), interface_macs=bindings())
        for address in ('198.51.100.20', '192.0.2.10'):
            with self.subTest(address=address), self.assertRaises(ProjectValidationError):
                session.resolve('a', 'eth0', address)
        self.assertEqual(session.arp_table('a', 'eth0'), {})

    def test_duplicate_declared_ipv4_is_rejected(self):
        p=network();p['nodes'][3]['ports'][0]['ipv4']='192.0.2.20/24'
        with self.assertRaisesRegex(ProjectValidationError, 'duplicate declared'):
            ArpSession(p,interface_macs=bindings())

    def test_reject_undeclared_source(self):
        session=ArpSession(network(), interface_macs=bindings())
        with self.assertRaisesRegex(ProjectValidationError,'undeclared'):
            session.resolve('fake', 'eth0', '192.0.2.20')
        with self.assertRaisesRegex(ProjectValidationError,'undeclared'):
            session.arp_table('fake', 'eth0')

    def test_cache_is_detached_and_project_unchanged(self):
        p=network();original=copy.deepcopy(p)
        session=ArpSession(p,interface_macs=bindings())
        session.resolve('a', 'eth0', '192.0.2.20')
        table=session.arp_table('a', 'eth0');table.clear()
        self.assertEqual(session.arp_table('a', 'eth0'), {'192.0.2.20': B})
        self.assertEqual(p, original)
        self.assertEqual(p['schemaVersion'], '1.0')

    def test_no_router_bridging_or_fake_ip_reachability(self):
        from test_ethernet import node, link
        from network_core.model import blank_project
        p=blank_project('No bridging')
        p['nodes']=[node('a','host',['e']),node('r','router',['a','b']),node('b','host',['e'])]
        p['nodes'][0]['ports'][0]['ipv4']='192.0.2.10/24'
        p['nodes'][1]['ports'][0]['ipv4']='192.0.2.1/24'
        p['nodes'][1]['ports'][1]['ipv4']='198.51.100.1/24'
        p['nodes'][2]['ports'][0]['ipv4']='192.0.2.20/24'
        p['links']=[link('l1','a','e','r','a'),link('l2','r','b','b','e')]
        session=ArpSession(p, interface_macs={('a','e'):A,('r','a'):C,('r','b'):'02:00:00:00:00:0D',('b','e'):B})
        result=session.resolve('a','e','192.0.2.20')
        self.assertEqual(result['status'],'NO_REPLY')
        self.assertEqual([x['linkId'] for x in result['requestTransmissions']],['l1'])


if __name__ == '__main__':
    unittest.main()
