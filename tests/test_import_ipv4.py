"""Explicit port IPv4 bindings in the source-backed import plan."""
import copy
import tempfile
import unittest
from pathlib import Path

from network_core.import_plan import build_plan, internal_id
from network_core.import_verification import evidence_status, verify_sources
from network_core.model import ProjectValidationError, validate_project
from network_core.storage import ProjectStore
from test_import_plan import source, view


def request(address='192.168.10.20/24', *, ip_role=True):
    raw = f'Device,Label,Kind,Port,PortName,Enabled,IPv4\nSERVER1,Server,host,eth0,Ethernet 0,true,{address}\n'.encode()
    headers = ('Device', 'Label', 'Kind', 'Port', 'PortName', 'Enabled', 'IPv4')
    node = view({'node.id':['A'], 'node.label':['B'], 'node.kind':['C']}, headers=headers)
    port = view({'port.nodeId':['A'], 'port.id':['D'], 'port.name':['E'], 'port.enabled':['F']},
                view_id='view-2', headers=headers, role='interface_inventory')
    if ip_role:
        ip = view({'ip.nodeId':['A'], 'ip.portId':['D'], 'ip.ipv4':['G']},
                  view_id='view-3', headers=headers, role='ip_plan')
        views = [node, port, ip]
    else:
        port['columns']['port.ipv4'] = ['G']
        views = [node, port]
    return {'contractVersion':'1', 'projectName':'IPv4 documented', 'sources':[source(raw)],
            'mappingViews':views, 'transformations':[], 'rowValues':[],
            'excludedUses':[], 'selectedUnitIds':[]}


def select_all(req):
    discovery = build_plan(req)['plan']
    req['selectedUnitIds'] = sorted(u['unitId'] for u in discovery['units'])
    return build_plan(req)['plan']


