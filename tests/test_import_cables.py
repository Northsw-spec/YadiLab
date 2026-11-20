"""Explicit cable claims and endpoint dependencies in source-backed imports."""
import copy
import tempfile
import unittest
from pathlib import Path

from network_core.import_plan import build_plan, internal_id
from network_core.import_verification import verify_sources, evidence_status
from network_core.model import ProjectValidationError, validate_project, topology_trace
from network_core.storage import ProjectStore
from test_import_plan import source, view
from xlsx_fixture import make_workbook, workbook_parts, zip_parts
from ods_fixture import ods_parts, zip_parts as ods_zip


HEADERS = ('Node','Label','Kind','Port','PortName','PortEnabled',
           'Link','ANode','APort','BNode','BPort','LinkEnabled')


def cable_request(enabled='true'):
    raw = (','.join(HEADERS) + '\n' +
           f'SW1,Switch,switch,p1,Port 1,true,CABLE-001,SW1,p1,H1,eth0,{enabled}\n' +
           'H1,Host,host,eth0,Ethernet 0,true,,,,,,\n').encode()
    node = view({'node.id':['A'],'node.label':['B'],'node.kind':['C']},
                rows=(2,3), headers=HEADERS)
    port = view({'port.nodeId':['A'],'port.id':['D'],'port.name':['E'],'port.enabled':['F']},
                rows=(2,3), view_id='view-2', headers=HEADERS, role='interface_inventory')
    link = view({'link.id':['G'],'link.aNode':['H'],'link.aPort':['I'],
                 'link.bNode':['J'],'link.bPort':['K'],'link.enabled':['L']},
                view_id='view-3', headers=HEADERS, role='cable_register')
    return {'contractVersion':'1','projectName':'Cables','sources':[source(raw)],
            'mappingViews':[node,port,link], 'transformations':[], 'rowValues':[],
            'excludedUses':[], 'selectedUnitIds':[]}


def select_all(req):
    discovery = build_plan(req)['plan']
    req['selectedUnitIds'] = sorted(u['unitId'] for u in discovery['units'])
    return build_plan(req)['plan']


