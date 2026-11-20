"""Synthetic only: combined 4C source, plan, model and provenance acceptance."""
from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from network_core.import_plan import build_plan, internal_id
from network_core.import_verification import evidence_status, verify_sources
from network_core.model import ProjectValidationError, canonical_network_view, topology_trace, validate_project
from network_core.routing import ConnectedRoutingTable
from network_core.storage import ProjectStore
from test_import_plan import source, view
from xlsx_fixture import make_workbook
from ods_fixture import ods_parts, zip_parts as ods_zip


NAME = 'synthetic only 4C integrated'
DEVICES = 'Node,Label,Kind,Zone\nR1,Router 1,router,WAN\nR2,Router 2,router,WAN\nSW1,Switch 1,switch,LAN\nH1,Host 1,host,LAN\nH2,Host 2,host,LAN\n'
ZONES = 'Zone,Label\nLAN,Local LAN\nWAN,Wide area\n'
PORT_ROWS = (
    ('R1','eth0','Ethernet 0','true','','',''),
    ('R1','eth1','Ethernet 1','true','','',''),
    ('R2','eth0','Ethernet 0','true','','',''),
    ('SW1','g1','Gigabit 1','true','access','10',''),
    ('SW1','g2','Gigabit 2','true','access','10',''),
    ('SW1','g3','Gigabit 3','true','trunk','','10,20'),
    ('H1','eth0','Ethernet 0','true','','',''),
    ('H2','eth0','Ethernet 0','false','','',''),
)
IP_ROWS = (('R1','eth0','10.0.0.1/30'),('R1','eth1','192.168.10.1/24'),
           ('R2','eth0','10.0.0.2/30'),('H1','eth0','192.168.10.20/24'),
           ('H2','eth0','192.168.10.21/24'))
LINK_ROWS = (('L1','R1','eth0','R2','eth0','true'),
             ('L2','R1','eth1','SW1','g1','true'),
             ('L3','SW1','g2','H1','eth0','true'),
             ('L4','SW1','g3','H2','eth0','false'))
PORT_HEADER = ('Node','Port','Name','enabled','Mode','VLAN','Allowed')
LINK_HEADER = ('Link','ANode','APort','BNode','BPort','enabled')
IP_HEADER = ('Node','Port','IPv4')
ROUTE_HEADER = ('Node','Route','Destination','NextHop','OutPort')


def csv_text(header, rows):
    import csv
    import io
    out = io.StringIO(newline='')
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(header)
    writer.writerows(rows)
    return out.getvalue()


def _mapping(role, columns, rows, source_index, view_index, headers):
    item = view(columns, rows=rows, view_id=f'view-{view_index}', headers=headers, role=role)
    item['sourceId'] = f'src-{source_index}'
    return item


def _ods(text, columns):
    parts = ods_parts({'IP plan': text})
    parts['content.xml'] = parts['content.xml'].replace(b'1024', str(columns).encode())
    return ods_zip(parts)