class IPv4ImportTests(unittest.TestCase):
    def test_missing_support_reproduced_by_positive_binding(self):
        for ip_role in (True, False):
            with self.subTest(ip_role=ip_role):
                plan = select_all(request(ip_role=ip_role))
                self.assertTrue(plan['canApply'])
                units = {u['kind']:u for u in plan['units']}
                self.assertEqual(units['ipBinding']['dependencies'], [units['port']['unitId']])
                self.assertEqual(units['ipBinding']['targetKey'], '["SERVER1","eth0"]')
                self.assertEqual(units['ipBinding']['unitId'],
                                 internal_id('u-', ['ipBinding','["SERVER1","eth0"]']))
                self.assertEqual(plan['proposedProject']['nodes'][0]['ports'],
                                 [{'id':'eth0','name':'Ethernet 0','enabled':True,
                                   'ipv4':'192.168.10.20/24'}])

    def test_invalid_address_and_missing_port_fail_closed(self):
        for address in ('192.168.10.20', '192.168.10.20/33', '999.168.10.20/24',
                        '192.168.10.20/', '192.168.10.20/24 extra', '2001:db8::1/64'):
            with self.subTest(address=address):
                plan = build_plan(request(address))['plan']
                self.assertEqual(next(u for u in plan['units'] if u['kind']=='ipBinding')['status'], 'INVALID')
        req = request()
        req['mappingViews'][2]['columns'].pop('ip.portId')
        plan = build_plan(req)['plan']
        self.assertFalse(any(u['kind']=='ipBinding' and u['status']=='ACTIONABLE' for u in plan['units']))
        req = request()
        req['mappingViews'][2]['columns']['ip.portId'] = ['B']
        plan = build_plan(req)['plan']
        self.assertEqual(next(u for u in plan['units'] if u['kind']=='ipBinding')['status'], 'BLOCKED')

    def test_dependencies_conflicts_and_replay(self):
        req = request()
        units = {u['kind']:u for u in build_plan(req)['plan']['units']}
        req['selectedUnitIds'] = [units['ipBinding']['unitId']]
        self.assertFalse(build_plan(req)['plan']['canApply'])
        req['selectedUnitIds'] = sorted((units['ipBinding']['unitId'], units['port']['unitId']))
        self.assertFalse(build_plan(req)['plan']['canApply'])
        req['selectedUnitIds'] = sorted(u['unitId'] for u in units.values())
        plan = build_plan(req)['plan']
        self.assertTrue(plan['canApply'])
        binding = next(c for c in plan['proposedProject']['importEvidence']['acceptedChanges']
                       if c['targetKind']=='ipBinding')
        self.assertEqual(binding['changeIds'], [internal_id('c-', [units['ipBinding']['unitId'],
                                                           'setExplicitField','port.ipv4'])])
        self.assertEqual(binding['fieldValues'], {'port.ipv4':'192.168.10.20/24'})
        self.assertEqual({r['address'] for r in binding['fieldOrigins']['port.ipv4']}, {'G2'})
        self.assertEqual(verify_sources({'project':plan['proposedProject'],
                                         'sources':req['sources']})['replayStatus'], 'MATCH')
        with tempfile.TemporaryDirectory() as folder:
            store = ProjectStore(Path(folder))
            store.save('ipv4', plan['proposedProject'], None)
            saved = store.read('ipv4')['project']
            self.assertEqual(saved['nodes'][0]['ports'][0]['ipv4'], '192.168.10.20/24')
            self.assertEqual(verify_sources({'project':saved,'sources':req['sources']})['sourceStatus'],
                             'SOURCE_VERIFIED')
            edited = copy.deepcopy(saved)
            edited['nodes'][0]['ports'][0]['ipv4'] = '192.168.10.21/24'
            self.assertEqual(evidence_status({'project':edited})['baselineStatus'], 'CHANGED_SINCE_IMPORT')
            self.assertEqual(verify_sources({'project':edited,'sources':req['sources']})['replayStatus'], 'MATCH')

        req = request(ip_role=False)
        duplicate = view({'ip.nodeId':['A'], 'ip.portId':['D'], 'ip.ipv4':['G']},
                         view_id='view-3', headers=('Device','Label','Kind','Port','PortName','Enabled','IPv4'),
                         role='ip_plan')
        req['mappingViews'].append(duplicate)
        plan = select_all(req)
        self.assertEqual(len([u for u in plan['units'] if u['kind']=='ipBinding']), 1)
        binding = next(c for c in plan['proposedProject']['importEvidence']['acceptedChanges']
                       if c['targetKind']=='ipBinding')
        self.assertEqual(len(binding['fieldOrigins']['port.ipv4']), 2)
        req['rowValues'] = [{'viewId':'view-3','row':2,'targetField':'ip.ipv4',
                             'valueType':'text','value':'192.168.10.30/24'}]
        self.assertIn('FIELD_CONFLICT', [d['code'] for d in build_plan(req)['plan']['diagnostics']])

    def test_tampered_binding_rejected(self):
        req = request()
        project = select_all(req)['proposedProject']
        altered = source(b'Device,Label,Kind,Port,PortName,Enabled,IPv4\n'
                         b'SERVER1,Server,host,eth0,Ethernet 0,true,192.168.10.30/24\n')
        with self.assertRaises(ProjectValidationError):
            verify_sources({'project':project, 'sources':[altered]})
        for tamper in ('target', 'unit', 'change', 'field', 'origin', 'fingerprint'):
            damaged = copy.deepcopy(project)
            evidence = damaged['importEvidence']
            binding = next(c for c in evidence['acceptedChanges'] if c['targetKind']=='ipBinding')
            if tamper == 'target': binding['targetKey'] = '["SERVER1", "eth0"]'
            elif tamper == 'unit': binding['unitId'] = 'u-' + '0'*32
            elif tamper == 'change': binding['changeIds'] = ['c-' + '0'*32]
            elif tamper == 'field': binding['fieldValues']['node.label'] = 'Oops'
            elif tamper == 'origin': binding['fieldOrigins']['port.ipv4'] = []
            else: evidence['planFingerprint'] = '0'*64
            with self.subTest(tamper=tamper), self.assertRaises(ProjectValidationError):
                validate_project(damaged)

    def test_excluded_or_blocked_port_cannot_support_binding(self):
        req = request()
        req['excludedUses'] = [{'viewId':'view-2','row':2,'reason':'Port not approved'}]
        plan = build_plan(req)['plan']
        self.assertEqual(next(u for u in plan['units'] if u['kind']=='ipBinding')['status'], 'BLOCKED')
        self.assertFalse(plan['canApply'])
        req = request()
        req['mappingViews'][1]['columns'].pop('port.enabled')
        plan = build_plan(req)['plan']
        self.assertEqual(next(u for u in plan['units'] if u['kind']=='port')['status'], 'BLOCKED')
        self.assertEqual(next(u for u in plan['units'] if u['kind']=='ipBinding')['status'], 'BLOCKED')

    def test_separate_source_and_conflicting_source(self):
        req = request()
        second = b'Device,Port,IPv4\nSERVER1,eth0,192.168.10.20/24\n'
        req['sources'].append(source(second, 'ip-plan.csv', 'src-2'))
        ip = req['mappingViews'][2]
        ip['sourceId'] = 'src-2'
        ip['expectedHeaders'] = ['Device','Port','IPv4']
        ip['columns'] = {'ip.nodeId':['A'], 'ip.portId':['B'], 'ip.ipv4':['C']}
        plan = select_all(req)
        self.assertTrue(plan['canApply'])
        binding = next(c for c in plan['proposedProject']['importEvidence']['acceptedChanges']
                       if c['targetKind']=='ipBinding')
        self.assertEqual([(r['sourceId'],r['address']) for r in binding['fieldOrigins']['port.ipv4']],
                         [('src-2','C2')])
        self.assertEqual(verify_sources({'project':plan['proposedProject'],
                                         'sources':req['sources']})['sourceStatus'], 'SOURCE_VERIFIED')
        req['mappingViews'][1]['columns']['port.ipv4'] = ['G']
        plan = build_plan(req)['plan']
        self.assertTrue(all(u['status']=='ACTIONABLE' for u in plan['units']))
        second = b'Device,Port,IPv4\nSERVER1,eth0,192.168.10.30/24\n'
        req['sources'][1] = source(second, 'ip-plan.csv', 'src-2')
        plan = build_plan(req)['plan']
        binding_unit = next(u for u in plan['units'] if u['kind']=='ipBinding')
        self.assertEqual(binding_unit['status'], 'BLOCKED')
        conflict = next(d for d in binding_unit['diagnostics'] if d['code']=='FIELD_CONFLICT')
        self.assertEqual({r['sourceId'] for r in conflict['sourceRefs']}, {'src-1','src-2'})

    def test_composite_port_identity(self):
        for rows, expected in (
            ((b'SERVER1,Server,host,eth0,Ethernet 0,true,192.168.10.20/24',
              b'SERVER2,Second,host,eth0,Ethernet 0,true,192.168.10.21/24'),
             [('SERVER1','eth0','192.168.10.20/24'), ('SERVER2','eth0','192.168.10.21/24')]),
            ((b'SERVER1,Server,host,eth0,Ethernet 0,true,192.168.10.20/24',
              b'SERVER1,Server,host,eth1,Ethernet 1,true,10.0.0.1/30'),
             [('SERVER1','eth0','192.168.10.20/24'), ('SERVER1','eth1','10.0.0.1/30')]),
        ):
            req = request()
            req['sources'] = [source(b'Device,Label,Kind,Port,PortName,Enabled,IPv4\n' + b'\n'.join(rows) + b'\n')]
            for mapping in req['mappingViews']:
                mapping['selectedRows'] = [2,3]
            plan = select_all(req)
            self.assertTrue(plan['canApply'])
            actual = [(node['id'], port['id'], port['ipv4']) for node in plan['proposedProject']['nodes']
                      for port in node['ports']]
            self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
