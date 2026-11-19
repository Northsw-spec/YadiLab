"""Historical status and byte-for-byte source replay, including real HTTP."""
import copy
import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from network_core.import_plan import build_plan
from network_core.import_verification import evidence_status, verify_sources
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from test_import_candidate import selected_request
from test_import_plan import request, source, view
from xlsx_fixture import workbook_parts, zip_parts
from ods_fixture import ods_parts, zip_parts as ods_zip


def candidate():
    req = selected_request()
    return req, build_plan(req)['plan']['proposedProject']


class ImportVerificationTests(unittest.TestCase):
    def test_mixed_delimiters_fingerprint_and_complete_replay(self):
        comma = b'ID,Label,Kind\nSW-01,Core,switch\n'
        semicolon = b'ID;Label;Kind\nH-01;Workstation;host\n'
        req = request(comma)
        second = source(semicolon, 'inventory.csv', 'src-2')
        second['csvDelimiter'] = ';'
        req['sources'].append(second)
        second_view = view({'node.id':['A'],'node.label':['B'],'node.kind':['C']}, view_id='view-2')
        second_view['sourceId'] = 'src-2'
        req['mappingViews'].append(second_view)
        discovery = build_plan(req)['plan']
        self.assertEqual({unit['targetKey'] for unit in discovery['units']}, {'SW-01','H-01'})
        req['selectedUnitIds'] = sorted(unit['unitId'] for unit in discovery['units'])
        project = build_plan(req)['plan']['proposedProject']
        self.assertEqual([item['csvDelimiter'] for item in project['importEvidence']['sources']], [',',';'])
        self.assertEqual(verify_sources({'project':project,'sources':req['sources']})['verifiedSourceIds'],
                         ['src-1','src-2'])
        wrong = copy.deepcopy(req['sources'])
        wrong[1]['csvDelimiter'] = ','
        with self.assertRaises(ProjectValidationError):
            verify_sources({'project':project,'sources':wrong})
        fingerprint_request = copy.deepcopy(req)
        fingerprint_request['mappingViews'] = []
        fingerprint_request['selectedUnitIds'] = []
        correct_hash = build_plan(fingerprint_request)['plan']['fingerprint']
        fingerprint_request['sources'][1]['csvDelimiter'] = ','
        self.assertNotEqual(build_plan(fingerprint_request)['plan']['fingerprint'], correct_hash)
        ods = ods_parts({'Inventory':'ID,Label,Kind\nX,Extra,host\n'})
        ods['content.xml'] = ods['content.xml'].replace(b'1024', b'3')
        for raw, filename in ((zip_parts(workbook_parts({'Inventory':'ID,Label,Kind\nX,Extra,host\n'})), 'extra.xlsx'),
                              (ods_zip(ods), 'extra.ods')):
            mixed = copy.deepcopy(fingerprint_request)
            mixed['sources'][1] = source(raw, filename, 'src-2')
            plan = build_plan(mixed)['plan']
            self.assertEqual([item['csvDelimiter'] for item in plan['sourceManifest']], [',',None])

    def test_independent_workbook_bytes_replay(self):
        raw_rows = 'ID,Label,Kind\nH-01,Host,host\n'
        workbook = zip_parts(workbook_parts({'Inventory':raw_rows}))
        ods = ods_parts({'Inventory':raw_rows})
        ods['content.xml'] = ods['content.xml'].replace(b'1024', b'3')
        for raw, filename in ((workbook, 'inventory.xlsx'),
                              (ods_zip(ods), 'inventory.ods')):
            with self.subTest(filename=filename):
                req = request()
                req['sources'] = [source(raw, filename)]
                req['selectedUnitIds'] = [build_plan(req)['plan']['units'][0]['unitId']]
                project = build_plan(req)['plan']['proposedProject']
                result = verify_sources({'project':project,'sources':req['sources']})
                self.assertEqual(result['sourceStatus'], 'SOURCE_VERIFIED')
                self.assertEqual(result['verifiedSourceIds'], ['src-1'])
                self.assertEqual(project['importEvidence']['sources'][0]['sha256'],
                                 hashlib.sha256(raw).hexdigest())

    def test_status_tracks_current_network_not_source_claims(self):
        _, project = candidate()
        original = copy.deepcopy(project)
        self.assertEqual(evidence_status({'project':project}), {
            'manifestStatus':'MANIFEST_VALIDATED','baselineStatus':'BASELINE_MATCH'})
        project['nodes'][0]['label'] = 'Edited'
        self.assertEqual(evidence_status({'project':project})['baselineStatus'],
                         'CHANGED_SINCE_IMPORT')
        project['nodes'][0]['label'] = original['nodes'][0]['label']
        self.assertEqual(evidence_status({'project':project})['baselineStatus'],
                         'BASELINE_MATCH')
        self.assertEqual(project, original)
        for bad in ({'project':{'schemaVersion':'1.4'}}, {'project':project,'extra':1},
                    {'project':{**project,'schemaVersion':'1.3'}},
                    {'project':{**project,'importEvidence':{}}}):
            with self.assertRaises(ProjectValidationError):
                evidence_status(bad)

    def test_full_replay_is_historical_and_read_only(self):
        req, project = candidate()
        before = copy.deepcopy(project)
        expected = {'manifestStatus':'MANIFEST_VALIDATED','baselineStatus':'BASELINE_MATCH',
                    'sourceStatus':'SOURCE_VERIFIED','replayStatus':'MATCH',
                    'verifiedSourceIds':['src-1'],'diagnostics':[]}
        self.assertEqual(verify_sources({'project':project,'sources':req['sources']}), expected)
        project['nodes'][0]['label'] = 'Changed after import'
        status = verify_sources({'project':project,'sources':req['sources']})
        self.assertEqual(status['sourceStatus'], 'SOURCE_VERIFIED')
        self.assertEqual(status['baselineStatus'], 'CHANGED_SINCE_IMPORT')
        self.assertEqual(project['importEvidence'], before['importEvidence'])

    def test_multiple_sources_require_exact_complete_originals(self):
        first = b'ID,Label,Kind\nA,One,host\n'
        second = b'ID,Label,Kind\nB,Two,switch\n'
        req = request(first)
        req['sources'].append(source(second, 'second.csv', 'src-2'))
        extra = view({'node.id':['A'],'node.label':['B'],'node.kind':['C']}, view_id='view-2')
        extra['sourceId'] = 'src-2'
        req['mappingViews'].append(extra)
        req['selectedUnitIds'] = sorted(u['unitId'] for u in build_plan(req)['plan']['units'])
        project = build_plan(req)['plan']['proposedProject']
        good = verify_sources({'project':project,'sources':req['sources']})
        self.assertEqual(good['verifiedSourceIds'], ['src-1','src-2'])
        self.assertEqual(good['sourceStatus'], 'SOURCE_VERIFIED')
        for sources in (req['sources'][:1], list(reversed(req['sources'])),
                        req['sources'] + [source(b'ID\nC\n','extra.csv','src-3')],
                        [req['sources'][0], {**req['sources'][1], 'filename':'wrong.csv'}],
                        [req['sources'][0], {**req['sources'][1], 'contentBase64':source(b'changed')['contentBase64']}],
                        [req['sources'][0], {**req['sources'][1], 'csvDelimiter':';'}]):
            with self.subTest(sources=sources), self.assertRaises(ProjectValidationError):
                verify_sources({'project':project,'sources':sources})

    def test_matching_source_hash_can_still_fail_replay(self):
        req, project = candidate()
        changed = copy.deepcopy(project)
        decision = {'viewId':'view-1','row':2,'targetField':'node.label',
                    'valueType':'text','value':'Core'}
        changed['importEvidence']['rowValues'] = [decision]
        fingerprint_input = {'contractVersion':'1','projectName':'Dokumenterat nät',
                             'validatorVersion':'1.4',
                             'sources':[{'sourceId':'src-1',
                                         'sha256':hashlib.sha256(b'ID,Label,Kind\nSW-01,Core,switch\n').hexdigest(),
                                         'csvDelimiter':','}],
                             'mappingViews':changed['importEvidence']['mappingViews'],
                             'transformations':[], 'rowValues':[decision],
                             'excludedUses':[], 'selectedUnitIds':req['selectedUnitIds']}
        changed['importEvidence']['planFingerprint'] = hashlib.sha256(json.dumps(
            fingerprint_input, ensure_ascii=False, sort_keys=True,
            separators=(',',':')).encode()).hexdigest()
        result = verify_sources({'project':changed,'sources':req['sources']})
        self.assertEqual(result['sourceStatus'], 'SOURCE_HASH_MATCH')
        self.assertEqual(result['replayStatus'], 'MISMATCH')
        self.assertEqual(result['verifiedSourceIds'], [])
        self.assertEqual(set(result['diagnostics'][0]),
                         {'code','sourceId','tableId','row','message'})
        damaged = copy.deepcopy(project)
        damaged['importEvidence']['acceptedChanges'][0]['changeIds'][0] = 'c-' + '0'*32
        with self.assertRaises(ProjectValidationError):
            verify_sources({'project':damaged,'sources':req['sources']})

    def test_http_contract_and_saved_bytes_unchanged(self):
        req, project = candidate()
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory))
            saved = store.save('proof', project, None)
            target = Path(directory) / 'proof.yadilab'
            raw_before = target.read_bytes()
            server = LabHTTPServer(('127.0.0.1',0), store)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                for path, payload, expected in (
                    ('/api/import/evidence-status', {'project':project}, 200),
                    ('/api/import/verify-sources', {'project':project,'sources':req['sources']}, 200),
                    ('/api/import/verify-sources', {'project':project,'sources':[]}, 422),
                    ('/api/import/evidence-status', {'project':{}}, 422)):
                    con = http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                    con.request('POST',path,body=json.dumps(payload).encode(),headers={
                        'Content-Type':'application/json',
                        'Host':f'127.0.0.1:{server.server_port}'})
                    response = con.getresponse()
                    body = json.loads(response.read())
                    con.close()
                    self.assertEqual(response.status,expected)
                    if expected == 422:
                        self.assertEqual(set(body), {'error','message'})
                    elif path.endswith('evidence-status'):
                        self.assertEqual(set(body),{'manifestStatus','baselineStatus'})
                    else:
                        self.assertEqual(set(body),{'manifestStatus','baselineStatus',
                             'sourceStatus','replayStatus','verifiedSourceIds','diagnostics'})
                self.assertEqual(target.read_bytes(),raw_before)
                self.assertEqual(store.read('proof')['sha256'],saved['sha256'])
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