def corpus_a():
    """Six independently structured original documents, all synthetic only."""
    port_text = csv_text(PORT_HEADER, PORT_ROWS)
    link_text = csv_text(LINK_HEADER, LINK_ROWS)
    sources = [
        source(DEVICES.encode(), 'synthetic-only-devices.csv', 'src-1'),
        source(ZONES.encode(), 'synthetic-only-zones.csv', 'src-2'),
        source(make_workbook({'Ports': port_text}), 'synthetic-only-interfaces.xlsx', 'src-3'),
        source(_ods(csv_text(IP_HEADER, IP_ROWS), 3), 'synthetic-only-ip-plan.ods', 'src-4'),
        source(csv_text(ROUTE_HEADER, [('R1','route1','192.168.30.0/24','10.0.0.2','eth0')]).encode(),
               'synthetic-only-routes.csv', 'src-5'),
        source(make_workbook({'Cables': link_text}), 'synthetic-only-cables.xlsx', 'src-6'),
    ]
    views = [
        _mapping('device_inventory', {'node.id':['A'],'node.label':['B'],'node.kind':['C'],'node.zoneId':['D']},
                 (2,3,4,5,6), 1, 1, ('Node','Label','Kind','Zone')),
        _mapping('zone_inventory', {'zone.id':['A'],'zone.label':['B']},
                 (2,3), 2, 2, ('Zone','Label')),
        _mapping('interface_inventory', {'port.nodeId':['A'],'port.id':['B'],'port.name':['C'],'port.enabled':['D']},
                 tuple(range(2,10)), 3, 3, PORT_HEADER),
        _mapping('interface_inventory', {'port.nodeId':['A'],'port.id':['B'],'port.vlanMode':['E'],'port.accessVlan':['F']},
                 (5,6), 3, 4, PORT_HEADER),
        _mapping('interface_inventory', {'port.nodeId':['A'],'port.id':['B'],'port.vlanMode':['E'],'port.allowedVlans':['G']},
                 (7,), 3, 5, PORT_HEADER),
        _mapping('ip_plan', {'ip.nodeId':['A'],'ip.portId':['B'],'ip.ipv4':['C']},
                 tuple(range(2,7)), 4, 6, IP_HEADER),
        _mapping('static_route_register', {'route.nodeId':['A'],'route.id':['B'],'route.destination':['C'],
                                           'route.nextHop':['D'],'route.outPort':['E']},
                 (2,), 5, 7, ROUTE_HEADER),
        _mapping('cable_register', {'link.id':['A'],'link.aNode':['B'],'link.aPort':['C'],
                                     'link.bNode':['D'],'link.bPort':['E'],'link.enabled':['F']},
                 (2,3,4,5), 6, 8, LINK_HEADER),
    ]
    transformations = [
        {'viewId':'view-4','targetField':'port.accessVlan','operation':'parse_vlan_integer','delimiter':None},
        {'viewId':'view-5','targetField':'port.allowedVlans','operation':'split_vlan_integer_list','delimiter':','},
    ]
    return {'contractVersion':'1','projectName':NAME,'sources':sources,'mappingViews':views,
            'transformations':transformations,'rowValues':[],'excludedUses':[],'selectedUnitIds':[]}


def corpus_b():
    """Combined rows carry several roles, with a documentation-only row."""
    header = ('Node','Label','Kind','Zone','Port','Name','enabled','Mode','VLAN','Allowed',
              'IPv4','Link','ANode','APort','BNode','BPort','LinkEnabled',
              'Route','Destination','NextHop','OutPort','Note')
    identities = {'R1':('Router 1','router','WAN'),'R2':('Router 2','router','WAN'),
                  'SW1':('Switch 1','switch','LAN'),'H1':('Host 1','host','LAN'),
                  'H2':('Host 2','host','LAN')}
    ips = {(n,p):ip for n,p,ip in IP_ROWS}
    rows = []
    for index, (node, port, label, enabled, mode, vlan, allowed) in enumerate(PORT_ROWS):
        name, kind, zone = identities[node]
        # R1's descriptive facts and zone reference are deliberately split
        # across two original rows sharing its explicit identity.
        if index == 0:
            zone = ''
        elif index == 1:
            name = kind = ''
        link = LINK_ROWS[index] if index < 4 else ('','','','','','')
        route = ('route1','192.168.30.0/24','10.0.0.2','eth0') if index == 0 else ('','','','')
        rows.append((node,name,kind,zone,port,label,enabled,mode,vlan,allowed,
                     ips.get((node,port),''),*link,*route,'synthetic only'))
    rows.append(('',)*21 + ('synthetic only documentation row',))
    combined = csv_text(header, rows)
    sources = [source(combined.encode(), 'synthetic-only-combined.csv', 'src-1'),
               source(ZONES.encode(), 'synthetic-only-zones.csv', 'src-2')]
    views = [
        _mapping('device_inventory', {'node.id':['A'],'node.label':['B'],'node.kind':['C'],'node.zoneId':['D']},
                 tuple(range(2,10)), 1, 1, header),
        _mapping('zone_inventory', {'zone.id':['A'],'zone.label':['B']}, (2,3), 2, 2, ('Zone','Label')),
        _mapping('interface_inventory', {'port.nodeId':['A'],'port.id':['E'],'port.name':['F'],'port.enabled':['G']},
                 tuple(range(2,10)), 1, 3, header),
        _mapping('interface_inventory', {'port.nodeId':['A'],'port.id':['E'],'port.vlanMode':['H'],'port.accessVlan':['I']},
                 (5,6), 1, 4, header),
        _mapping('interface_inventory', {'port.nodeId':['A'],'port.id':['E'],'port.vlanMode':['H'],'port.allowedVlans':['J']},
                 (7,), 1, 5, header),
        _mapping('ip_plan', {'ip.nodeId':['A'],'ip.portId':['E'],'ip.ipv4':['K']},
                 (2,3,4,8,9), 1, 6, header),
        _mapping('static_route_register', {'route.nodeId':['A'],'route.id':['R'],'route.destination':['S'],
                                           'route.nextHop':['T'],'route.outPort':['U']},
                 (2,), 1, 7, header),
        _mapping('cable_register', {'link.id':['L'],'link.aNode':['M'],'link.aPort':['N'],
                                     'link.bNode':['O'],'link.bPort':['P'],'link.enabled':['Q']},
                 (2,3,4,5), 1, 8, header),
        _mapping('documentation_only', {}, (10,), 1, 9, header),
    ]
    transformations = [
        {'viewId':'view-4','targetField':'port.accessVlan','operation':'parse_vlan_integer','delimiter':None},
        {'viewId':'view-5','targetField':'port.allowedVlans','operation':'split_vlan_integer_list','delimiter':','},
    ]
    return {'contractVersion':'1','projectName':NAME,'sources':sources,'mappingViews':views,
            'transformations':transformations,'rowValues':[],'excludedUses':[],'selectedUnitIds':[]}


