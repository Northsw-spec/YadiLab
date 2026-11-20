"""Explicit source-backed static routes with declared port and IPv4 dependencies."""
import copy
import tempfile
import unittest
from pathlib import Path

from network_core.import_plan import build_plan, internal_id
from network_core.import_verification import verify_sources, evidence_status
from network_core.model import ProjectValidationError, validate_project
from network_core.routing import ConnectedRoutingTable
from network_core.storage import ProjectStore
from test_import_plan import source, view


HEADERS = ('Node','Label','Kind','Port','PortName','Enabled','IPv4',
           'Route','Destination','NextHop','OutPort')


def route_request(destination='192.168.20.0/24', hop='10.0.0.2', out='eth0', kind='router', enabled='true'):
    raw = (','.join(HEADERS) + '\n' +
           f'R1,Router,{kind},eth0,Ethernet 0,{enabled},10.0.0.1/30,route1,{destination},{hop},{out}\n').encode()
    mappings = [
        view({'node.id':['A'],'node.label':['B'],'node.kind':['C']}, headers=HEADERS),
        view({'port.nodeId':['A'],'port.id':['D'],'port.name':['E'],'port.enabled':['F']},
             view_id='view-2', headers=HEADERS, role='interface_inventory'),
        view({'ip.nodeId':['A'],'ip.portId':['D'],'ip.ipv4':['G']},
             view_id='view-3', headers=HEADERS, role='ip_plan'),
        view({'route.nodeId':['A'],'route.id':['H'],'route.destination':['I'],
              'route.nextHop':['J'],'route.outPort':['K']},
             view_id='view-4', headers=HEADERS, role='static_route_register'),
    ]
    return {'contractVersion':'1','projectName':'Routes','sources':[source(raw)],
            'mappingViews':mappings,'transformations':[], 'rowValues':[],
            'excludedUses':[], 'selectedUnitIds':[]}


def all_selected(req):
    discovery = build_plan(req)['plan']
    req['selectedUnitIds'] = sorted(unit['unitId'] for unit in discovery['units'])
    return build_plan(req)['plan']


