"""Read-only source pagination against real CSV, OOXML and ODF bytes."""
import base64
import hashlib
import io
import json
import http.client
import tempfile
import threading
import unittest
from pathlib import Path

from network_core.import_inspection import inspect_page, inspect_source
from network_core.model import ProjectValidationError, blank_project
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from xlsx_fixture import workbook_parts, zip_parts
from ods_fixture import ods_parts, zip_parts as ods_zip


def request(filename, raw, table='sheet-1', row=1):
    value = {'filename': filename, 'contentBase64': base64.b64encode(raw).decode(),
             'tableId': table, 'fromRow': row}
    if filename.endswith('.csv'):
        value['csvDelimiter'] = ','
    return value


class PageTests(unittest.TestCase):
    def test_csv_26_100_last_and_quoted_record(self):
        raw = ('"first\nline"\n' + ''.join(f'{n}\n' for n in range(2, 5002))).encode()
        first = inspect_page(request('data.csv', raw))
        self.assertEqual((len(first['rows']), first['rows'][-1]['row'], first['nextRow']), (25, 25, 26))
        self.assertEqual(first['rows'][0]['cells'][0]['value'], 'first\nline')
        self.assertEqual(first['source']['sha256'], hashlib.sha256(raw).hexdigest())
        for index, wanted in [(26, 26), (100, 100), (5001, 5001)]:
            with self.subTest(index=index):
                result = inspect_page(request('data.csv', raw, row=index))
                self.assertEqual(result['rows'][0]['row'], wanted)
        self.assertEqual(inspect_page(request('data.csv', raw, row=5001))['nextRow'], None)
        self.assertNotIn('nextRow', inspect_source({k: v for k, v in request('data.csv', raw).items()
                                                     if k not in ('tableId', 'fromRow')})['tables'][0])

    def test_xlsx_sparse_26_and_100(self):
        parts = workbook_parts({'Sparse': 'ID\n001\n002\n'})
        part = 'xl/worksheets/sheet1.xml'
        parts[part] = parts[part].replace(b'<row r="2">', b'<row r="26">').replace(b'r="A2"', b'r="A26"')
        parts[part] = parts[part].replace(b'<row r="3">', b'<row r="100">').replace(b'r="A3"', b'r="A100"')
        raw = zip_parts(parts)
        result = inspect_page(request('sparse.xlsx', raw, row=25))
        self.assertEqual([r['row'] for r in result['rows']], [26, 100])
        self.assertEqual(result['rows'][1]['cells'][0]['address'], 'A100')
        self.assertEqual(inspect_page(request('sparse.xlsx', raw, row=27))['rows'][0]['row'], 100)

    def test_ods_sparse_repeat_and_last(self):
        parts = ods_parts({'Sparse': 'ID\n001\n'})
        content = parts['content.xml'].replace(b'1024', b'1')
        content = content.replace(b'</table:table-row><table:table-row>',
                                  b'</table:table-row><table:table-row table:number-rows-repeated="98"><table:table-cell/></table:table-row><table:table-row>', 1)
        parts['content.xml'] = content
        raw = ods_zip(parts)
        result = inspect_page(request('sparse.ods', raw, row=26))
        self.assertEqual([r['row'] for r in result['rows']], [100])
        self.assertEqual(result['rows'][0]['cells'][0]['address'], 'A100')
        self.assertIsNone(result['nextRow'])

    def test_repeated_ods_pages_without_expanding_all_rows(self):
        parts = ods_parts({'Repeat': 'ID\n'})
        content = parts['content.xml'].replace(b'1024', b'1')
        content = content.replace(b'<table:table-row>', b'<table:table-row table:number-rows-repeated="5001">', 1)
        parts['content.xml'] = content
        raw = ods_zip(parts)
        result = inspect_page(request('repeat.ods', raw, row=5000))
        self.assertEqual([r['row'] for r in result['rows']], [5000, 5001])
        self.assertEqual(result['rows'][1]['cells'][0]['address'], 'A5001')

    def test_invalid_request_and_source_rejected(self):
        raw = b'ID\n001\n'
        for change in ({'tableId': 'sheet-2'}, {'fromRow': 0}, {'fromRow': True},
                       {'fromRow': 5002}, {'extra': 'x'}):
            with self.subTest(change=change), self.assertRaises(ProjectValidationError):
                inspect_page({**request('data.csv', raw), **change})
        with self.assertRaises(ProjectValidationError):
            inspect_page(request('data.csv', b'ID\n\xff', row=2))


class PageHTTPTests(unittest.TestCase):
    def test_real_http_no_project_write_and_422(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ProjectStore(Path(directory))
            store.save('proof', blank_project(), None)
            saved = (Path(directory) / 'proof.yadilab').read_bytes()
            server = LabHTTPServer(('127.0.0.1', 0), store)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                def post(value):
                    body = json.dumps(value).encode()
                    con = http.client.HTTPConnection('127.0.0.1', server.server_port)
                    con.request('POST', '/api/import/inspect-page', body=body,
                                headers={'Host': f'127.0.0.1:{server.server_port}',
                                         'Content-Type': 'application/json'})
                    response = con.getresponse()
                    result = response.status, json.loads(response.read())
                    con.close()
                    return result
                status, reply = post(request('data.csv', b'ID\n001\n', row=2))
                self.assertEqual(status, 200)
                self.assertEqual(reply['rows'][0]['cells'][0]['value'], '001')
                self.assertEqual((Path(directory) / 'proof.yadilab').read_bytes(), saved)
                status, reply = post(request('data.csv', b'ID\n001\n', table='sheet-2'))
                self.assertEqual(status, 422)
                self.assertEqual(reply['error'], 'INVALID_PROJECT')
                self.assertEqual((Path(directory) / 'proof.yadilab').read_bytes(), saved)
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=4)


if __name__ == '__main__':
    unittest.main()