def expected_network():
    def p(identifier, name, enabled=True, ipv4=None, vlan=None):
        result = {'id':identifier,'name':name,'enabled':enabled,'ipv4':ipv4}
        if vlan is not None:
            result['vlan'] = vlan
        return result
    return {
        'schemaVersion':'1.3','name':NAME,
        'zones':[{'id':'LAN','label':'Local LAN'},{'id':'WAN','label':'Wide area'}],
        'nodes':[
            {'id':'H1','label':'Host 1','kind':'host','x':110,'y':110,'zoneId':'LAN',
             'ports':[p('eth0','Ethernet 0',ipv4='192.168.10.20/24')]},
            {'id':'H2','label':'Host 2','kind':'host','x':370,'y':110,'zoneId':'LAN',
             'ports':[p('eth0','Ethernet 0',False,'192.168.10.21/24')]},
            {'id':'R1','label':'Router 1','kind':'router','x':630,'y':110,'zoneId':'WAN',
             'ports':[p('eth0','Ethernet 0',ipv4='10.0.0.1/30'),
                      p('eth1','Ethernet 1',ipv4='192.168.10.1/24')],
             'staticRoutes':[{'id':'route1','destination':'192.168.30.0/24',
                              'nextHop':'10.0.0.2','outPort':'eth0'}]},
            {'id':'R2','label':'Router 2','kind':'router','x':110,'y':330,'zoneId':'WAN',
             'ports':[p('eth0','Ethernet 0',ipv4='10.0.0.2/30')]},
            {'id':'SW1','label':'Switch 1','kind':'switch','x':370,'y':330,'zoneId':'LAN',
             'ports':[p('g1','Gigabit 1',vlan={'mode':'access','vlan':10}),
                      p('g2','Gigabit 2',vlan={'mode':'access','vlan':10}),
                      p('g3','Gigabit 3',vlan={'mode':'trunk','allowedVlans':[10,20]})]},
        ],
        'links':[
            {'id':'L1','a':{'node':'R1','port':'eth0'},'b':{'node':'R2','port':'eth0'},'enabled':True},
            {'id':'L2','a':{'node':'R1','port':'eth1'},'b':{'node':'SW1','port':'g1'},'enabled':True},
            {'id':'L3','a':{'node':'SW1','port':'g2'},'b':{'node':'H1','port':'eth0'},'enabled':True},
            {'id':'L4','a':{'node':'SW1','port':'g3'},'b':{'node':'H2','port':'eth0'},'enabled':False},
        ],
    }


def select_all(req):
    discovery = build_plan(req)['plan']
    req['selectedUnitIds'] = sorted(u['unitId'] for u in discovery['units'])
    return build_plan(req)['plan']