class StaticRouteImportTests(unittest.TestCase):
    def test_valid_route_and_dependency(self):
        req = route_request()
        plan = all_selected(req)
        self.assertTrue(plan['canApply'])
        units = {unit['kind']:unit for unit in plan['units']}
        self.assertEqual(units['staticRoute']['targetKey'], '["R1","route1"]')
        self.assertEqual(units['staticRoute']['unitId'],
                         internal_id('u-', ['staticRoute','["R1","route1"]']))
        self.assertEqual(units['staticRoute']['dependencies'], sorted(
            [units['node']['unitId'],units['port']['unitId'],units['ipBinding']['unitId']]))
        project = plan['proposedProject']
        self.assertEqual(project['nodes'][0]['staticRoutes'],
                         [{'id':'route1','destination':'192.168.20.0/24',
                           'nextHop':'10.0.0.2','outPort':'eth0'}])
        self.assertEqual(project['nodes'][0]['ports'][0]['ipv4'], '10.0.0.1/30')
        self.assertEqual(project['links'], [])
        selected = ConnectedRoutingTable(project, 'R1').lookup('192.168.20.10')['selectedRoute']
        self.assertEqual((selected['routeId'], selected['nextHop'], selected['outInterface']),
                         ('route1','10.0.0.2',{'node':'R1','port':'eth0'}))
        self.assertEqual(verify_sources({'project':project,'sources':req['sources']})['replayStatus'], 'MATCH')

    def test_invalid_route_facts_fail_closed(self):
        for dest, hop, out in (
            ('192.168.20.5/24','10.0.0.2','eth0'), ('192.168.20.0','10.0.0.2','eth0'),
            ('192.168.20.0/33','10.0.0.2','eth0'), ('2001:db8::/64','10.0.0.2','eth0'),
            ('192.168.20.0/24','10.0.0.1','eth0'), ('192.168.20.0/24','10.0.0.5','eth0'),
            ('192.168.20.0/24','224.0.0.1','eth0'), ('192.168.20.0/24','240.0.0.1','eth0'),
            ('192.168.20.0/24','10.0.0.0','eth0'), ('192.168.20.0/24','10.0.0.3','eth0'),
            ('192.168.20.0/24','10.0.0.2','eth1'),
        ):
            with self.subTest(dest=dest, hop=hop, out=out):
                plan = build_plan(route_request(dest, hop, out))['plan']
                self.assertNotEqual(next(u for u in plan['units'] if u['kind']=='staticRoute')['status'], 'ACTIONABLE')
        self.assertTrue(all_selected(route_request(kind='firewall'))['canApply'])

    def test_default_route_disabled_port_and_disk_replay(self):
        req = route_request('0.0.0.0/0', enabled='false')
        plan = all_selected(req)
        project = plan['proposedProject']
        self.assertEqual(project['nodes'][0]['staticRoutes'][0],
                         {'id':'route1','destination':'0.0.0.0/0','nextHop':'10.0.0.2','outPort':'eth0'})
        self.assertIs(project['nodes'][0]['ports'][0]['enabled'], False)
        self.assertFalse(any(r['type'] == 'STATIC' for r in ConnectedRoutingTable(project, 'R1').routes()))
        with tempfile.TemporaryDirectory() as folder:
            store = ProjectStore(Path(folder))
            store.save('routes', project, None)
            saved = store.read('routes')['project']
            self.assertEqual(saved['nodes'][0]['staticRoutes'], project['nodes'][0]['staticRoutes'])
            self.assertEqual(verify_sources({'project':saved,'sources':req['sources']})['sourceStatus'],
                             'SOURCE_VERIFIED')
            changed = copy.deepcopy(saved)
            changed['nodes'][0]['staticRoutes'][0]['destination'] = '192.168.30.0/24'
            self.assertEqual(evidence_status({'project':changed})['baselineStatus'], 'CHANGED_SINCE_IMPORT')
            self.assertEqual(verify_sources({'project':changed,'sources':req['sources']})['replayStatus'], 'MATCH')

    def test_missing_dependencies_and_duplicate_facts(self):
        req = route_request()
        units = {u['kind']:u for u in build_plan(req)['plan']['units']}
        req['selectedUnitIds'] = [units['staticRoute']['unitId']]
        self.assertFalse(build_plan(req)['plan']['canApply'])
        req['selectedUnitIds'] = sorted(u['unitId'] for kind,u in units.items() if kind != 'ipBinding')
        self.assertFalse(build_plan(req)['plan']['canApply'])
        req = route_request()
        req['excludedUses'] = [{'viewId':'view-3','row':2,'reason':'IP not approved'}]
        self.assertEqual(next(u for u in build_plan(req)['plan']['units'] if u['kind']=='staticRoute')['status'], 'BLOCKED')
        req = route_request()
        req['mappingViews'][2]['columns'].pop('ip.ipv4')
        self.assertEqual(next(u for u in build_plan(req)['plan']['units'] if u['kind']=='staticRoute')['status'], 'BLOCKED')
        req = route_request(kind='switch')
        self.assertEqual(next(u for u in build_plan(req)['plan']['units'] if u['kind']=='staticRoute')['status'], 'INVALID')

        req = route_request()
        raw = (','.join(HEADERS) + '\n' +
               'R1,Router,router,eth0,Ethernet 0,true,10.0.0.1/30,route1,192.168.20.0/24,10.0.0.2,eth0\n' +
               'R1,Router,router,eth0,Ethernet 0,true,10.0.0.1/30,route2,192.168.20.0/24,10.0.0.2,eth0\n').encode()
        req['sources'] = [source(raw)]
        for mapping in req['mappingViews']:
            mapping['selectedRows'] = [2,3]
        plan = build_plan(req)['plan']
        self.assertEqual([u['status'] for u in plan['units'] if u['kind']=='staticRoute'],
                         ['BLOCKED','BLOCKED'])

    def test_duplicate_claims_conflicts_and_receipt_tampering(self):
        req = route_request()
        duplicate = copy.deepcopy(req['mappingViews'][3])
        duplicate['viewId'] = 'view-5'
        req['mappingViews'].append(duplicate)
        plan = all_selected(req)
        self.assertEqual(len([u for u in plan['units'] if u['kind']=='staticRoute']), 1)
        project = plan['proposedProject']
        change = next(c for c in project['importEvidence']['acceptedChanges'] if c['targetKind']=='staticRoute')
        self.assertEqual(change['fieldValues'], {'nodeId':'R1','id':'route1','destination':'192.168.20.0/24',
                                                 'nextHop':'10.0.0.2','outPort':'eth0'})
        self.assertEqual(len(change['fieldOrigins']['nextHop']), 2)
        self.assertEqual(change['changeIds'], [internal_id('c-', [change['unitId'],'create','__object__'])])
        for field in ('targetKey','unitId','changeIds','fieldValues','fieldOrigins'):
            damaged = copy.deepcopy(project)
            route_change = next(c for c in damaged['importEvidence']['acceptedChanges'] if c['targetKind']=='staticRoute')
            if field == 'targetKey': route_change[field] = '["R1", "route1"]'
            elif field == 'unitId': route_change[field] = 'u-' + '0'*32
            elif field == 'changeIds': route_change[field] = ['c-' + '0'*32]
            elif field == 'fieldValues': route_change[field]['nextHop'] = '10.0.0.1'
            else: route_change[field]['nextHop'] = []
            with self.subTest(field=field), self.assertRaises(ProjectValidationError):
                validate_project(damaged)

    def test_complementary_views_and_two_distinct_routes(self):
        req = route_request()
        route_view = req['mappingViews'][3]
        route_view['columns'].pop('route.outPort')
        complement = copy.deepcopy(route_view)
        complement['viewId'] = 'view-5'
        complement['columns'] = {'route.nodeId':['A'], 'route.id':['H'], 'route.outPort':['K']}
        req['mappingViews'].append(complement)
        plan = all_selected(req)
        self.assertTrue(plan['canApply'])
        self.assertEqual(plan['proposedProject']['nodes'][0]['staticRoutes'][0]['outPort'], 'eth0')

        req = route_request()
        raw = (','.join(HEADERS) + '\n' +
               'R1,Router,router,eth0,Ethernet 0,true,10.0.0.1/30,route1,192.168.20.0/24,10.0.0.2,eth0\n' +
               'R1,Router,router,eth0,Ethernet 0,true,10.0.0.1/30,default,0.0.0.0/0,10.0.0.2,eth0\n').encode()
        req['sources'] = [source(raw)]
        for mapping in req['mappingViews']:
            mapping['selectedRows'] = [2,3]
        plan = all_selected(req)
        self.assertTrue(plan['canApply'])
        self.assertEqual(plan['proposedProject']['nodes'][0]['staticRoutes'], [
            {'id':'default','destination':'0.0.0.0/0','nextHop':'10.0.0.2','outPort':'eth0'},
            {'id':'route1','destination':'192.168.20.0/24','nextHop':'10.0.0.2','outPort':'eth0'}])

    def test_conflicting_route_cells_are_reported(self):
        req = route_request()
        raw = (','.join(HEADERS) + '\n' +
               'R1,Router,router,eth0,Ethernet 0,true,10.0.0.1/30,route1,192.168.20.0/24,10.0.0.2,eth0\n' +
               'R1,Router,router,eth0,Ethernet 0,true,10.0.0.1/30,route1,192.168.20.0/24,10.0.0.3,eth0\n').encode()
        req['sources'] = [source(raw)]
        for mapping in req['mappingViews']:
            mapping['selectedRows'] = [2,3]
        plan = build_plan(req)['plan']
        unit = next(u for u in plan['units'] if u['kind']=='staticRoute')
        self.assertEqual(unit['status'], 'BLOCKED')
        conflict = next(d for d in unit['diagnostics'] if d['code']=='FIELD_CONFLICT')
        self.assertEqual({ref['address'] for ref in conflict['sourceRefs']}, {'J2','J3'})

    def test_route_from_second_document(self):
        req = route_request()
        req['sources'].append(source(
            b'Node,Route,Destination,NextHop,OutPort\n'
            b'R1,route1,192.168.20.0/24,10.0.0.2,eth0\n',
            'routes.csv', 'src-2'))
        route_view = req['mappingViews'][3]
        route_view['sourceId'] = 'src-2'
        route_view['expectedHeaders'] = ['Node','Route','Destination','NextHop','OutPort']
        route_view['columns'] = {'route.nodeId':['A'],'route.id':['B'],
                                 'route.destination':['C'],'route.nextHop':['D'],
                                 'route.outPort':['E']}
        plan = all_selected(req)
        self.assertTrue(plan['canApply'])
        change = next(c for c in plan['proposedProject']['importEvidence']['acceptedChanges']
                      if c['targetKind']=='staticRoute')
        self.assertEqual((change['fieldOrigins']['nextHop'][0]['sourceId'],
                          change['fieldOrigins']['nextHop'][0]['address']), ('src-2','D2'))
        self.assertEqual(verify_sources({'project':plan['proposedProject'],
                                         'sources':req['sources']})['sourceStatus'], 'SOURCE_VERIFIED')


if __name__ == '__main__':
    unittest.main()
