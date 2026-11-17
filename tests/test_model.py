import copy
import unittest

from network_core.model import (
    ProjectValidationError, blank_project, topology_trace, validate_project,
)


def example():
    p = blank_project('Test')
    p['zones'] = [{'id': 'zone-1', 'label': 'Rack A'}]
    p['nodes'] = [
        {'id': 'pc-a', 'label': 'PC A', 'kind': 'host', 'x': 30, 'y': 25, 'zoneId': 'zone-1',
         'ports': [{'id': 'eth0', 'name': 'Ethernet', 'enabled': True, 'ipv4': '192.0.2.1/24'}]},
        {'id': 'sw-a', 'label': 'Switch', 'kind': 'switch', 'x': 310, 'y': 25, 'zoneId': 'zone-1',
         'ports': [{'id': 'gi1', 'name': 'Gi1', 'enabled': True, 'ipv4': None},
                   {'id': 'gi2', 'name': 'Gi2', 'enabled': True, 'ipv4': None}]},
        {'id': 'pc-b', 'label': 'PC B', 'kind': 'host', 'x': 620, 'y': 25, 'zoneId': None,
         'ports': [{'id': 'eth0', 'name': 'Ethernet', 'enabled': True, 'ipv4': '192.0.2.2/24'}]},
    ]
    p['links'] = [
        {'id': 'cable-1', 'a': {'node': 'pc-a', 'port': 'eth0'}, 'b': {'node': 'sw-a', 'port': 'gi1'}, 'enabled': True},
        {'id': 'cable-2', 'a': {'node': 'sw-a', 'port': 'gi2'}, 'b': {'node': 'pc-b', 'port': 'eth0'}, 'enabled': True},
    ]
    return p


