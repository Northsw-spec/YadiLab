"""Independent candidate, historical receipt, HTTP and disk regression cases."""
import copy
import hashlib
import http.client
import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from urllib.request import Request, urlopen

from network_core.import_plan import build_plan, canonical_json, node_layout
from network_core.model import ProjectValidationError, canonical_network_view, validate_project
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_import_plan import request, source
from xlsx_fixture import workbook_parts, zip_parts
from ods_fixture import ods_parts, zip_parts as ods_zip


def selected_request(raw=b'ID,Label,Kind\nSW-01,Core,switch\n'):
    req = request(raw)
    first = build_plan(req)['plan']
    req['selectedUnitIds'] = [first['units'][0]['unitId']]
    return req


class CandidateTests(unittest.TestCase):
    def test_selected_canonical_node_and_historical_receipt(self):
        req = selected_request()
        first = build_plan(req)
        second = build_plan(copy.deepcopy(req))
        self.assertEqual(first, second)
        plan = first['plan']
        self.assertEqual(set(first), {'plan'})
        self.assertTrue(plan['canApply'])
        project = plan['proposedProject']
        self.assertEqual(set(project), {'schemaVersion', 'name', 'zones', 'nodes', 'links', 'importEvidence'})
        self.assertEqual(project['nodes'], [{'id':'SW-01','label':'Core','kind':'switch',
                                            'x':110,'y':110,'zoneId':None,'ports':[]}])
        self.assertEqual(project['links'], [])
        self.assertEqual(plan['units'][0]['changes'][0]['operation'], 'create')
        receipt = project['importEvidence']
        self.assertEqual(receipt['acceptedChanges'][0]['changeIds'],
                         ['c-b8d5c4d8b632f6649c65c06f220a54bc'])
        self.assertEqual(receipt['acceptedChanges'][0]['fieldOrigins']['ports'], [])
        self.assertEqual(receipt['acceptedChanges'][0]['fieldOrigins']['zoneId'], [])
        self.assertEqual(receipt['acceptedChanges'][0]['fieldOrigins']['x'][0]['kind'], 'derived_layout')
        self.assertEqual(receipt['decisions'][0], {'sourceId':'src-1','tableId':'sheet-1','row':1,
            'viewId':None,'status':'DOCUMENTATION_ONLY','reason':None,'unitIds':[]})
        self.assertEqual(receipt['baselineNetworkSha256'],
                         '169b8cd93667b3f2c3ab8094a314dc05815ab6d65a8dada33a7d7bc5279e3f1c')
        self.assertEqual(canonical_network_view(project)['schemaVersion'], '1.3')
        self.assertNotIn('importEvidence', canonical_network_view(project))

    def test_duplicate_claims_and_blocked_selection(self):
        raw = b'ID,Label,Kind\nSW-01,Core,switch\nSW-01,Core,switch\n'
        req = request(raw)
        req['mappingViews'][0]['selectedRows'] = [2, 3]
        req['selectedUnitIds'] = [build_plan(req)['plan']['units'][0]['unitId']]
        plan = build_plan(req)['plan']
        self.assertEqual(len(plan['proposedProject']['nodes']), 1)
        self.assertEqual(len(plan['proposedProject']['importEvidence']['acceptedChanges'][0]
                             ['fieldOrigins']['label']), 2)
        req['sources'] = [source(raw.replace(b'SW-01,Core,switch\nSW-01,Core',
                                             b'SW-01,Core,switch\nSW-01,Edge'))]
        plan = build_plan(req)['plan']
        self.assertIsNone(plan['proposedProject'])
        self.assertFalse(plan['canApply'])
        self.assertIn('SELECTED_UNIT_NOT_ACTIONABLE', [d['code'] for d in plan['diagnostics']])

    def test_explicit_row_decision_and_value_map_replay(self):
        req = request(b'ID,Label,Kind\n,Core,managed switch\n')
        req['mappingViews'][0]['valueMaps'] = {'node.kind': {'managed switch':'switch'}}
        req['rowValues'] = [{'viewId':'view-1','row':2,'targetField':'node.id',
                             'valueType':'text','value':'SW-01'}]
        req['selectedUnitIds'] = [build_plan(req)['plan']['units'][0]['unitId']]
        project = build_plan(req)['plan']['proposedProject']
        self.assertEqual(project['nodes'][0]['id'], 'SW-01')
        accepted = project['importEvidence']['acceptedChanges'][0]
        self.assertEqual([r['kind'] for r in accepted['fieldOrigins']['id']], ['user_decision'])
        self.assertEqual({r['kind'] for r in accepted['fieldOrigins']['kind']},
                         {'source_cell', 'user_decision'})
        damaged = copy.deepcopy(project)
        damaged['importEvidence']['acceptedChanges'][0]['fieldOrigins']['id'][0][
            'decisionId'] = 'd-' + '0' * 32
        with self.assertRaises(ProjectValidationError):
            validate_project(damaged)

    def test_unknown_id_and_semantically_invalid_sources(self):
        req = request()
        req['selectedUnitIds'] = ['u-' + '0' * 32]
        with self.assertRaises(ProjectValidationError):
            build_plan(req)
        for raw in (b'ID,Label,Kind\n,Core,switch\n',
                    b'ID,Label,Kind\nSW-01,Core,unknown\n'):
            req = request(raw)
            plan = build_plan(req)['plan']
            self.assertFalse(plan['canApply'])
            self.assertIsNone(plan['proposedProject'])

    def test_real_xlsx_ods_candidates_and_numeric_id_rejection(self):
        workbook = zip_parts(workbook_parts({'Inventory':'ID,Label,Kind\nH-01,Host,host\n'}))
        ods = ods_parts({'Inventory':'ID,Label,Kind\nH-01,Host,host\n'})
        ods['content.xml'] = ods['content.xml'].replace(b'1024', b'3')
        for raw, filename in ((workbook, 'inventory.xlsx'),
                              (ods_zip(ods), 'inventory.ods')):
            req = request()
            req['sources'] = [source(raw, filename)]
            req['selectedUnitIds'] = [build_plan(req)['plan']['units'][0]['unitId']]
            plan = build_plan(req)['plan']
            self.assertTrue(plan['canApply'])
            self.assertEqual(plan['proposedProject']['nodes'][0]['id'], 'H-01')
            self.assertEqual(plan['sourceManifest'][0]['sha256'], hashlib.sha256(raw).hexdigest())
        parts = workbook_parts({'Inventory':'ID,Label,Kind\n1,Host,host\n'})
        parts['xl/worksheets/sheet1.xml'] = parts['xl/worksheets/sheet1.xml'].replace(
            b'<c r="A2" t="inlineStr"><is><t>1</t></is></c>',
            b'<c r="A2" t="n"><v>1</v></c>')
        req = request()
        req['sources'] = [source(zip_parts(parts), 'numeric.xlsx')]
        plan = build_plan(req)['plan']
        self.assertIsNone(plan['claims'][0]['targetKey'])
        self.assertEqual(plan['units'], [])

    def test_layout_vectors_and_bounds(self):
        self.assertEqual(node_layout([]), {})
        self.assertEqual(node_layout(['A']), {'A': (110, 110)})
        self.assertEqual([node_layout(['A','B','C','D'])[v] for v in 'ABCD'],
                         [(110,110),(370,110),(110,330),(370,330)])
        self.assertEqual(node_layout(['A','B','C','D','E'])['E'], (370,330))
        self.assertEqual(max(y for x,y in node_layout([f'N{i:04d}' for i in range(1821)]).values()), 9350)
        positions = node_layout([f'N{i:04d}' for i in range(2000)])
        self.assertEqual(max(x for x,y in positions.values()), 11550)
        self.assertEqual(max(y for x,y in positions.values()), 9790)
        with self.assertRaises(ProjectValidationError):
            node_layout([f'N{i:04d}' for i in range(2001)])

    def test_full_candidate_layout_boundary(self):
        for count in (1821, 2000, 2001):
            raw = b'ID,Label,Kind\n' + b''.join(
                f'N{i:04d},Node {i},host\n'.encode() for i in range(count))
            req = request(raw)
            req['mappingViews'][0]['selectedRows'] = list(range(2, count + 2))
            req['selectedUnitIds'] = sorted(
                unit['unitId'] for unit in build_plan(req)['plan']['units'])
            if count == 2001:
                with self.assertRaisesRegex(ProjectValidationError, '2000 selected nodes'):
                    build_plan(req)
            else:
                plan = build_plan(req)['plan']
                self.assertTrue(plan['canApply'])
                self.assertEqual(len(plan['proposedProject']['nodes']), count)
                self.assertLessEqual(max(n['y'] for n in plan['proposedProject']['nodes']), 100000)
                if count == 2000:
                    self.assertEqual(max(n['x'] for n in plan['proposedProject']['nodes']), 11550)
                    self.assertEqual(max(n['y'] for n in plan['proposedProject']['nodes']), 9790)
                self.assertEqual(plan['proposedProject']['links'], [])

    def test_numeric_projection_and_receipt_limits(self):
        project = build_plan(selected_request())['plan']['proposedProject']
        project['nodes'][0]['x'] = 1.0
        one = canonical_network_view(project)
        self.assertEqual(one['nodes'][0]['x'], 1)
        project['nodes'][0]['x'] = 1
        self.assertEqual(canonical_network_view(project), one)
        project['nodes'][0]['x'] = -0.0
        zero = canonical_network_view(project)
        project['nodes'][0]['x'] = 0
        self.assertEqual(canonical_network_view(project), zero)
        project['nodes'][0]['x'] = 1.5
        self.assertEqual(canonical_network_view(project)['nodes'][0]['x'], 1.5)
        for invalid in (float('nan'), float('inf')):
            project['nodes'][0]['x'] = invalid
            with self.assertRaises(ProjectValidationError):
                canonical_network_view(project)
        project = build_plan(selected_request())['plan']['proposedProject']
        project['importEvidence']['decisions'] *= 10000
        with self.assertRaisesRegex(ProjectValidationError, '2 MiB'):
            validate_project(project)
        req = request()
        req['sources'][0]['contentBase64'] = 'A' * (8 * 1024 * 1024)
        with self.assertRaisesRegex(ProjectValidationError, 'PAYLOAD_LIMIT'):
            build_plan(req)

    def test_manual_vlan_link_route_edit_keeps_receipt(self):
        req = request(b'ID,Label,Kind\nH-01,Host,host\nS-01,Switch,switch\n')
        req['mappingViews'][0]['selectedRows'] = [2, 3]
        req['selectedUnitIds'] = sorted(u['unitId'] for u in build_plan(req)['plan']['units'])
        project = build_plan(req)['plan']['proposedProject']
        receipt = canonical_json(project['importEvidence'])
        host = next(n for n in project['nodes'] if n['id'] == 'H-01')
        switch = next(n for n in project['nodes'] if n['id'] == 'S-01')
        host['ports'] = [{'id':'eth0','name':'eth0','enabled':True,
                          'ipv4':'192.0.2.10/24','mac':'02:00:00:00:00:0A'}]
        host['staticRoutes'] = [{'id':'route-1','destination':'203.0.113.0/24',
                                 'nextHop':'192.0.2.1','outPort':'eth0'}]
        switch['ports'] = [{'id':'ge1','name':'ge1','enabled':True,'ipv4':None,
                            'vlan':{'mode':'access','vlan':10}}]
        project['links'] = [{'id':'cable-1','a':{'node':'H-01','port':'eth0'},
                             'b':{'node':'S-01','port':'ge1'},'enabled':True}]
        edited = validate_project(project)
        self.assertEqual(edited['schemaVersion'], '1.4')
        self.assertEqual(canonical_json(edited['importEvidence']), receipt)
        self.assertEqual(len(canonical_network_view(edited)['links']), 1)

    def test_evidence_tampering_and_edit_preserve_history(self):
        project = build_plan(selected_request())['plan']['proposedProject']
        receipt = copy.deepcopy(project['importEvidence'])
        for mutate in (
            lambda e: e['acceptedChanges'][0]['changeIds'].__setitem__(0, 'c-' + '0' * 32),
            lambda e: e['acceptedChanges'][0]['fieldOrigins']['id'][0].__setitem__('address', 'B2'),
            lambda e: e['acceptedChanges'][0]['fieldOrigins'].__setitem__('ports',
                [copy.deepcopy(e['acceptedChanges'][0]['fieldOrigins']['id'][0])]),
            lambda e: e['acceptedChanges'][0]['fieldOrigins'].__setitem__('id',
                [copy.deepcopy(e['acceptedChanges'][0]['fieldOrigins']['x'][0])]),
            lambda e: e['acceptedChanges'][0]['fieldValues'].__setitem__('label', 'Fabricated'),
            lambda e: e.__setitem__('planFingerprint', '0' * 64),
            lambda e: e['decisions'].pop(0),
            lambda e: e['sources'][0].__setitem__('sha256', 'bad'),
            lambda e: e.__setitem__('extra', 'unknown'),
        ):
            altered = copy.deepcopy(project)
            mutate(altered['importEvidence'])
            with self.subTest(mutate=mutate), self.assertRaises(ProjectValidationError):
                validate_project(altered)
        edited = copy.deepcopy(project)
        edited['nodes'][0]['label'] = 'Renamed'
        edited['nodes'][0]['kind'] = 'host'
        edited['nodes'][0]['ports'] = [{'id':'eth0','name':'eth0','enabled':True,
                                        'ipv4':'192.0.2.10/24','mac':'02:00:00:00:00:0A'}]
        validated = validate_project(edited)
        self.assertEqual(validated['schemaVersion'], '1.4')
        self.assertEqual(canonical_json(validated['importEvidence']), canonical_json(receipt))
        self.assertNotEqual(hashlib.sha256(canonical_json(canonical_network_view(validated))).hexdigest(),
                            receipt['baselineNetworkSha256'])
        self.assertEqual(validate_project(project)['schemaVersion'], '1.4')
        for version in ('1.0','1.1','1.2','1.3'):
            old = {k: copy.deepcopy(project[k]) for k in ('schemaVersion','name','zones','nodes','links')}
            old['schemaVersion'] = version
            self.assertEqual(validate_project(old)['schemaVersion'], version)

    def test_real_disk_save_reopen_and_no_plan_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory))
            initial = store.save('existing', {'schemaVersion':'1.3','name':'Old',
                'zones':[],'nodes':[],'links':[]}, None)
            path = Path(directory) / 'existing.yadilab'
            original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            req = selected_request()
            project = build_plan(req)['plan']['proposedProject']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original_hash)
            saved = store.save('imported', project, None)
            store = ProjectStore(Path(directory))  # fresh storage instance, same real bytes
            opened = store.read('imported')
            self.assertEqual(opened['project'], project)
            self.assertEqual(opened['sha256'], saved['sha256'])
            edited = copy.deepcopy(opened['project'])
            edited['nodes'][0]['label'] = 'After save'
            store.save('imported', edited, saved['sha256'])
            self.assertEqual(store.read('imported')['project']['importEvidence'],
                             project['importEvidence'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), original_hash)

    def test_schema_14_http_save_open_after_server_process_restart(self):
        project = build_plan(selected_request())['plan']['proposedProject']
        with tempfile.TemporaryDirectory() as directory:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            command = [sys.executable, '-m', 'network_core', '--port', str(port),
                       '--data-dir', directory, '--no-browser']
            root = Path(__file__).resolve().parent.parent

            def launch():
                process = subprocess.Popen(command, cwd=root, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)
                for _ in range(100):
                    if process.poll() is not None:
                        self.fail('local server process exited before HTTP was ready')
                    try:
                        with urlopen(f'http://127.0.0.1:{port}/api/health', timeout=.2):
                            return process
                    except OSError:
                        time.sleep(.05)
                process.terminate()
                self.fail('local server process did not start')

            process = launch()
            try:
                payload = json.dumps({'filename':'imported','project':project,
                                      'expectedSha256':None}).encode()
                with urlopen(Request(f'http://127.0.0.1:{port}/api/save', data=payload,
                                     headers={'Content-Type':'application/json'}), timeout=10) as response:
                    self.assertEqual(response.status, 200)
                    saved = json.load(response)
                file_path = Path(directory) / 'imported.yadilab'
                disk_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
                self.assertEqual(saved['sha256'], disk_sha)
            finally:
                process.terminate()
                process.wait(timeout=8)
            process = launch()
            try:
                with urlopen(f'http://127.0.0.1:{port}/api/projects/imported', timeout=10) as response:
                    opened = json.load(response)
                self.assertEqual(opened['sha256'], disk_sha)
                self.assertEqual(opened['project'], project)
                self.assertEqual(opened['project']['schemaVersion'], '1.4')
            finally:
                process.terminate()
                process.wait(timeout=8)

    def test_http_candidate_and_unknown_unit(self):
        with tempfile.TemporaryDirectory() as directory:
            server = LabHTTPServer(('127.0.0.1', 0), ProjectStore(Path(directory)))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                conflict = request(b'ID,Label,Kind\nSW-01,Core,switch\nSW-01,Other,switch\n')
                conflict['mappingViews'][0]['selectedRows'] = [2, 3]
                conflict['selectedUnitIds'] = [build_plan(conflict)['plan']['units'][0]['unitId']]
                for req, expected in ((request(), 200), (selected_request(), 200),
                                      (conflict, 200),
                                      ({**request(), 'selectedUnitIds':['u-' + '0'*32]}, 422)):
                    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
                    connection.request('POST', '/api/import/build-candidate',
                        body=json.dumps(req).encode(), headers={'Content-Type':'application/json',
                        'Host':f'127.0.0.1:{server.server_port}'})
                    reply = connection.getresponse()
                    body = json.loads(reply.read())
                    connection.close()
                    self.assertEqual(reply.status, expected)
                    if expected == 200:
                        self.assertEqual(set(body), {'plan'})
                        if req is conflict:
                            self.assertFalse(body['plan']['canApply'])
                            self.assertIsNone(body['plan']['proposedProject'])
                    else:
                        self.assertEqual(body['error'], 'INVALID_PROJECT')
                candidate = build_plan(selected_request())['plan']['proposedProject']
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
                connection.request('POST', '/api/export/spreadsheet',
                    body=json.dumps({'project':candidate,'format':'xlsx'}).encode(),
                    headers={'Content-Type':'application/json',
                             'Host':f'127.0.0.1:{server.server_port}'})
                reply = connection.getresponse()
                error = json.loads(reply.read())
                connection.close()
                self.assertEqual(reply.status, 422)
                self.assertIn('historical evidence', error['message'])
                self.assertEqual(list(Path(directory).iterdir()), [])
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