class CableImportTests(unittest.TestCase):
    def test_native_spreadsheet_booleans_and_numeric_rejection(self):
        headers = HEADERS[:-1] + ('enabled',)
        csv = (','.join(headers) + '\n' +
               'SW1,Switch,switch,p1,Port 1,true,CABLE-001,SW1,p1,H1,eth0,false\n' +
               'H1,Host,host,eth0,Ethernet 0,true,,,,,,\n')
        ods = ods_parts({'Cables':csv})
        ods['content.xml'] = ods['content.xml'].replace(b'1024', b'12')
        for filename, raw in (('cables.xlsx', make_workbook({'Cables':csv})),
                              ('cables.ods', ods_zip(ods))):
            with self.subTest(filename=filename):
                req = cable_request()
                req['sources'] = [source(raw, filename)]
                for mapping in req['mappingViews']:
                    mapping['expectedHeaders'] = list(headers)
                plan = select_all(req)
                self.assertTrue(plan['canApply'])
                self.assertIs(plan['proposedProject']['links'][0]['enabled'], False)
                self.assertEqual(verify_sources({'project':plan['proposedProject'],
                                                 'sources':req['sources']})['sourceStatus'],
                                 'SOURCE_VERIFIED')
        parts = workbook_parts({'Cables':csv})
        path = 'xl/worksheets/sheet1.xml'
        parts[path] = parts[path].replace(b'<c r="L2" t="b"><v>0</v></c>',
                                           b'<c r="L2" t="n"><v>1</v></c>')
        req = cable_request()
        req['sources'] = [source(zip_parts(parts), 'cables.xlsx')]
        for mapping in req['mappingViews']:
            mapping['expectedHeaders'] = list(headers)
        link = next(u for u in build_plan(req)['plan']['units'] if u['kind']=='link')
        self.assertEqual(link['status'], 'BLOCKED')

    def test_explicit_link_and_dependencies(self):
        req = cable_request()
        plan = select_all(req)
        self.assertTrue(plan['canApply'])
        link = next(u for u in plan['units'] if u['kind']=='link')
        self.assertEqual(link['unitId'], internal_id('u-', ['link','CABLE-001']))
        self.assertEqual(link['dependencies'], sorted(
            internal_id('u-', ['port', key]) for key in ('["SW1","p1"]','["H1","eth0"]')))
        self.assertEqual(plan['proposedProject']['links'], [{
            'id':'CABLE-001','a':{'node':'SW1','port':'p1'},
            'b':{'node':'H1','port':'eth0'},'enabled':True}])

    def test_invalid_boolean_and_unknown_endpoint(self):
        for text in ('yes','TRUE','1',' true'):
            with self.subTest(text=text):
                plan = build_plan(cable_request(text))['plan']
                self.assertEqual(next(u for u in plan['units'] if u['kind']=='link')['status'], 'BLOCKED')
        for field, column in (('link.aNode','G'), ('link.bNode','G'),
                              ('link.aPort','G'), ('link.bPort','D')):
            req = cable_request()
            req['mappingViews'][2]['columns'][field] = [column]
            plan = build_plan(req)['plan']
            with self.subTest(field=field):
                self.assertEqual(next(u for u in plan['units'] if u['kind']=='link')['status'],
                                 'BLOCKED')

    def test_three_cables_and_topology(self):
        rows = [
            'SW1,Switch,switch,p1,Port 1,true,CABLE-001,SW1,p1,R1,eth0,true',
            'SW1,Switch,switch,p2,Port 2,true,CABLE-002,SW1,p2,H1,eth0,true',
            'SW1,Switch,switch,p3,Port 3,true,CABLE-003,SW1,p3,H2,eth0,false',
            'R1,Router,router,eth0,Ethernet 0,true,,,,,,',
            'H1,Host,host,eth0,Ethernet 0,true,,,,,,',
            'H2,Host,host,eth0,Ethernet 0,true,,,,,,',
        ]
        req = cable_request()
        req['sources'] = [source((','.join(HEADERS)+'\n'+'\n'.join(rows)+'\n').encode())]
        for mapping in req['mappingViews'][:2]:
            mapping['selectedRows'] = list(range(2,8))
        req['mappingViews'][2]['selectedRows'] = [2,3,4]
        plan = select_all(req)
        self.assertTrue(plan['canApply'])
        project = plan['proposedProject']
        self.assertEqual(project['links'], [
            {'id':'CABLE-001','a':{'node':'SW1','port':'p1'},'b':{'node':'R1','port':'eth0'},'enabled':True},
            {'id':'CABLE-002','a':{'node':'SW1','port':'p2'},'b':{'node':'H1','port':'eth0'},'enabled':True},
            {'id':'CABLE-003','a':{'node':'SW1','port':'p3'},'b':{'node':'H2','port':'eth0'},'enabled':False},
        ])
        self.assertEqual(topology_trace(project,'R1','H1')['status'], 'PATH_PRESENT')
        self.assertEqual(topology_trace(project,'R1','H2')['status'], 'NO_PATH')
        self.assertEqual(verify_sources({'project':project,'sources':req['sources']})['sourceStatus'],
                         'SOURCE_VERIFIED')

    def test_explicit_boolean_map_constant_and_row_value(self):
        req = cable_request('yes')
        mapping = req['mappingViews'][2]
        mapping['valueMaps'] = {'link.enabled': {'yes':'true', 'no':'false'}}
        plan = select_all(req)
        self.assertIs(plan['proposedProject']['links'][0]['enabled'], True)
        origins = next(c for c in plan['proposedProject']['importEvidence']['acceptedChanges']
                       if c['targetKind']=='link')['fieldOrigins']['enabled']
        self.assertEqual({ref['kind'] for ref in origins}, {'source_cell','user_decision'})
        self.assertEqual(verify_sources({'project':plan['proposedProject'],
                                         'sources':req['sources']})['replayStatus'], 'MATCH')
        mapping['valueMaps']['link.enabled']['yes'] = 'on'
        with self.assertRaises(ProjectValidationError):
            build_plan(req)

        req = cable_request('unknown')
        mapping = req['mappingViews'][2]
        mapping['columns'].pop('link.enabled')
        mapping['constants']['link.enabled'] = {'type':'boolean','value':False}
        self.assertIs(select_all(req)['proposedProject']['links'][0]['enabled'], False)
        req = cable_request('unknown')
        mapping = req['mappingViews'][2]
        mapping['columns'].pop('link.enabled')
        req['rowValues'] = [{'viewId':'view-3','row':2,'targetField':'link.enabled',
                             'valueType':'boolean','value':True}]
        self.assertIs(select_all(req)['proposedProject']['links'][0]['enabled'], True)
        req = cable_request('true')
        req['rowValues'] = [{'viewId':'view-3','row':2,'targetField':'link.enabled',
                             'valueType':'boolean','value':False}]
        self.assertIn('FIELD_CONFLICT', [d['code'] for d in build_plan(req)['plan']['diagnostics']])

    def test_missing_fields_occupied_ports_and_conflicts(self):
        for field in ('link.id','link.aNode','link.aPort','link.bNode','link.bPort','link.enabled'):
            req = cable_request()
            req['mappingViews'][2]['columns'].pop(field)
            plan = build_plan(req)['plan']
            self.assertFalse(any(u['kind']=='link' and u['status']=='ACTIONABLE' for u in plan['units']))
        req = cable_request()
        req['mappingViews'][2]['columns']['link.bNode'] = ['H']
        self.assertEqual(next(u for u in build_plan(req)['plan']['units'] if u['kind']=='link')['status'], 'INVALID')

        req = cable_request()
        raw = (','.join(HEADERS)+'\n' +
               'SW1,Switch,switch,p1,Port 1,true,CABLE-001,SW1,p1,H1,eth0,true\n' +
               'H1,Host,host,eth0,Ethernet 0,true,CABLE-002,SW1,p1,H1,eth0,true\n').encode()
        req['sources'] = [source(raw)]
        req['mappingViews'][2]['selectedRows'] = [2,3]
        discovery = build_plan(req)['plan']
        self.assertEqual(len([u for u in discovery['units'] if u['kind']=='link']), 2)
        req['selectedUnitIds'] = sorted(u['unitId'] for u in discovery['units'])
        plan = build_plan(req)['plan']
        self.assertFalse(plan['canApply'])
        self.assertIn('PORT_OCCUPIED', [d['code'] for d in plan['diagnostics']])
        req['selectedUnitIds'] = sorted(u['unitId'] for u in discovery['units']
                                        if u['kind'] != 'link' or u['targetKey'] == 'CABLE-001')
        self.assertTrue(build_plan(req)['plan']['canApply'])

        req = cable_request()
        raw = (','.join(HEADERS)+'\n' +
               'SW1,Switch,switch,p1,Port 1,true,CABLE-001,SW1,p1,H1,eth0,true\n' +
               'H1,Host,host,eth0,Ethernet 0,true,CABLE-001,SW1,p1,H1,p1,true\n').encode()
        req['sources'] = [source(raw)]
        req['mappingViews'][2]['selectedRows'] = [2,3]
        plan = build_plan(req)['plan']
        link = next(u for u in plan['units'] if u['kind']=='link')
        self.assertEqual(link['status'], 'BLOCKED')
        conflict = next(d for d in link['diagnostics'] if d['code']=='FIELD_CONFLICT')
        self.assertEqual({r['address'] for r in conflict['sourceRefs']}, {'K2','K3'})

    def test_duplicate_claims_and_missing_selection(self):
        req = cable_request()
        req['sources'] = [source((','.join(HEADERS)+'\n' +
            'SW1,Switch,switch,p1,Port 1,true,CABLE-001,SW1,p1,H1,eth0,true\n' +
            'H1,Host,host,eth0,Ethernet 0,true,CABLE-001,SW1,p1,H1,eth0,true\n').encode())]
        req['mappingViews'][2]['selectedRows'] = [2,3]
        discovery = build_plan(req)['plan']
        links = [u for u in discovery['units'] if u['kind']=='link']
        self.assertEqual(len(links), 1)
        self.assertEqual(len(links[0]['sourceUses']), 2)
        self.assertEqual(len(discovery['recordReviews']), 3)
        req['selectedUnitIds'] = sorted(u['unitId'] for u in discovery['units'])
        selected = build_plan(req)['plan']
        self.assertTrue(selected['canApply'])
        change = next(c for c in selected['proposedProject']['importEvidence']['acceptedChanges']
                      if c['targetKind']=='link')
        self.assertEqual(len(change['fieldOrigins']['a']), 4)
        self.assertEqual(len(selected['proposedProject']['links']), 1)
        self.assertEqual(verify_sources({'project':selected['proposedProject'],
                                         'sources':req['sources']})['sourceStatus'], 'SOURCE_VERIFIED')
        for omitted in links[0]['dependencies']:
            req['selectedUnitIds'] = [u for u in discovery['units'] if u['unitId'] != omitted]
            req['selectedUnitIds'] = sorted(u['unitId'] for u in req['selectedUnitIds'])
            plan = build_plan(req)['plan']
            self.assertFalse(plan['canApply'])
            self.assertIsNone(plan['proposedProject'])

    def test_complementary_rows_and_blocked_port(self):
        req = cable_request()
        req['sources'] = [source((','.join(HEADERS)+'\n' +
            'SW1,Switch,switch,p1,Port 1,true,CABLE-001,SW1,p1,,,\n' +
            'H1,Host,host,eth0,Ethernet 0,true,CABLE-001,,,H1,eth0,true\n').encode())]
        req['mappingViews'][2]['selectedRows'] = [2,3]
        plan = select_all(req)
        self.assertTrue(plan['canApply'])
        self.assertEqual(plan['proposedProject']['links'], [{
            'id':'CABLE-001','a':{'node':'SW1','port':'p1'},
            'b':{'node':'H1','port':'eth0'},'enabled':True}])
        link = next(u for u in plan['units'] if u['kind']=='link')
        self.assertEqual(len(link['sourceUses']), 2)
        self.assertEqual(verify_sources({'project':plan['proposedProject'],
                                         'sources':req['sources']})['replayStatus'], 'MATCH')
        req['mappingViews'][1]['columns'].pop('port.name')
        blocked = build_plan(req)['plan']
        self.assertFalse(blocked['canApply'])
        self.assertEqual(next(u for u in blocked['units'] if u['kind']=='link')['status'], 'BLOCKED')
        self.assertIn('UNAVAILABLE_LINK_ENDPOINT', [d['code'] for d in blocked['diagnostics']])

    def test_inactive_endpoint_and_source_bytes(self):
        req = cable_request('true')
        req['sources'] = [source((','.join(HEADERS)+'\n' +
            'SW1,Switch,switch,p1,Port 1,false,CABLE-001,SW1,p1,H1,eth0,true\n' +
            'H1,Host,host,eth0,Ethernet 0,true,,,,,,\n').encode())]
        project = select_all(req)['proposedProject']
        self.assertEqual(topology_trace(project,'SW1','H1')['status'], 'NO_PATH')
        changed = copy.deepcopy(req['sources'])
        changed[0] = source((','.join(HEADERS)+'\n' +
            'SW1,Switch,switch,p1,Port 1,false,CABLE-001,SW1,p1,H1,eth0,false\n' +
            'H1,Host,host,eth0,Ethernet 0,true,,,,,,\n').encode())
        with self.assertRaises(ProjectValidationError):
            verify_sources({'project':project,'sources':changed})

    def test_disk_history_and_tamper(self):
        req = cable_request('false')
        project = select_all(req)['proposedProject']
        self.assertIs(project['links'][0]['enabled'], False)
        with tempfile.TemporaryDirectory() as folder:
            store = ProjectStore(Path(folder))
            store.save('cables', project, None)
            saved = store.read('cables')['project']
            self.assertEqual(saved['links'], [{
                'id':'CABLE-001','a':{'node':'SW1','port':'p1'},
                'b':{'node':'H1','port':'eth0'},'enabled':False}])
            self.assertEqual(verify_sources({'project':saved,'sources':req['sources']})['sourceStatus'],
                             'SOURCE_VERIFIED')
            edited = copy.deepcopy(saved)
            edited['links'][0]['enabled'] = True
            self.assertEqual(evidence_status({'project':edited})['baselineStatus'], 'CHANGED_SINCE_IMPORT')
            self.assertEqual(verify_sources({'project':edited,'sources':req['sources']})['replayStatus'], 'MATCH')
        for field in ('targetKey','unitId','changeIds','fieldValues','fieldOrigins'):
            damaged = copy.deepcopy(project)
            change = next(c for c in damaged['importEvidence']['acceptedChanges'] if c['targetKind']=='link')
            if field == 'targetKey': change[field] = 'CABLE-002'
            elif field == 'unitId': change[field] = 'u-'+'0'*32
            elif field == 'changeIds': change[field] = ['c-'+'0'*32]
            elif field == 'fieldValues': change[field]['enabled'] = True
            else: change[field]['a'] = []
            with self.subTest(field=field), self.assertRaises(ProjectValidationError):
                validate_project(damaged)


if __name__ == '__main__':
    unittest.main()
