"""Prefix-aware endpoint addresses over declared Ethernet, including legacy files."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from network_core.arp import ArpSession
from network_core.icmp_ping import EchoExchange
from network_core.import_plan import build_plan
from network_core.ipv4 import IPv4Trace
from network_core.model import ProjectValidationError, validate_project
from network_core.routing import ConnectedRoutingTable
from network_core.storage import ProjectStore
from test_icmp_investigation_lan import lan_lab
from test_import_integration_4c import corpus_a
from test_ipv4_forwarding import lab


class IPv4HostAddressTests(unittest.TestCase):
    def test_network_and_broadcast_hosts_cannot_reply(self):
        for address in ('192.168.10.0/24', '192.168.10.255/24'):
            with self.subTest(address=address):
                project = lan_lab()
                project['nodes'][2]['ports'][0]['ipv4'] = address
                with self.assertRaisesRegex(ProjectValidationError, 'network or broadcast'):
                    validate_project(project)
                for operation in (
                    lambda: ArpSession(project).resolve('a', 'eth0', address.split('/')[0]),
                    lambda: IPv4Trace(project).send('a', 'eth0', address.split('/')[0], 5),
                    lambda: EchoExchange(project).ping('a', 'eth0', address.split('/')[0], 5, 12, 1),
                ):
                    with self.assertRaises(ProjectValidationError):
                        operation()

    def test_source_and_prefix_boundaries(self):
        for address in ('192.168.10.0/24', '192.168.10.255/24',
                        '192.0.2.0/30', '192.0.2.3/30',
                        '192.0.2.0/29', '192.0.2.7/29',
                        '192.0.2.0/25', '192.0.2.127/25',
                        '192.0.2.0/23', '192.0.3.255/23',
                        '10.0.0.0/8', '10.255.255.255/8'):
            with self.subTest(address=address):
                project = lan_lab()
                project['nodes'][0]['ports'][0]['ipv4'] = address
                with self.assertRaisesRegex(ProjectValidationError, 'network or broadcast'):
                    validate_project(project)
        for address in ('192.168.10.1/24', '192.168.10.254/24',
                        '192.0.2.1/30', '192.0.2.2/30',
                        '192.0.2.1/29', '192.0.2.126/25',
                        '192.0.3.254/23', '192.0.2.0/31',
                        '192.0.2.1/31', '192.0.2.7/32'):
            with self.subTest(address=address):
                project = lan_lab()
                project['nodes'][0]['ports'][0]['ipv4'] = address
                self.assertEqual(validate_project(project)['nodes'][0]['ports'][0]['ipv4'], address)

    def test_valid_lan_routed_31_and_32(self):
        project = lan_lab()
        result = EchoExchange(project).ping('a', 'eth0', '192.168.10.20', 5, 12, 1)
        self.assertEqual(result['status'], 'REPLIED')
        self.assertEqual(result['request']['steps'][0]['arp']['status'], 'RESOLVED')
        self.assertEqual(len(result['request']['steps'][0]['ipv4Transmissions']), 2)
        self.assertTrue(result['macTables'])
        p31 = copy.deepcopy(project)
        p31['nodes'][0]['ports'][0]['ipv4'] = '192.0.2.0/31'
        p31['nodes'][2]['ports'][0]['ipv4'] = '192.0.2.1/31'
        self.assertEqual(EchoExchange(p31).ping('a', 'eth0', '192.0.2.1', 5, 12, 1)['status'], 'REPLIED')
        p32 = copy.deepcopy(project)
        p32['nodes'][0]['ports'][0]['ipv4'] = '192.0.2.7/32'
        self.assertEqual(ConnectedRoutingTable(p32, 'a').lookup('192.168.10.20')['status'], 'NO_ROUTE')
        self.assertEqual(IPv4Trace(p32).send('a', 'eth0', '192.168.10.20', 5)['status'], 'NO_ROUTE')
        routed = lab()
        self.assertEqual(IPv4Trace(routed).send('a', 'eth0', '203.0.113.20', 5)['status'], 'DELIVERED')

    def test_next_hop_rejected_but_network_route_destination_allowed(self):
        project = lab()
        self.assertEqual(validate_project(project)['nodes'][0]['staticRoutes'][0]['destination'],
                         '203.0.113.0/24')
        for address in ('192.0.2.0', '192.0.2.255'):
            with self.subTest(address=address):
                changed = copy.deepcopy(project)
                changed['nodes'][0]['staticRoutes'][0]['nextHop'] = address
                with self.assertRaisesRegex(ProjectValidationError, 'network or broadcast'):
                    validate_project(changed)

    def test_legacy_original_bytes_survive_rejected_open_and_explicit_correction(self):
        for version in ('1.0', '1.1', '1.2', '1.3'):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                project = lan_lab()
                project['schemaVersion'] = version
                project['nodes'][2]['ports'][0]['ipv4'] = '192.168.10.0/24'
                if version == '1.0':
                    for node in project['nodes']:
                        for port in node['ports']:
                            port.pop('mac', None)
                            port.pop('vlan', None)
                elif version == '1.1':
                    for node in project['nodes']:
                        for port in node['ports']:
                            port.pop('vlan', None)
                original = (json.dumps(project, ensure_ascii=False, indent=2) + '\n').encode()
                path = Path(directory) / 'legacy.yadilab'
                path.write_bytes(original)
                store = ProjectStore(Path(directory))
                with self.assertRaisesRegex(ProjectValidationError, 'network or broadcast'):
                    store.read('legacy')
                with self.assertRaisesRegex(ProjectValidationError, 'network or broadcast'):
                    store.save('legacy', project)
                self.assertEqual(path.read_bytes(), original)
                corrected = copy.deepcopy(project)
                corrected['nodes'][2]['ports'][0]['ipv4'] = '192.168.10.20/24'
                store.save('corrected', corrected)
                self.assertEqual(store.read('corrected')['project']['schemaVersion'], version)
                self.assertEqual(path.read_bytes(), original)

    def test_schema14_legacy_receipt_survives_correction_in_new_file(self):
        request = corpus_a()
        request['selectedUnitIds'] = sorted(unit['unitId'] for unit in build_plan(request)['plan']['units'])
        baseline = build_plan(request)['plan']['proposedProject']
        self.assertEqual(baseline['schemaVersion'], '1.4')
        damaged = copy.deepcopy(baseline)
        port = next(port for node in damaged['nodes'] if node['kind'] != 'switch'
                    for port in node['ports'] if port['ipv4'] is not None)
        original_ip = port['ipv4']
        port['ipv4'] = '192.168.10.255/24'
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory))
            original_path = store.path('old')
            original_bytes = (json.dumps(damaged, ensure_ascii=False, indent=2) + '\n').encode()
            original_path.write_bytes(original_bytes)
            with self.assertRaisesRegex(ProjectValidationError, 'network or broadcast'):
                store.read('old')
            port['ipv4'] = original_ip  # explicit correction in a separate copy
            store.save('corrected', damaged)
            reopened = store.read('corrected')['project']
            self.assertEqual(reopened['schemaVersion'], '1.4')
            self.assertEqual(reopened['importEvidence'], baseline['importEvidence'])
            self.assertEqual(original_path.read_bytes(), original_bytes)


if __name__ == '__main__':
    unittest.main()
