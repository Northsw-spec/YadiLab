"""Explicit zone claims, node dependencies and historical replay for the first 4C slice."""
import copy
import tempfile
import unittest
from pathlib import Path

from network_core.import_plan import build_plan, internal_id
from network_core.import_verification import verify_sources, evidence_status
from network_core.model import ProjectValidationError, validate_project
from network_core.storage import ProjectStore
from test_import_plan import source, view


def zone_request():
    zone = b'ID,Label\nZ1,North\n'
    node = b'ID,Label,Kind,Zone\nN1,Host,host,Z1\n'
    zone_view = view({'zone.id':['A'], 'zone.label':['B']},
                     headers=('ID','Label'), role='zone_inventory')
    node_view = view({'node.id':['A'], 'node.label':['B'], 'node.kind':['C'], 'node.zoneId':['D']},
                     view_id='view-2', headers=('ID','Label','Kind','Zone'))
    node_view['sourceId'] = 'src-2'
    return {'contractVersion':'1', 'projectName':'Explicit zones',
            'sources':[source(zone,'zones.csv'), source(node,'nodes.csv','src-2')],
            'mappingViews':[zone_view,node_view], 'transformations':[],
            'rowValues':[], 'excludedUses':[], 'selectedUnitIds':[]}


class ZoneImportTests(unittest.TestCase):
    def test_zone_node_dependencies_and_replay(self):
        req = zone_request()
        first = build_plan(req)['plan']
        by_kind = {unit['kind']:unit for unit in first['units']}
        self.assertEqual(set(by_kind), {'zone','node'})
        self.assertEqual(by_kind['zone']['unitId'], internal_id('u-',['zone','Z1']))
        self.assertEqual(by_kind['node']['dependencies'], [by_kind['zone']['unitId']])
        self.assertEqual(first['report']['zones'], 1)
        self.assertFalse(first['canApply'])
        req['selectedUnitIds'] = [by_kind['node']['unitId']]
        incomplete = build_plan(req)['plan']
        self.assertFalse(incomplete['canApply'])
        self.assertIsNone(incomplete['proposedProject'])
        self.assertIn('SELECTED_UNIT_NOT_ACTIONABLE', [d['code'] for d in incomplete['diagnostics']])
        req['selectedUnitIds'] = [by_kind['zone']['unitId']]
        self.assertFalse(build_plan(req)['plan']['canApply'])  # A zone alone is no network project.
        req['selectedUnitIds'] = sorted(unit['unitId'] for unit in by_kind.values())
        plan = build_plan(req)['plan']
        self.assertTrue(plan['canApply'])
        project = plan['proposedProject']
        self.assertEqual(project['zones'], [{'id':'Z1','label':'North'}])
        self.assertEqual(project['nodes'][0]['zoneId'], 'Z1')
        self.assertEqual(project['nodes'][0]['ports'], [])
        self.assertEqual(project['links'], [])
        self.assertEqual(validate_project(project), project)
        self.assertEqual([change['targetKind'] for change in project['importEvidence']['acceptedChanges']],
                         [next(unit['kind'] for unit in first['units'] if unit['unitId']==identifier)
                          for identifier in req['selectedUnitIds']])
        self.assertEqual(verify_sources({'project':project,'sources':req['sources']})['sourceStatus'],
                         'SOURCE_VERIFIED')
        before = copy.deepcopy(project['importEvidence'])
        project['zones'][0]['label'] = 'Edited'
        self.assertEqual(evidence_status({'project':project})['baselineStatus'], 'CHANGED_SINCE_IMPORT')
        self.assertEqual(project['importEvidence'], before)
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory))
            saved = store.save('zones', project, None)
            loaded = store.read('zones')['project']
            self.assertEqual(loaded, project)
            self.assertEqual(loaded['importEvidence'], before)
            self.assertEqual(verify_sources({'project':loaded,'sources':req['sources']})['sourceStatus'],
                             'SOURCE_VERIFIED')
            self.assertEqual(saved['sha256'], store.read('zones')['sha256'])

    def test_missing_invalid_conflicting_zone(self):
        req = zone_request()
        req['mappingViews'] = req['mappingViews'][1:]
        req['mappingViews'][0]['viewId'] = 'view-1'
        plan = build_plan(req)['plan']
        self.assertEqual(plan['units'][0]['status'], 'BLOCKED')
        self.assertIn('UNDECLARED_ZONE', [d['code'] for d in plan['diagnostics']])
        req = zone_request()
        req['sources'][0] = source(b'ID,Label\n1,North\n','zones.csv')
        plan = build_plan(req)['plan']
        self.assertTrue(any(d['code']=='NUMERIC_ID_REQUIRES_DECISION' for d in plan['diagnostics']) or
                        any(d['code']=='INVALID_ZONE_ID' for d in plan['diagnostics']))
        req = zone_request()
        req['sources'][0] = source(b'ID,Label\nZ1,North\nZ1,South\n','zones.csv')
        req['mappingViews'][0]['selectedRows'] = [2,3]
        plan = build_plan(req)['plan']
        zone = next(unit for unit in plan['units'] if unit['kind']=='zone')
        self.assertEqual(zone['status'], 'BLOCKED')
        self.assertEqual({ref['row'] for item in zone['diagnostics']
                          for ref in item['sourceRefs']}, {2,3})
        req['selectedUnitIds'] = sorted(unit['unitId'] for unit in plan['units'])
        self.assertFalse(build_plan(req)['plan']['canApply'])
        req = zone_request()
        req['sources'][0] = source(b'ID,Label\nZ1,North\nZ1,North\n','zones.csv')
        req['mappingViews'][0]['selectedRows'] = [2,3]
        plan = build_plan(req)['plan']
        self.assertEqual(len([u for u in plan['units'] if u['kind']=='zone']), 1)
        self.assertEqual(plan['report']['noOp'], 1)

    def test_same_original_row_can_declare_zone_and_node(self):
        req = zone_request()
        req['sources'] = [source(b'Node,Label,Kind,Zone,ZoneLabel\nN1,Host,host,Z1,North\n')]
        req['mappingViews'][0]['sourceId'] = 'src-1'
        req['mappingViews'][0]['columns'] = {'zone.id':['D'],'zone.label':['E']}
        req['mappingViews'][0]['expectedHeaders'] = ['Node','Label','Kind','Zone','ZoneLabel']
        req['mappingViews'][1]['sourceId'] = 'src-1'
        req['mappingViews'][1]['expectedHeaders'] = ['Node','Label','Kind','Zone','ZoneLabel']
        plan = build_plan(req)['plan']
        review = next(item for item in plan['recordReviews'] if item['row']==2)
        self.assertEqual(len(review['viewUses']), 2)
        req['selectedUnitIds'] = sorted(unit['unitId'] for unit in plan['units'])
        project = build_plan(req)['plan']['proposedProject']
        self.assertEqual(len(project['zones']), 1)
        self.assertEqual(len(project['nodes']), 1)
        self.assertEqual(verify_sources({'project':project,'sources':req['sources']})['sourceStatus'],
                         'SOURCE_VERIFIED')
        damaged = copy.deepcopy(project)
        zone_change = next(c for c in damaged['importEvidence']['acceptedChanges'] if c['targetKind']=='zone')
        zone_change['fieldValues']['label'] = 'False history'
        with self.assertRaises(ProjectValidationError):
            validate_project(damaged)
        for field, replacement in (('unitId', 'u-' + '0'*32),
                                   ('changeIds', ['c-' + '0'*32])):
            damaged = copy.deepcopy(project)
            zone_change = next(c for c in damaged['importEvidence']['acceptedChanges']
                               if c['targetKind']=='zone')
            zone_change[field] = replacement
            with self.subTest(field=field), self.assertRaises(ProjectValidationError):
                validate_project(damaged)
        damaged = copy.deepcopy(project)
        zone_change = next(c for c in damaged['importEvidence']['acceptedChanges'] if c['targetKind']=='zone')
        zone_change['fieldOrigins']['id'][0]['address'] = 'A1'
        with self.assertRaises(ProjectValidationError):
            validate_project(damaged)
        damaged = copy.deepcopy(project)
        node_change = next(c for c in damaged['importEvidence']['acceptedChanges'] if c['targetKind']=='node')
        node_change['fieldOrigins']['zoneId'] = []
        with self.assertRaises(ProjectValidationError):
            validate_project(damaged)

    def test_explicit_zone_decision_and_constant_replay(self):
        req = zone_request()
        req['sources'][0] = source(b'ID,Label\n,North\n','zones.csv')
        req['rowValues'] = [{'viewId':'view-1','row':2,'targetField':'zone.id',
                             'valueType':'text','value':'Z1'}]
        req['mappingViews'][0]['constants'] = {'zone.label':{'type':'text','value':'North'}}
        req['mappingViews'][0]['columns'] = {'zone.id':['A']}
        discovery = build_plan(req)['plan']
        req['selectedUnitIds'] = sorted(unit['unitId'] for unit in discovery['units'])
        project = build_plan(req)['plan']['proposedProject']
        self.assertEqual(project['zones'], [{'id':'Z1','label':'North'}])
        zone = next(c for c in project['importEvidence']['acceptedChanges']
                    if c['targetKind']=='zone')
        self.assertEqual(zone['fieldOrigins']['id'][0]['kind'], 'user_decision')
        self.assertEqual(zone['fieldOrigins']['label'][0]['kind'], 'user_constant')
        self.assertEqual(verify_sources({'project':project,'sources':req['sources']})['sourceStatus'],
                         'SOURCE_VERIFIED')


if __name__ == '__main__':
    unittest.main()
