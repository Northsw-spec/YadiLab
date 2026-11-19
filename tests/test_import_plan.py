"""Independent assertions for read-only, explicit import discovery."""
import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from network_core.model import ProjectValidationError, blank_project
from network_core.storage import ProjectStore
from network_core.import_plan import build_plan, canonical_json, internal_id
from xlsx_fixture import workbook_parts, zip_parts
from ods_fixture import ods_parts, zip_parts as ods_zip


def source(raw, filename='inventory.csv', source_id='src-1'):
    result = {'sourceId': source_id, 'filename': filename,
              'contentBase64': base64.b64encode(raw).decode('ascii')}
    if filename.endswith('.csv'):
        result['csvDelimiter'] = ','
    return result


def view(columns, rows=(2,), *, view_id='view-1', header=1, headers=('ID', 'Label', 'Kind'), role='device_inventory'):
    return {'viewId': view_id, 'sourceId': 'src-1', 'tableId': 'sheet-1',
            'role': role, 'headerRow': header, 'selectedRows': list(rows),
            'columns': columns, 'valueMaps': {}, 'constants': {},
            'expectedHeaders': list(headers) if header is not None else [], 'label': 'Manuell tolkning'}


def request(raw=b'ID,Label,Kind\nSW-01,Core,switch\n', columns=None):
    return {'contractVersion': '1', 'projectName': 'Dokumenterat nät',
            'sources': [source(raw)],
            'mappingViews': [view(columns or {'node.id':['A'], 'node.label':['B'], 'node.kind':['C']})],
            'transformations': [], 'rowValues': [], 'excludedUses': [], 'selectedUnitIds': []}