class Integrated4CAcceptance(unittest.TestCase):
    def test_corpora_share_exact_network_and_historical_replay(self):
        expected = expected_network()
        self.assertEqual(validate_project(expected), expected)
        for label, make in (('A',corpus_a),('B',corpus_b)):
            with self.subTest(corpus=label):
                req = make()
                plan = select_all(req)
                self.assertTrue(plan['canApply'], plan['diagnostics'])
                project = plan['proposedProject']
                self.assertEqual(canonical_network_view(project), expected)
                self.assertEqual(validate_project(project), project)
                self.assertEqual(project['schemaVersion'], '1.4')
                receipt = project['importEvidence']
                self.assertEqual(receipt['sourceStorage'], 'external_not_embedded')
                self.assertEqual(len(receipt['acceptedChanges']), 2+5+8+5+1+4)
                self.assertEqual(len(plan['units']), 25)
                self.assertEqual(len(plan['claims']), 28 if label == 'A' else 31)
                self.assertEqual({u['kind'] for u in plan['units']},
                                 {'zone','node','port','ipBinding','staticRoute','link'})
                self.assertEqual({s['sha256'] for s in receipt['sources']},
                                 {hashlib.sha256(__import__('base64').b64decode(s['contentBase64'])).hexdigest()
                                  for s in req['sources']})
                for change in receipt['acceptedChanges']:
                    self.assertEqual(change['changeIds'], [internal_id('c-', [
                        change['unitId'], 'setExplicitField' if change['targetKind']=='ipBinding' else 'create',
                        'port.ipv4' if change['targetKind']=='ipBinding' else '__object__'])])
                    self.assertEqual(set(change['fieldValues']), set(change['fieldOrigins']))
                if label == 'A':
                    port_change = next(c for c in receipt['acceptedChanges']
                                       if c['targetKind']=='port' and c['targetKey']=='["R1","eth0"]')
                    ip_change = next(c for c in receipt['acceptedChanges']
                                     if c['targetKind']=='ipBinding' and c['targetKey']=='["R1","eth0"]')
                    self.assertEqual({r['sourceId'] for r in port_change['fieldOrigins']['name']}, {'src-3'})
                    self.assertEqual({r['sourceId'] for r in ip_change['fieldOrigins']['port.ipv4']}, {'src-4'})
                self.assertEqual(verify_sources({'project':project,'sources':req['sources']})['sourceStatus'],
                                 'SOURCE_VERIFIED')
                self.assertEqual(evidence_status({'project':project})['baselineStatus'], 'BASELINE_MATCH')
                if label == 'B':
                    review = next(r for r in plan['recordReviews'] if r['sourceId']=='src-1' and r['row']==2)
                    self.assertEqual(len(review['viewUses']), 5)
                    self.assertIn('V2', next(r for r in plan['recordReviews']
                                            if r['sourceId']=='src-1' and r['row']==2)['unmappedAddresses'])
                    r1_claims = [c for c in plan['claims'] if c['targetKind']=='node' and c['targetKey']=='R1']
                    self.assertEqual(len(r1_claims), 2)
                    self.assertEqual(set().union(*(set(c['fields']) for c in r1_claims)),
                                     {'node.id','node.label','node.kind','node.zoneId'})
                self.assertEqual(topology_trace(project,'R2','H1')['status'], 'PATH_PRESENT')
                self.assertEqual(topology_trace(project,'R2','H2')['status'], 'NO_PATH')
                self.assertEqual(ConnectedRoutingTable(project,'R1').lookup('192.168.30.4')
                                 ['selectedRoute']['routeId'], 'route1')
                inactive_route = copy.deepcopy(project)
                next(n for n in inactive_route['nodes'] if n['id']=='R1')['ports'][0]['enabled'] = False
                self.assertFalse(any(route['type']=='STATIC' for route in
                                     ConnectedRoutingTable(inactive_route,'R1').routes()))

    def test_selection_conflicts_and_no_implicit_objects(self):
        req = corpus_a()
        discovery = build_plan(req)['plan']
        units = {u['kind']:u for u in discovery['units'] if u['kind'] in ('staticRoute','link')}
        for kind in ('staticRoute','link'):
            req['selectedUnitIds'] = [units[kind]['unitId']]
            plan = build_plan(req)['plan']
            self.assertFalse(plan['canApply'])
            self.assertIsNone(plan['proposedProject'])
            self.assertIn('SELECTED_UNIT_NOT_ACTIONABLE', [d['code'] for d in plan['diagnostics']])
        req = corpus_a()
        req['mappingViews'] = [v for v in req['mappingViews'] if v['role'] != 'cable_register']
        req['selectedUnitIds'] = sorted(u['unitId'] for u in build_plan(req)['plan']['units'])
        no_cables = build_plan(req)['plan']
        self.assertTrue(no_cables['canApply'])
        self.assertEqual(no_cables['proposedProject']['links'], [])

    def test_cross_document_negative_matrix(self):
        import base64
        import csv
        import io
        # Each cell change is made in an actual combined CSV source, preserving
        # all other rows and the same explicitly chosen mapping views.
        cases = (
            ('node_kind',3,'C','host','node','FIELD_CONFLICT'),
            ('port_enabled',2,'G','yes','port','UNMAPPED_BOOLEAN'),
            ('port_ipv4',2,'K','invalid','ipBinding','INVALID_IPV4'),
            ('route_outport',2,'U','unknown','staticRoute','UNDECLARED_PORT'),
            ('route_nexthop',2,'T','10.0.0.5','staticRoute','INVALID_ROUTE_NEXTHOP'),
            ('link_bnode',2,'O','UNKNOWN','link','UNDECLARED_B_PORT'),
            ('link_bport',2,'P','unknown','link','UNDECLARED_B_PORT'),
            ('link_internal',2,'O','R1','link','INTERNAL_LINK'),
            ('link_boolean',2,'Q','yes','link','UNMAPPED_BOOLEAN'),
        )
        for name, row, column, replacement, kind, code in cases:
            with self.subTest(case=name):
                req = corpus_b()
                raw = base64.b64decode(req['sources'][0]['contentBase64']).decode()
                values = list(csv.reader(io.StringIO(raw)))
                position = 0
                for char in column:
                    position = position*26 + ord(char)-64
                values[row-1][position-1] = replacement
                req['sources'][0] = source(csv_text(values[0], values[1:]).encode(),
                                           req['sources'][0]['filename'], 'src-1')
                plan = build_plan(req)['plan']
                affected = [u for u in plan['units'] if u['kind']==kind]
                self.assertTrue(affected)
                self.assertTrue(any(u['status'] in ('BLOCKED','INVALID') for u in affected))
                self.assertIn(code, [d['code'] for d in plan['diagnostics']])
                self.assertTrue(any(d['sourceRefs'] for d in plan['diagnostics'] if d['code']==code))
                req['selectedUnitIds'] = sorted(u['unitId'] for u in plan['units'])
                selected = build_plan(req)['plan']
                self.assertFalse(selected['canApply'])
                self.assertIsNone(selected['proposedProject'])
        req = corpus_a()
        req['excludedUses'] = [{'viewId':'view-6','row':2,'reason':'synthetic only excluded IP'}]
        plan = build_plan(req)['plan']
        self.assertEqual(next(u for u in plan['units'] if u['kind']=='staticRoute')['status'], 'BLOCKED')
        self.assertIn('MISSING_PORT_IPV4', [d['code'] for d in plan['diagnostics']])

    def test_conflicting_facts_on_additional_source_rows(self):
        import base64
        import csv
        import io
        # A new original row complements or contradicts an existing selected
        # object. The respective role explicitly includes that row.
        cases = (
            ('port name','view-3',{'A':'R1','E':'eth0','F':'Other','G':'true'},'port','F'),
            ('port enabled','view-3',{'A':'R1','E':'eth0','F':'Ethernet 0','G':'false'},'port','G'),
            ('access VLAN','view-4',{'A':'SW1','E':'g1','H':'access','I':'20'},'port','I'),
            ('IPv4','view-6',{'A':'R1','E':'eth0','K':'10.0.0.9/30'},'ipBinding','K'),
            ('route destination','view-7',{'A':'R1','R':'route1','S':'192.168.40.0/24',
                                           'T':'10.0.0.2','U':'eth0'},'staticRoute','S'),
            ('link enabled','view-8',{'L':'L1','M':'R1','N':'eth0','O':'R2','P':'eth0',
                                     'Q':'false'},'link','Q'),
            ('reversed link','view-8',{'L':'L1','M':'R2','N':'eth0','O':'R1','P':'eth0',
                                      'Q':'true'},'link','M'),
        )
        for label, view_id, fields, kind, disputed in cases:
            with self.subTest(case=label):
                req = corpus_b()
                raw = base64.b64decode(req['sources'][0]['contentBase64']).decode()
                values = list(csv.reader(io.StringIO(raw)))
                extra = ['']*len(values[0])
                for column, value in fields.items():
                    position = 0
                    for char in column:
                        position = position*26 + ord(char)-64
                    extra[position-1] = value
                values.append(extra)
                req['sources'][0] = source(csv_text(values[0], values[1:]).encode(),
                                           req['sources'][0]['filename'], 'src-1')
                next(v for v in req['mappingViews'] if v['viewId']==view_id)['selectedRows'].append(11)
                plan = build_plan(req)['plan']
                self.assertIn('FIELD_CONFLICT', [d['code'] for d in plan['diagnostics']])
                self.assertTrue(any(u['kind']==kind and u['status']=='BLOCKED' for u in plan['units']))
                refs = [ref for d in plan['diagnostics'] if d['code']=='FIELD_CONFLICT'
                        for ref in d['sourceRefs']]
                self.assertIn(f'{disputed}11', {ref['address'] for ref in refs})
                req['selectedUnitIds'] = sorted(u['unitId'] for u in plan['units'])
                selected = build_plan(req)['plan']
                self.assertFalse(selected['canApply'])
                self.assertIsNone(selected['proposedProject'])

    def test_selected_port_occupancy_across_link_units(self):
        import base64
        import csv
        import io
        req = corpus_b()
        rows = list(csv.reader(io.StringIO(base64.b64decode(req['sources'][0]['contentBase64']).decode())))
        # L2 now tries to reuse R1/eth0, which L1 already occupies.
        rows[2][12:14] = ['R1','eth0']
        req['sources'][0] = source(csv_text(rows[0], rows[1:]).encode(),
                                   req['sources'][0]['filename'], 'src-1')
        discovery = build_plan(req)['plan']
        self.assertEqual(next(u for u in discovery['units'] if u['kind']=='link' and
                              u['targetKey']=='L2')['status'], 'ACTIONABLE')
        req['selectedUnitIds'] = sorted(u['unitId'] for u in discovery['units'])
        selected = build_plan(req)['plan']
        self.assertFalse(selected['canApply'])
        self.assertIsNone(selected['proposedProject'])
        self.assertIn('PORT_OCCUPIED', [d['code'] for d in selected['diagnostics']])

    def test_stable_input_and_changed_presentation_order(self):
        base = corpus_a()
        first = select_all(base)
        repeated = build_plan(copy.deepcopy(base))['plan']
        self.assertEqual(first['fingerprint'], repeated['fingerprint'])
        self.assertEqual(first['units'], repeated['units'])
        self.assertEqual(first['proposedProject'], repeated['proposedProject'])
        reordered = corpus_a()
        reordered['mappingViews'].reverse()
        names = {mapping['viewId']:f'view-{i}'
                 for i,mapping in enumerate(reordered['mappingViews'],1)}
        for mapping in reordered['mappingViews']:
            mapping['viewId'] = names[mapping['viewId']]
        for transformation in reordered['transformations']:
            transformation['viewId'] = names[transformation['viewId']]
        reordered['sources'][0] = source(('\n'.join([DEVICES.splitlines()[0]] +
            list(reversed(DEVICES.splitlines()[1:])))+'\n').encode(),
            reordered['sources'][0]['filename'], 'src-1')
        changed = select_all(reordered)
        self.assertTrue(changed['canApply'])
        self.assertEqual(canonical_network_view(changed['proposedProject']), expected_network())
        self.assertNotEqual(first['fingerprint'], changed['fingerprint'])

    def test_real_store_and_source_tamper(self):
        req = corpus_a()
        project = select_all(req)['proposedProject']
        with tempfile.TemporaryDirectory() as folder:
            store = ProjectStore(Path(folder))
            path = Path(folder)/'synthetic-only-integrated.yadilab'
            self.assertFalse(path.exists())
            store.save('synthetic-only-integrated', project, None)
            self.assertTrue(path.is_file())
            saved = store.read('synthetic-only-integrated')['project']
            self.assertEqual(saved, project)
            self.assertEqual(verify_sources({'project':saved,'sources':req['sources']})['replayStatus'],
                             'MATCH')
            modified = copy.deepcopy(saved)
            modified['links'][3]['enabled'] = True
            self.assertEqual(modified['importEvidence'], saved['importEvidence'])
            self.assertEqual(evidence_status({'project':modified})['baselineStatus'],
                             'CHANGED_SINCE_IMPORT')
            self.assertEqual(verify_sources({'project':modified,'sources':req['sources']})['sourceStatus'],
                             'SOURCE_VERIFIED')
            modified['links'][3]['enabled'] = False
            self.assertEqual(evidence_status({'project':modified})['baselineStatus'], 'BASELINE_MATCH')
            altered = copy.deepcopy(req['sources'])
            altered[-1]['contentBase64'] = __import__('base64').b64encode(b'changed').decode()
            with self.assertRaises(ProjectValidationError):
                verify_sources({'project':saved,'sources':altered})
            self.assertEqual(store.read('synthetic-only-integrated')['project'], saved)


if __name__ == '__main__':
    unittest.main()
