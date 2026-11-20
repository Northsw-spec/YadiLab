"""4C3: source backed, explicit VLAN imports."""
import copy
import unittest

from network_core.import_plan import build_plan, internal_id
from network_core.import_verification import verify_sources, evidence_status
from network_core.model import ProjectValidationError, validate_project
from network_core.storage import ProjectStore
from pathlib import Path
import tempfile
from test_import_ports import port_request


def vlan_request(mode='access', value='10'):
    raw = f'Device,Label,Kind,Port,PortName,Enabled,Mode,VLAN\nSW-01,Core,switch,Gi1_0_1,Uplink,true,{mode},"{value}"\n'.encode()
    req = port_request(raw)
    port = req['mappingViews'][1]
    port['columns']['port.vlanMode'] = ['G']
    field = 'port.accessVlan' if mode == 'access' else 'port.allowedVlans'
    port['columns'][field] = ['H']
    for view in req['mappingViews']:
        view['expectedHeaders'] += ['Mode', 'VLAN']
    req['transformations'] = [{'viewId': 'view-2', 'targetField': field,
                               'operation': 'parse_vlan_integer' if mode == 'access' else 'split_vlan_integer_list',
                               'delimiter': None if mode == 'access' else ','}]
    return req


class VlanImportTests(unittest.TestCase):
    def selected(self, req):
        discovery = build_plan(req)['plan']
        req['selectedUnitIds'] = sorted(unit['unitId'] for unit in discovery['units'])
        return build_plan(req)['plan']

    def test_negative_syntax_and_absent_transformation(self):
        for value in ('0', '4095', '010', '10 ', ' 10'):
            with self.subTest(value=value):
                plan = build_plan(vlan_request(value=value))['plan']
                self.assertEqual(next(u for u in plan['units'] if u['kind'] == 'port')['status'], 'BLOCKED')
        req = vlan_request()
        req['transformations'] = []
        self.assertEqual(next(u for u in build_plan(req)['plan']['units'] if u['kind'] == 'port')['status'], 'BLOCKED')
        for value in ('10, 20', '10,20,', '010,20', '10,,20', '10,10', '4095'):
            with self.subTest(value=value):
                plan = build_plan(vlan_request('trunk', value))['plan']
                self.assertEqual(next(u for u in plan['units'] if u['kind'] == 'port')['status'], 'BLOCKED')

    def test_invalid_transformations(self):
        for change in ({'operation': 'parse_int'}, {'delimiter': ','}, {'targetField': 'port.name'}):
            req = vlan_request()
            req['transformations'][0].update(change)
            with self.assertRaises(ProjectValidationError):
                build_plan(req)
        req = vlan_request()
        req['transformations'].append(copy.deepcopy(req['transformations'][0]))
        with self.assertRaises(ProjectValidationError):
            build_plan(req)

    def test_access_trunk_and_replay(self):
        for mode, value, expected in (
            ('access', '10', {'mode': 'access', 'vlan': 10}),
            ('trunk', '10,20', {'mode': 'trunk', 'allowedVlans': [10, 20]}),
        ):
            with self.subTest(mode=mode):
                req = vlan_request(mode, value)
                plan = self.selected(req)
                self.assertTrue(plan['canApply'])
                project = plan['proposedProject']
                self.assertEqual(project['nodes'][0]['ports'][0],
                                 {'id': 'Gi1_0_1', 'name': 'Uplink', 'enabled': True,
                                  'ipv4': None, 'vlan': expected})
                self.assertEqual(validate_project(project), project)
                self.assertEqual(verify_sources({'project': project, 'sources': req['sources']})['sourceStatus'], 'SOURCE_VERIFIED')
                damaged = copy.deepcopy(project)
                change = next(c for c in damaged['importEvidence']['acceptedChanges'] if c['targetKind'] == 'port')
                change['fieldOrigins']['vlan'] = []
                with self.assertRaises(ProjectValidationError):
                    validate_project(damaged)

    def test_row_decision_conflict_and_combinations(self):
        req = vlan_request()
        req['rowValues'] = [{'viewId':'view-2','row':2,'targetField':'port.accessVlan',
                             'valueType':'integer','value':20}]
        self.assertIn('FIELD_CONFLICT', [d['code'] for d in build_plan(req)['plan']['diagnostics']])
        req['rowValues'][0]['value'] = 10
        self.assertTrue(self.selected(req)['canApply'])
        for bad in (True, 0, 4095, 10.0, '10'):
            with self.subTest(bad=bad):
                req['rowValues'][0]['value'] = bad
                with self.assertRaises(ProjectValidationError):
                    build_plan(req)
        for mutate in ('missing_mode', 'missing_value', 'both', 'unknown_mode', 'host'):
            req = vlan_request()
            port = req['mappingViews'][1]
            if mutate == 'missing_mode':
                port['columns'].pop('port.vlanMode')
            elif mutate == 'missing_value':
                port['columns'].pop('port.accessVlan')
                req['transformations'] = []
            elif mutate == 'both':
                port['constants']['port.allowedVlans'] = {'type':'integer_list','value':[20]}
            elif mutate == 'unknown_mode':
                port['constants']['port.vlanMode'] = {'type':'text','value':'hybrid'}
                port['columns'].pop('port.vlanMode')
            else:
                raw = b'Device,Label,Kind,Port,PortName,Enabled,Mode,VLAN\nSW-01,Core,host,Gi1_0_1,Uplink,true,access,10\n'
                req = vlan_request()
                req['sources'] = [port_request(raw)['sources'][0]]
            with self.subTest(mutate=mutate):
                plan = build_plan(req)['plan']
                self.assertEqual(next(u for u in plan['units'] if u['kind'] == 'port')['status'], 'BLOCKED')

    def test_receipt_storage_and_tampering(self):
        req = vlan_request()
        project = self.selected(req)['proposedProject']
        with tempfile.TemporaryDirectory() as folder:
            store = ProjectStore(Path(folder))
            store.save('vlan', project, None)
            saved = store.read('vlan')['project']
            self.assertEqual(saved['nodes'][0]['ports'][0]['vlan'], {'mode':'access','vlan':10})
            self.assertEqual(verify_sources({'project':saved,'sources':req['sources']})['replayStatus'], 'MATCH')
            edited = copy.deepcopy(saved)
            edited['nodes'][0]['ports'][0]['vlan']['vlan'] = 20
            self.assertEqual(evidence_status({'project':edited})['baselineStatus'], 'CHANGED_SINCE_IMPORT')
            self.assertEqual(verify_sources({'project':edited,'sources':req['sources']})['replayStatus'], 'MATCH')
            altered_sources = copy.deepcopy(req['sources'])
            altered_sources[0]['contentBase64'] = altered_sources[0]['contentBase64'][:-4] + 'AAAA'
            with self.assertRaises(ProjectValidationError):
                verify_sources({'project':saved,'sources':altered_sources})
        for changed in ('transformation', 'fingerprint', 'value', 'decision'):
            damaged = copy.deepcopy(project)
            evidence = damaged['importEvidence']
            if changed == 'transformation':
                evidence['transformations'][0]['operation'] = 'parse_int'
            elif changed == 'fingerprint':
                evidence['planFingerprint'] = '0' * 64
            elif changed == 'value':
                next(c for c in evidence['acceptedChanges'] if c['targetKind'] == 'port')['fieldValues']['vlan']['vlan'] = 20
            else:
                refs = next(c for c in evidence['acceptedChanges'] if c['targetKind'] == 'port')['fieldOrigins']['vlan']
                next(ref for ref in refs if ref['kind'] == 'user_decision')['decisionId'] = 'd-' + '0' * 32
            with self.subTest(changed=changed):
                with self.assertRaises(ProjectValidationError):
                    validate_project(damaged)

    def test_complementary_views_and_identical_claims(self):
        req = vlan_request()
        duplicate = copy.deepcopy(req['mappingViews'][1])
        duplicate['viewId'] = 'view-3'
        req['mappingViews'].append(duplicate)
        req['transformations'].append({**req['transformations'][0], 'viewId':'view-3'})
        plan = self.selected(req)
        self.assertTrue(plan['canApply'])
        self.assertEqual(len(plan['proposedProject']['nodes'][0]['ports']), 1)
        refs = next(c for c in plan['proposedProject']['importEvidence']['acceptedChanges']
                    if c['targetKind'] == 'port')['fieldOrigins']['vlan']
        self.assertEqual(len([r for r in refs if r['kind'] == 'source_cell']), 4)
        self.assertEqual(verify_sources({'project':plan['proposedProject'],
                                         'sources':req['sources']})['sourceStatus'], 'SOURCE_VERIFIED')
        duplicate['constants']['port.vlanMode'] = {'type':'text','value':'trunk'}
        duplicate['columns'].pop('port.vlanMode')
        plan = build_plan(req)['plan']
        self.assertIn('FIELD_CONFLICT', [d['code'] for d in plan['diagnostics']])

    def test_typed_trunk_row_value_and_absent_vlan(self):
        req = port_request()
        port = req['mappingViews'][1]
        port['constants']['port.vlanMode'] = {'type':'text','value':'trunk'}
        req['rowValues'] = [{'viewId':'view-2','row':2,'targetField':'port.allowedVlans',
                             'valueType':'integer_list','value':[10,20]}]
        plan = self.selected(req)
        self.assertTrue(plan['canApply'])
        self.assertEqual(plan['proposedProject']['nodes'][0]['ports'][0]['vlan'],
                         {'mode':'trunk','allowedVlans':[10,20]})
        self.assertEqual(verify_sources({'project':plan['proposedProject'],
                                         'sources':req['sources']})['replayStatus'], 'MATCH')
        req['rowValues'][0]['value'] = [10,10]
        with self.assertRaises(ProjectValidationError):
            build_plan(req)
        plain = self.selected(port_request())['proposedProject']
        self.assertNotIn('vlan', plain['nodes'][0]['ports'][0])


if __name__ == '__main__':
    unittest.main()