class ImportPlanTests(unittest.TestCase):
    def test_canonical_bytes_and_known_ids(self):
        self.assertEqual(canonical_json(['node', 'SW-01']), b'["node","SW-01"]')
        self.assertEqual(internal_id('u-', ['node', 'SW-01']), 'u-0b0bbd73049222b0ae6089e767301fb8')
        self.assertEqual(internal_id('u-', ['port', '["SW-01","Gi1/0/1"]']),
                         'u-cd5877fb95e157afef963461702f49ec')
        self.assertEqual(internal_id('cl-', ['view-1','src-1','sheet-1',2,'node','SW-01']),
                         'cl-8491ea9628e63a4640a29b50983002c2')
        self.assertEqual(internal_id('c-', ['u-0b0bbd73049222b0ae6089e767301fb8',
                                            'create', '__object__']),
                         'c-b8d5c4d8b632f6649c65c06f220a54bc')
        self.assertEqual(internal_id('d-', ['view-1',2,'node.id','text','SW-01']),
                         'd-da521f326b75fe021f54eab8f4769505')
        self.assertEqual(canonical_json({'b': 1, 'a': 'Ä'}), '{"a":"Ä","b":1}'.encode())
        self.assertEqual(canonical_json({'x': 1.5}), b'{"x":1.5}')
        with self.assertRaises(ProjectValidationError):
            canonical_json({'metadata': float('nan')})
        req = request(); req['projectName'] = 1.5
        with self.assertRaises(ProjectValidationError):
            build_plan(req)

    def test_explicit_csv_plan_and_no_project(self):
        plan = build_plan(request())['plan']
        self.assertEqual(set(plan), {'planVersion','fingerprint','sourceManifest','mappingViews',
            'transformations','rowValues','excludedUses','selectedUnitIds','claims','units',
            'recordReviews','diagnostics','report','proposedProject','canApply'})
        self.assertIsNone(plan['proposedProject'])
        self.assertIs(plan['canApply'], False)
        self.assertEqual(plan['claims'][0]['targetKey'], 'SW-01')
        self.assertEqual(plan['claims'][0]['fields'], {'node.id':'SW-01','node.label':'Core','node.kind':'switch'})
        self.assertEqual(plan['units'][0]['unitId'], 'u-0b0bbd73049222b0ae6089e767301fb8')
        self.assertEqual(plan['units'][0]['status'], 'ACTIONABLE')
        self.assertEqual(plan['recordReviews'][1]['unmappedAddresses'], [])
        self.assertEqual(plan['recordReviews'][0]['unmappedAddresses'], ['A1','B1','C1'])
        self.assertEqual(plan['sourceManifest'][0]['sha256'], hashlib.sha256(b'ID,Label,Kind\nSW-01,Core,switch\n').hexdigest())
        self.assertEqual(plan['fingerprint'],
                         'badacda07b20f474d1e1c39ab3ac097e50d02af8dc28d71e1a02cbfe1ec491f2')

    def test_duplicate_and_conflict_keep_origins(self):
        raw = b'ID,Label,Kind\nSW-01,Core,switch\nSW-01,Core,switch\n'
        req = request(raw)
        req['mappingViews'][0]['selectedRows'] = [2,3]
        plan = build_plan(req)['plan']
        self.assertEqual(len(plan['units']), 1)
        self.assertEqual(len(plan['units'][0]['sourceUses']), 2)
        self.assertEqual([r['viewUses'][0]['status'] for r in plan['recordReviews'][1:]], ['ACTIONABLE','NO_OP'])
        req['sources'] = [source(raw.replace(b'SW-01,Core,switch\nSW-01,Core', b'SW-01,Core,switch\nSW-01,Edge'))]
        plan = build_plan(req)['plan']
        self.assertEqual(plan['units'][0]['status'], 'BLOCKED')
        refs = [ref for d in plan['diagnostics'] if d['code'] == 'FIELD_CONFLICT' for ref in d['sourceRefs']]
        self.assertEqual({r['address'] for r in refs}, {'B2','B3'})

    def test_two_views_same_row_and_unmapped_cell(self):
        raw = b'ID,Label,Kind,Other ID,Note\nSW-01,Core,switch,R-02,ignored\n'
        req = request(raw)
        req['mappingViews'][0]['expectedHeaders'] = ['ID','Label','Kind','Other ID','Note']
        second = view({'node.id':['D'],'node.label':['B'],'node.kind':['C']}, view_id='view-2',
                      headers=('ID','Label','Kind','Other ID','Note'))
        req['mappingViews'].append(second)
        plan = build_plan(req)['plan']
        self.assertEqual(len(plan['claims']), 2)
        self.assertEqual(len(plan['units']), 2)
        self.assertEqual(len(plan['recordReviews']), 2)
        self.assertEqual(len(plan['recordReviews'][1]['viewUses']), 2)
        self.assertEqual(plan['recordReviews'][1]['unmappedAddresses'], ['E2'])
        self.assertEqual(plan['report']['unmappedCells'], 6)

    def test_missing_id_numeric_id_unknown_kind_and_exclusion(self):
        req = request(b'ID,Label,Kind\n,Core,switch\n')
        plan = build_plan(req)['plan']
        self.assertIsNone(plan['claims'][0]['targetKey'])
        self.assertEqual(plan['units'], [])
        self.assertEqual(plan['recordReviews'][1]['viewUses'][0]['status'], 'BLOCKED')
        parts = workbook_parts({'Inventory': 'ID,Label,Kind\n1,Core,switch\n'})
        parts['xl/worksheets/sheet1.xml'] = parts['xl/worksheets/sheet1.xml'].replace(
            b'<c r="A2" t="inlineStr"><is><t>1</t></is></c>', b'<c r="A2" t="n"><v>1</v></c>')
        req = request()
        req['sources'] = [source(zip_parts(parts), 'data.xlsx')]
        plan = build_plan(req)['plan']
        self.assertIsNone(plan['claims'][0]['targetKey'])
        self.assertEqual(plan['recordReviews'][1]['viewUses'][0]['status'], 'BLOCKED')
        req = request(b'ID,Label,Kind\nSW-01,Core,unknown\n')
        plan = build_plan(req)['plan']
        self.assertEqual(plan['units'][0]['status'], 'INVALID')
        req = request()
        req['excludedUses'] = [{'viewId':'view-1','row':2,'reason':'Ej aktuell'}]
        plan = build_plan(req)['plan']
        self.assertEqual(plan['units'], [])
        self.assertEqual(plan['recordReviews'][1]['viewUses'][0]['status'], 'EXCLUDED')

    def test_ods_and_different_explicit_column_order(self):
        req = request(b'Kind,ID,Label\nswitch,SW-01,Core\n',
                      {'node.id':['B'],'node.label':['C'],'node.kind':['A']})
        req['mappingViews'][0]['expectedHeaders'] = ['Kind','ID','Label']
        csv_plan = build_plan(req)['plan']
        parts = ods_parts({'Inventory': 'Kind,ID,Label\nswitch,SW-01,Core\n'})
        parts['content.xml'] = parts['content.xml'].replace(b'1024', b'3')
        req['sources'] = [source(ods_zip(parts), 'data.ods')]
        ods_plan = build_plan(req)['plan']
        self.assertEqual(csv_plan['claims'][0]['fields'], ods_plan['claims'][0]['fields'])
        self.assertEqual(csv_plan['units'][0]['targetKey'], ods_plan['units'][0]['targetKey'])

    def test_selected_row_after_preview_limit_is_real(self):
        raw = b'ID,Label,Kind\n' + b''.join(
            f'node-{n},Node {n},host\n'.encode() for n in range(2, 28))
        req = request(raw)
        req['mappingViews'][0]['selectedRows'] = [26]
        plan = build_plan(req)['plan']
        self.assertEqual(plan['claims'][0]['sourceRef']['row'], 26)
        self.assertEqual(plan['claims'][0]['targetKey'], 'node-26')
        self.assertEqual(plan['recordReviews'][25]['row'], 26)
        self.assertEqual(len(plan['recordReviews']), 27)
        self.assertEqual(len(plan['units']), 1)

    def test_documentation_only_and_unmapped_value_remain_visible(self):
        req = request(b'ID,Label,Kind,IP\nSW-01,Core,managed switch,192.0.2.1\n')
        req['mappingViews'][0]['expectedHeaders'] = ['ID','Label','Kind','IP']
        req['mappingViews'][0]['valueMaps'] = {'node.kind': {'switch': 'switch'}}
        plan = build_plan(req)['plan']
        self.assertEqual(plan['units'][0]['status'], 'BLOCKED')
        self.assertIn('UNMAPPED_VALUE', [d['code'] for d in plan['diagnostics']])
        self.assertEqual(plan['recordReviews'][1]['unmappedAddresses'], ['D2'])
        req['mappingViews'] = [view({}, role='documentation_only', headers=('ID','Label','Kind','IP'))]
        plan = build_plan(req)['plan']
        self.assertEqual(plan['claims'], [])
        self.assertEqual(plan['units'], [])
        self.assertEqual(plan['recordReviews'][1]['viewUses'][0]['status'], 'DOCUMENTATION_ONLY')
        self.assertEqual(plan['recordReviews'][1]['unmappedAddresses'], ['A2','B2','C2','D2'])

    def test_fingerprint_changes_only_with_decisions_and_bytes(self):
        req = request()
        baseline = build_plan(req)['plan']['fingerprint']
        reordered = {k:req[k] for k in reversed(list(req))}
        reordered['mappingViews'] = [{k: v[k] for k in reversed(list(v))}
                                     for v in req['mappingViews']]
        self.assertEqual(build_plan(reordered)['plan']['fingerprint'], baseline)
        one_column = request(b'ID\nX\n')
        one_column['mappingViews'] = []
        comma_hash = build_plan(one_column)['plan']['fingerprint']
        one_column['sources'][0]['csvDelimiter'] = ';'
        self.assertNotEqual(build_plan(one_column)['plan']['fingerprint'], comma_hash)
        for modified in [lambda p: p['sources'][0].update(contentBase64=source(b'ID,Label,Kind\nSW-01,Core,host\n')['contentBase64']),
                         lambda p: p.update(projectName='Annat'),
                         lambda p: p['mappingViews'][0].update(label='Annan vy'),
                         lambda p: p['mappingViews'][0].update(selectedRows=[]),
                         lambda p: p['excludedUses'].append({'viewId':'view-1','row':2,'reason':'Nej'}),
                         lambda p: p['rowValues'].append({'viewId':'view-1','row':2,'targetField':'node.label','valueType':'text','value':'Core'})]:
            candidate = copy.deepcopy(req)
            modified(candidate)
            self.assertNotEqual(build_plan(candidate)['plan']['fingerprint'], baseline)
        chosen = copy.deepcopy(req)
        chosen['selectedUnitIds'] = ['u-0b0bbd73049222b0ae6089e767301fb8']
        plan = build_plan(chosen)['plan']
        self.assertNotEqual(plan['fingerprint'], baseline)
        self.assertIsNone(plan['proposedProject'])
        self.assertFalse(plan['canApply'])
        self.assertIn('CANDIDATE_NOT_IMPLEMENTED', [d['code'] for d in plan['diagnostics']])

    def test_explicit_value_maps_row_decision_and_conflict(self):
        req = request(b'ID,Label,Kind\n,Core,managed switch\n')
        req['mappingViews'][0]['valueMaps'] = {'node.kind': {'managed switch': 'switch'}}
        req['rowValues'] = [{'viewId':'view-1','row':2,'targetField':'node.id',
                             'valueType':'text','value':'SW-01'}]
        plan = build_plan(req)['plan']
        claim = plan['claims'][0]
        self.assertEqual(claim['fields']['node.kind'], 'switch')
        self.assertEqual(claim['fields']['node.id'], 'SW-01')
        self.assertEqual([o['kind'] for o in claim['origins']['node.id']], ['user_decision'])
        self.assertEqual({o['kind'] for o in claim['origins']['node.kind']},
                         {'source_cell', 'user_decision'})
        self.assertEqual(plan['units'][0]['status'], 'ACTIONABLE')
        req['rowValues'][0]['targetField'] = 'node.label'
        req['rowValues'][0]['value'] = 'Different'
        plan = build_plan(req)['plan']
        self.assertEqual(plan['recordReviews'][1]['viewUses'][0]['status'], 'BLOCKED')
        self.assertIn('FIELD_CONFLICT', [d['code'] for d in plan['diagnostics']])
        self.assertEqual({o['kind'] for o in plan['claims'][0]['origins']['node.label']},
                         {'source_cell', 'user_decision'})

    def test_resource_limits_and_malformed_types(self):
        req = request()
        req['sources'] = [source(b'ID\nX\n', source_id=f'src-{i}') for i in range(1, 10)]
        with self.assertRaises(ProjectValidationError):
            build_plan(req)
        req = request()
        req['mappingViews'] = [dict(req['mappingViews'][0], viewId=f'view-{i}') for i in range(1, 66)]
        with self.assertRaises(ProjectValidationError):
            build_plan(req)
        req = request(b'ID\n' + b'X\n' * 5000, {'node.id':['A']})
        req['mappingViews'][0]['expectedHeaders'] = ['ID']
        req['mappingViews'][0]['selectedRows'] = list(range(2, 5002))
        req['mappingViews'] = [dict(req['mappingViews'][0], viewId=f'view-{i}')
                               for i in range(1, 6)]
        with self.assertRaisesRegex(ProjectValidationError, '20000 selected row uses'):
            build_plan(req)
        req = request()
        oversized = (b'X' * 30000 + b'\n') * 70
        req['sources'] = [source(oversized, source_id='src-1'),
                          source(oversized, source_id='src-2')]
        with self.assertRaisesRegex(ProjectValidationError, '4 MiB'):
            build_plan(req)
        req = request(b'ID,Label,Kind\n' + b'SW-01,Core,switch\n' * 129)
        req['mappingViews'][0]['selectedRows'] = list(range(2, 131))
        with self.assertRaisesRegex(ProjectValidationError, '128 origins'):
            build_plan(req)
        req = request()
        req['mappingViews'] = []
        req['sources'] = [source(b'ID\n' + b'X\n' * 4000, source_id=f'src-{i}')
                          for i in range(1, 4)]
        with self.assertRaisesRegex(ProjectValidationError, 'combined row or cell budget'):
            build_plan(req)
        req['sources'] = [source((b','.join([b'x'] * 250) + b'\n') * 100,
                                 source_id=f'src-{i}') for i in range(1, 6)]
        with self.assertRaisesRegex(ProjectValidationError, 'combined row or cell budget'):
            build_plan(req)

    def test_plan_response_over_8_mib_is_rejected_not_truncated(self):
        raw = b'ID,Label,Kind\n' + b''.join(
            f'N{n},Node {n},host\n'.encode() for n in range(2, 5002))
        req = request(raw)
        req['mappingViews'][0]['selectedRows'] = list(range(2, 5002))
        req['mappingViews'] = [dict(req['mappingViews'][0], viewId=f'view-{i}')
                               for i in range(1, 5)]
        with self.assertRaisesRegex(ProjectValidationError, 'PLAN_TOO_LARGE'):
            build_plan(req)
        for edit in [lambda r: r['mappingViews'][0].update(role=[]),
                     lambda r: r['mappingViews'][0].update(sourceId=[]),
                     lambda r: r['mappingViews'][0]['columns'].update({'node.id': [['A']]}),
                     lambda r: r['rowValues'].append({'viewId':'view-1','row':[],
                         'targetField':'node.id','valueType':'text','value':'X'}),
                     lambda r: r['selectedUnitIds'].append(1)]:
            req = request()
            edit(req)
            with self.subTest(edit=edit), self.assertRaises(ProjectValidationError):
                build_plan(req)

    def test_invalid_requests_fail_closed(self):
        bad = []
        req = request(); req['mappingViews'][0]['expectedHeaders'] = ['wrong']; bad.append(req)
        req = request(); req['mappingViews'][0]['selectedRows'] = [100]; bad.append(req)
        req = request(); req['mappingViews'][0]['tableId'] = 'sheet-2'; bad.append(req)
        req = request(); req['mappingViews'][0]['columns']['node.id'] = ['Z']; bad.append(req)
        req = request(); req['mappingViews'][0]['viewId'] = 'view-2'; bad.append(req)
        req = request(); req['extra'] = 1; bad.append(req)
        req = request(); req['transformations'] = [{'viewId':'view-1','targetField':'port.accessVlan','operation':'parse_vlan_integer','delimiter':None}]; bad.append(req)
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ProjectValidationError):
                build_plan(value)

    def test_saved_file_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory))
            store.save('proof', blank_project(), None)
            target = Path(directory) / 'proof.yadilab'
            before = target.read_bytes()
            build_plan(request())
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), hashlib.sha256(before).hexdigest())


if __name__ == '__main__':
    unittest.main()
