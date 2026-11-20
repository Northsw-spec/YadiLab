"""4C2: explicit source-backed port claims, dependencies and historical replay."""
import copy
import tempfile
import unittest
from pathlib import Path

from network_core.import_plan import build_plan, internal_id
from network_core.import_verification import verify_sources
from network_core.model import ProjectValidationError, validate_project
from network_core.storage import ProjectStore
from test_import_plan import source, view


def port_request(raw=b'Device,Label,Kind,Port,PortName,Enabled\nSW-01,Core,switch,Gi1_0_1,Uplink,true\n'):
    headers = ('Device', 'Label', 'Kind', 'Port', 'PortName', 'Enabled')
    node = view({'node.id': ['A'], 'node.label': ['B'], 'node.kind': ['C']},
                headers=headers)
    port = view({'port.nodeId': ['A'], 'port.id': ['D'], 'port.name': ['E'],
                 'port.enabled': ['F']}, view_id='view-2',
                headers=headers, role='interface_inventory')
    return {'contractVersion': '1', 'projectName': 'Ports from source',
            'sources': [source(raw)], 'mappingViews': [node, port],
            'transformations': [], 'rowValues': [], 'excludedUses': [],
            'selectedUnitIds': []}


class PortImportTests(unittest.TestCase):
    def test_one_row_two_roles_dependency_candidate_and_replay(self):
        req = port_request()
        discovery = build_plan(req)['plan']
        units = {unit['kind']: unit for unit in discovery['units']}
        self.assertEqual(set(units), {'node', 'port'})
        self.assertEqual(units['port']['targetKey'], '["SW-01","Gi1_0_1"]')
        self.assertEqual(units['port']['unitId'],
                         internal_id('u-', ['port', '["SW-01","Gi1_0_1"]']))
        self.assertEqual(units['port']['dependencies'], [units['node']['unitId']])
        self.assertEqual(len(discovery['recordReviews'][1]['viewUses']), 2)
        self.assertEqual(discovery['report']['ports'], 1)
        self.assertEqual(discovery['report']['links'], 0)
        self.assertFalse(discovery['canApply'])

        req['selectedUnitIds'] = [units['port']['unitId']]
        invalid_selection = build_plan(req)['plan']
        self.assertFalse(invalid_selection['canApply'])
        self.assertIsNone(invalid_selection['proposedProject'])
        self.assertIn('SELECTED_UNIT_NOT_ACTIONABLE',
                      [d['code'] for d in invalid_selection['diagnostics']])

        req['selectedUnitIds'] = sorted(unit['unitId'] for unit in units.values())
        plan = build_plan(req)['plan']
        self.assertTrue(plan['canApply'])
        project = plan['proposedProject']
        self.assertEqual(project['nodes'][0]['ports'],
                         [{'id': 'Gi1_0_1', 'name': 'Uplink',
                           'enabled': True, 'ipv4': None}])
        self.assertEqual(project['links'], [])
        self.assertEqual(validate_project(project), project)
        changes = {item['targetKind']: item for item in project['importEvidence']['acceptedChanges']}
        self.assertEqual(changes['node']['fieldValues']['ports'], [])
        self.assertEqual(changes['port']['fieldValues'],
                         {'nodeId': 'SW-01', 'id': 'Gi1_0_1', 'name': 'Uplink',
                          'enabled': True, 'ipv4': None})
        self.assertEqual(changes['port']['fieldOrigins']['ipv4'], [])
        self.assertEqual(changes['port']['fieldOrigins']['enabled'][0]['kind'], 'source_cell')
        self.assertEqual(verify_sources({'project': project,
                                         'sources': req['sources']})['sourceStatus'],
                         'SOURCE_VERIFIED')
        with tempfile.TemporaryDirectory() as tmp:
            store = ProjectStore(Path(tmp))
            store.save('ports', project, None)
            saved = store.read('ports')['project']
            self.assertEqual(saved, project)
            self.assertEqual(verify_sources({'project': saved,
                                             'sources': req['sources']})['sourceStatus'],
                             'SOURCE_VERIFIED')

        damaged = copy.deepcopy(project)
        port_change = next(c for c in damaged['importEvidence']['acceptedChanges']
                           if c['targetKind'] == 'port')
        port_change['fieldOrigins']['enabled'] = []
        with self.assertRaises(ProjectValidationError):
            validate_project(damaged)

    def test_missing_and_conflicting_port_facts(self):
        req = port_request()
        req['mappingViews'] = [req['mappingViews'][1]]
        req['mappingViews'][0]['viewId'] = 'view-1'
        plan = build_plan(req)['plan']
        self.assertEqual(plan['units'][0]['kind'], 'port')
        self.assertEqual(plan['units'][0]['status'], 'BLOCKED')
        self.assertIn('UNDECLARED_NODE', [d['code'] for d in plan['diagnostics']])

        req = port_request()
        req['mappingViews'][1]['columns'].pop('port.name')
        plan = build_plan(req)['plan']
        port = next(u for u in plan['units'] if u['kind'] == 'port')
        self.assertEqual(port['status'], 'BLOCKED')
        self.assertIn('MISSING_REQUIRED_FIELD', [d['code'] for d in plan['diagnostics']])

        raw = (b'Device,Label,Kind,Port,PortName,Enabled\n'
               b'SW-01,Core,switch,Gi1_0_1,Uplink,true\n'
               b'SW-01,Core,switch,Gi1_0_1,Uplink,false\n')
        req = port_request(raw)
        for v in req['mappingViews']:
            v['selectedRows'] = [2, 3]
        plan = build_plan(req)['plan']
        port = next(u for u in plan['units'] if u['kind'] == 'port')
        self.assertEqual(port['status'], 'BLOCKED')
        self.assertIn('FIELD_CONFLICT', [d['code'] for d in plan['diagnostics']])

    def test_port_id_must_obey_canonical_model(self):
        req = port_request(b'Device,Label,Kind,Port,PortName,Enabled\n'
                           b'SW-01,Core,switch,Gi1/0/1,Uplink,true\n')
        plan = build_plan(req)['plan']
        port = next(unit for unit in plan['units'] if unit['kind'] == 'port')
        self.assertEqual(port['status'], 'INVALID')
        self.assertIn('INVALID_PORT_ID', [d['code'] for d in plan['diagnostics']])

    def test_explicit_boolean_and_origin(self):
        req = port_request(b'Device,Label,Kind,Port,PortName,Enabled\n'
                           b'SW-01,Core,switch,Gi1_0_1,Uplink,yes\n')
        discovery = build_plan(req)['plan']
        self.assertIn('UNMAPPED_BOOLEAN', [d['code'] for d in discovery['diagnostics']])
        req['mappingViews'][1]['valueMaps'] = {'port.enabled': {'yes': 'true', 'no': 'false'}}
        discovery = build_plan(req)['plan']
        self.assertTrue(all(u['status'] == 'ACTIONABLE' for u in discovery['units']))
        req['selectedUnitIds'] = sorted(unit['unitId'] for unit in discovery['units'])
        project = build_plan(req)['plan']['proposedProject']
        self.assertIs(type(project['nodes'][0]['ports'][0]['enabled']), bool)
        origin = next(c for c in project['importEvidence']['acceptedChanges']
                      if c['targetKind'] == 'port')['fieldOrigins']['enabled']
        self.assertEqual({ref['kind'] for ref in origin}, {'source_cell', 'user_decision'})
        self.assertEqual(verify_sources({'project': project,
                                         'sources': req['sources']})['sourceStatus'],
                         'SOURCE_VERIFIED')
        req['mappingViews'][1]['valueMaps'] = {'port.enabled': {'yes': 'on'}}
        with self.assertRaises(ProjectValidationError):
            build_plan(req)


if __name__ == '__main__':
    unittest.main()