class CanonicalModelTests(unittest.TestCase):
    def test_empty_document(self):
        self.assertEqual(validate_project(blank_project()), blank_project())

    def test_canonical_identity_and_explicit_links_preserved(self):
        p = example()
        self.assertEqual(validate_project(p), p)
        self.assertEqual([(l['id'], l['a'], l['b']) for l in validate_project(p)['links']],
                         [(l['id'], l['a'], l['b']) for l in p['links']])

    def test_path_reports_document_graph_not_ping(self):
        r = topology_trace(example(), 'pc-a', 'pc-b')
        self.assertEqual(r['status'], 'PATH_PRESENT')
        self.assertEqual([h['linkId'] for h in r['hops']], ['cable-1', 'cable-2'])
        self.assertIn('NOT simulated', r['meaning'])

    def test_disabled_link_prevents_graph_path(self):
        p = example(); p['links'][1]['enabled'] = False
        self.assertEqual(topology_trace(p, 'pc-a', 'pc-b')['status'], 'NO_PATH')

    def test_disabled_port_prevents_graph_path(self):
        p = example(); p['nodes'][1]['ports'][1]['enabled'] = False
        self.assertEqual(topology_trace(p, 'pc-a', 'pc-b')['status'], 'NO_PATH')

    def test_no_inferred_links_from_address_or_positions(self):
        p = example(); p['links'] = []
        self.assertEqual(topology_trace(p, 'pc-a', 'pc-b')['status'], 'NO_PATH')
        self.assertEqual(validate_project(p)['links'], [])

    def test_same_node_is_not_network_connectivity(self):
        result = topology_trace(example(), 'pc-a', 'pc-a')
        self.assertEqual(result['status'], 'SAME_NODE')
        self.assertEqual(result['hops'], [])

    def test_unknown_node_rejected(self):
        with self.assertRaises(ProjectValidationError):
            topology_trace(example(), 'pc-a', 'pretend-node')

    def test_undeclared_endpoint_rejected(self):
        p = example(); p['links'][0]['a']['port'] = 'fake-port'
        with self.assertRaisesRegex(ProjectValidationError, 'undeclared endpoint'):
            validate_project(p)

    def test_occupied_port_rejected_even_on_different_link(self):
        p = example(); p['links'].append({
            'id':'cable-3','a':{'node':'pc-a','port':'eth0'},
            'b':{'node':'pc-b','port':'eth0'},'enabled':True})
        with self.assertRaisesRegex(ProjectValidationError,'already connected'):
            validate_project(p)

    def test_duplicate_node_port_and_link_ids_rejected(self):
        for case in ('node','port','link'):
            with self.subTest(case=case):
                p = example()
                if case == 'node': p['nodes'][1]['id'] = p['nodes'][0]['id']
                if case == 'port': p['nodes'][1]['ports'][1]['id'] = p['nodes'][1]['ports'][0]['id']
                if case == 'link': p['links'][1]['id'] = p['links'][0]['id']
                with self.assertRaises(ProjectValidationError):
                    validate_project(p)

    def test_zone_must_be_declared(self):
        p = example(); p['nodes'][0]['zoneId'] = 'imaginary-zone'
        with self.assertRaisesRegex(ProjectValidationError,'unknown zone'):
            validate_project(p)

    def test_invalid_ip_fails_instead_of_being_silently_removed(self):
        p = example(); p['nodes'][0]['ports'][0]['ipv4'] = '192.0.2.500/24'
        with self.assertRaisesRegex(ProjectValidationError,'invalid IPv4'):
            validate_project(p)

    def test_ipv4_without_explicit_prefix_is_not_guessed(self):
        p = example(); p['nodes'][0]['ports'][0]['ipv4'] = '192.0.2.1'
        with self.assertRaisesRegex(ProjectValidationError, 'explicit IPv4 address/prefix'):
            validate_project(p)

    def test_invalid_types_are_validation_errors_not_server_crashes(self):
        for field, value in [('kind', {}), ('zoneId', [])]:
            with self.subTest(field=field):
                p = example(); p['nodes'][0][field] = value
                with self.assertRaises(ProjectValidationError):
                    validate_project(p)

    def test_47_nodes_46_real_links_15_zones(self):
        p = blank_project('Canonical chain')
        p['zones'] = [{'id':f'zone-{i}', 'label':f'Declared zone {i}'} for i in range(15)]
        for i in range(47):
            ports = []
            if i > 0:
                ports.append({'id':'in','name':'in','enabled':True,'ipv4':None})
            if i < 46:
                ports.append({'id':'out','name':'out','enabled':True,'ipv4':None})
            p['nodes'].append({'id':f'node-{i}', 'label':f'Node {i}', 'kind':'switch',
                               'x':i*17, 'y':i*8,'zoneId':f'zone-{i%15}', 'ports':ports})
            if i:
                p['links'].append({'id':f'cable-{i}',
                                   'a':{'node':f'node-{i-1}','port':'out'},
                                   'b':{'node':f'node-{i}','port':'in'},'enabled':True})
        validated = validate_project(p)
        self.assertEqual(len(validated['nodes']),47)
        self.assertEqual(len(validated['links']),46)
        self.assertEqual(len(validated['zones']),15)
        self.assertEqual([(link['id'],link['a'],link['b']) for link in validated['links']],
                         [(link['id'],link['a'],link['b']) for link in p['links']])
        trace = topology_trace(validated,'node-0','node-46')
        self.assertEqual([hop['linkId'] for hop in trace['hops']],
                         [f'cable-{i}' for i in range(1,47)])

    def test_ipv6_not_supported_yet(self):
        p = example(); p['nodes'][0]['ports'][0]['ipv4'] = '2001:db8::1/64'
        with self.assertRaisesRegex(ProjectValidationError,'IPv6 is not modeled'):
            validate_project(p)

    def test_version_and_unknown_fields_rejected_not_lost(self):
        p = example(); p['magicGeneratedLinks'] = 50
        with self.assertRaisesRegex(ProjectValidationError,'unsupported fields'):
            validate_project(p)
        p = example(); p['schemaVersion'] = '2.0'
        with self.assertRaisesRegex(ProjectValidationError,'only'):
            validate_project(p)

    def test_nested_extra_fields_fail_closed(self):
        for location in ('node','port','link'):
            with self.subTest(location=location):
                p = example()
                item = {'node':p['nodes'][0], 'port':p['nodes'][0]['ports'][0], 'link':p['links'][0]}[location]
                item['fake'] = 'do not drop me'
                with self.assertRaisesRegex(ProjectValidationError,'unsupported fields'):
                    validate_project(p)

    def test_self_link_rejected(self):
        p = example()
        p['links'][1] = {'id':'self', 'a':{'node':'sw-a','port':'gi1'},
                         'b':{'node':'sw-a','port':'gi2'},'enabled':True}
        with self.assertRaises(ProjectValidationError):
            validate_project(p)

    def test_nonfinite_coords_and_invalid_boolean(self):
        for val in [float('nan'), float('inf'), True, 100001]:
            with self.subTest(val=val):
                p = example();p['nodes'][0]['x'] = val
                with self.assertRaises(ProjectValidationError):
                    validate_project(p)
        p = example(); p['links'][0]['enabled'] = 1
        with self.assertRaisesRegex(ProjectValidationError,'true or false'):
            validate_project(p)

    def test_bfs_chooses_actual_connected_hops(self):
        p = example()
        # Without actual new ports, the documented graph must remain unchanged.
        result = topology_trace(p, 'pc-b', 'pc-a')
        self.assertEqual([(h['fromNode'],h['toNode']) for h in result['hops']],
                         [('pc-b','sw-a'),('sw-a','pc-a')])


if __name__ == '__main__':
    unittest.main()
