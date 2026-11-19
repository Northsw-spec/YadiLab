"""Source-faithful CSV inspection: real bytes, strict negative tests and HTTP isolation."""
import base64
import hashlib
import http.client
import json
import io
import zipfile
from xlsx_fixture import workbook_parts, zip_parts as xlsx_zip
from ods_fixture import ods_parts, zip_parts as ods_zip
import tempfile
import threading
import unittest
from pathlib import Path

from network_core.import_inspection import inspect_source
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore


def request(data: bytes, delimiter=",", name="inventory.csv"):
    return {"filename": name, "csvDelimiter": delimiter,
            "contentBase64": base64.b64encode(data).decode("ascii")}


class CsvInspectionTests(unittest.TestCase):
    def test_literal_cells_and_exact_source_sha(self):
        raw = "ID,Label\n001,Älg\n002,\"A, B\"\n".encode()
        result = inspect_source(request(raw))
        self.assertEqual(result["source"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["inspectionVersion"], "1")
        self.assertEqual(result["previewRowLimit"], 25)
        table = result["tables"][0]
        self.assertEqual((table["rowCount"], table["populatedRowCount"], table["columnCount"]),
                         (3, 3, 2))
        self.assertEqual(table["previewRows"][1]["cells"][0],
                         {"address": "A2", "type": "text", "value": "001"})
        self.assertEqual(table["previewRows"][2]["cells"][1]["value"], "A, B")

    def test_semicolon_and_crlf(self):
        table = inspect_source(request(b"a;b\r\n01;true\r\n", ";"))["tables"][0]
        self.assertEqual(table["previewRows"][1]["cells"][0]["value"], "01")
        self.assertEqual(table["previewRows"][1]["cells"][1]["value"], "true")

    def test_bom_preserved_in_hash_but_removed_from_first_cell(self):
        raw = b"\xef\xbb\xbfID,Note\r\n001,\"two\nlines\"\r\n"
        result = inspect_source(request(raw))
        self.assertEqual(result["source"]["sha256"], hashlib.sha256(raw).hexdigest())
        table = result["tables"][0]
        self.assertEqual(table["rowCount"], 2)
        self.assertEqual(table["previewRows"][0]["cells"][0]["value"], "ID")
        self.assertEqual(table["previewRows"][1]["cells"][1]["value"], "two\nlines")

    def test_one_column_is_valid_even_with_potentially_wrong_delimiter(self):
        table = inspect_source(request(b"a;b\nc;d\n", ","))["tables"][0]
        self.assertEqual((table["rowCount"], table["columnCount"]), (2, 1))

    def test_first_25_populated_rows_only(self):
        data = ("ID\n" + "".join(f"{i}\n" for i in range(1, 100))).encode()
        table = inspect_source(request(data))["tables"][0]
        self.assertEqual(table["rowCount"], 100)
        self.assertEqual(len(table["previewRows"]), 25)
        self.assertEqual(table["previewRows"][-1]["row"], 25)

    def test_blank_record_keeps_logical_coordinate(self):
        table = inspect_source(request(b'\nID,Name\n001,Client\n'))['tables'][0]
        self.assertEqual((table['rowCount'], table['populatedRowCount']), (3, 2))
        self.assertEqual(table['previewRows'][0]['cells'][0]['address'], 'A2')

    def test_column_address_after_z(self):
        csv_bytes = (",".join(str(i) for i in range(28)) + "\n").encode()
        row = inspect_source(request(csv_bytes))["tables"][0]["previewRows"][0]
        self.assertEqual(row["cells"][25]["address"], "Z1")
        self.assertEqual(row["cells"][26]["address"], "AA1")
        self.assertEqual(row["cells"][27]["address"], "AB1")

    def test_invalid_base64(self):
        with self.assertRaises(ProjectValidationError):
            inspect_source({"filename": "x.csv", "csvDelimiter": ",", "contentBase64": "@@"})

    def test_invalid_utf8_and_nul(self):
        for data in (b"a\xffb", b"a,\x00"):
            with self.subTest(data=data):
                with self.assertRaises(ProjectValidationError):
                    inspect_source(request(data))

    def test_malformed_quotes(self):
        with self.assertRaises(ProjectValidationError):
            inspect_source(request(b"a,b\n\"unterminated,b\n"))

    def test_inconsistent_column_count(self):
        with self.assertRaises(ProjectValidationError):
            inspect_source(request(b"a,b\n1\n"))

    def test_file_paths_and_extra_keys_denied(self):
        values = [dict(request(b"a\n"), filename="../x.csv"),
                  {**request(b"a\n"), "projectName": "not allowed"}]
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ProjectValidationError):
                    inspect_source(value)

    def test_logical_row_limit(self):
        with self.assertRaises(ProjectValidationError):
            inspect_source(request(b"v\n" * 5002))




def workbook_request(name, raw):
    return {"filename": name, "contentBase64": base64.b64encode(raw).decode("ascii")}


class WorkbookInspectionTests(unittest.TestCase):
    def test_xlsx_real_sparse_multiple_sheets_and_literal_types(self):
        parts = workbook_parts({"Älg inventering": "ID,x,enabled\n001,12.50,true\n", "Second": "Note\nHej\n"}, shared_strings=True)
        sheet = parts["xl/worksheets/sheet1.xml"].decode().replace('<row r="2">', '<row r="4">').replace('A2', 'A4').replace('B2', 'D4').replace('C2', 'E4')
        parts["xl/worksheets/sheet1.xml"] = sheet.encode()
        raw = xlsx_zip(parts)
        result = inspect_source(workbook_request('sparse.xlsx', raw))
        self.assertEqual(result['source']['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual([t['name'] for t in result['tables']], ['Älg inventering', 'Second'])
        first = result['tables'][0]
        self.assertEqual((first['rowCount'], first['populatedRowCount'], first['columnCount']), (4, 2, 5))
        self.assertEqual(first['previewRows'][1]['cells'], [
            {'address': 'A4', 'type': 'text', 'value': '001'},
            {'address': 'D4', 'type': 'number', 'value': '12.50'},
            {'address': 'E4', 'type': 'boolean', 'value': '1'}])

    def test_xlsx_more_than_24_parts_within_new_cap(self):
        raw = xlsx_zip(workbook_parts({f'Sheet {n}': 'ID\n001\n' for n in range(22)}))
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertGreater(len(z.namelist()), 24)
        self.assertEqual(len(inspect_source(workbook_request('many.xlsx', raw))['tables']), 22)

    def test_xlsx_rejects_hidden_formula_merge_external_macro_and_bad_coordinate(self):
        base = workbook_parts({'Data': 'ID\n001\n'})
        for label, path, old, new in [
            ('hidden', 'xl/workbook.xml', 'sheetId="1"', 'sheetId="1" state="hidden"'),
            ('formula', 'xl/worksheets/sheet1.xml', '<is><t>001</t></is>', '<f>1+1</f><is><t>001</t></is>'),
            ('merge', 'xl/worksheets/sheet1.xml', '</worksheet>', '<mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells></worksheet>'),
            ('coordinate', 'xl/worksheets/sheet1.xml', 'A2', 'A0'),
            ('external', 'xl/_rels/workbook.xml.rels', 'Target="worksheets/sheet1.xml"', 'TargetMode="External" Target="worksheets/sheet1.xml"'),
            ('macro', '[Content_Types].xml', 'sheet.main+xml', 'sheet.macroEnabled.main+xml'),
            ('wrong content type', '[Content_Types].xml', 'worksheet+xml', 'theme+xml'),
        ]:
            with self.subTest(label=label):
                parts = base.copy()
                parts[path] = parts[path].replace(old.encode(), new.encode())
                with self.assertRaises(ProjectValidationError):
                    inspect_source(workbook_request('bad.xlsx', xlsx_zip(parts)))

    def test_ods_real_literals_and_sparse_repetition(self):
        parts = ods_parts({'Särskilt blad': 'ID,x,enabled\n001,12.50,true\n'})
        content = parts['content.xml'].decode().replace('1024', '3')
        content = content.replace('<table:table-row>', '<table:table-row table:number-rows-repeated="3">', 1)
        parts['content.xml'] = content.encode()
        raw = ods_zip(parts)
        table = inspect_source(workbook_request('data.ods', raw))['tables'][0]
        self.assertEqual((table['rowCount'], table['populatedRowCount'], table['columnCount']), (4, 4, 3))
        self.assertEqual(table['previewRows'][3]['cells'][0], {'address': 'A4', 'type': 'text', 'value': '001'})
        self.assertEqual(table['previewRows'][3]['cells'][1], {'address': 'B4', 'type': 'number', 'value': '12.50'})
        self.assertEqual(table['previewRows'][3]['cells'][2], {'address': 'C4', 'type': 'boolean', 'value': 'true'})

    def test_ods_rejects_mime_hidden_formula_merge_and_huge_repeat(self):
        base = ods_parts({'Data': 'ID\n001\n'})
        for label, path, old, new in [
            ('mime', 'mimetype', 'application/vnd.oasis.opendocument.spreadsheet', 'application/vnd.oasis.opendocument.text'),
            ('hidden', 'content.xml', 'table:name="Data"', 'table:name="Data" table:visibility="collapse"'),
            ('formula', 'content.xml', 'office:value-type="string"', 'table:formula="of:=1+1" office:value-type="string"'),
            ('merge', 'content.xml', '<table:table-cell/>', '<table:covered-table-cell/>'),
            ('repeat', 'content.xml', 'number-columns-repeated="1024"', 'number-columns-repeated="1000000"'),
            ('manifest', 'META-INF/manifest.xml', 'media-type="text/xml"', 'media-type="text/plain"'),
        ]:
            with self.subTest(label=label):
                parts = base.copy()
                parts[path] = parts[path].replace(old.encode(), new.encode())
                with self.assertRaises(ProjectValidationError):
                    inspect_source(workbook_request('bad.ods', ods_zip(parts)))

    def test_high_column_and_second_row_header_are_not_reinterpreted(self):
        fields = [''] * 65
        fields[-1] = '001'
        table = inspect_source(request(('\n' + ','.join(fields) + '\n').encode()))['tables'][0]
        self.assertEqual((table['rowCount'], table['columnCount']), (2, 65))
        self.assertEqual(table['previewRows'][0]['cells'][0], {'address': 'BM2', 'type': 'text', 'value': '001'})

    def test_zip_part_and_expansion_limits(self):
        parts = workbook_parts({'Data': 'ID\n001\n'})
        for n in range(260):
            parts[f'extra/{n}.xml'] = b'x'
        with self.assertRaises(ProjectValidationError):
            inspect_source(workbook_request('too-many.xlsx', xlsx_zip(parts)))
        parts = workbook_parts({'Data': 'ID\n001\n'})
        parts['xl/worksheets/sheet1.xml'] += b'x' * (5 * 1024 * 1024 + 1)
        with self.assertRaises(ProjectValidationError):
            inspect_source(workbook_request('huge.xlsx', xlsx_zip(parts)))

    def test_duplicate_zip_entries_and_corrupt_zip(self):
        for name, raw in [('bad.xlsx', b'PKbroken'), ('bad.ods', b'PKbroken')]:
            with self.assertRaises(ProjectValidationError):
                inspect_source(workbook_request(name, raw))
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            z.writestr('x', '1')
            z.writestr('x', '2')
        with self.assertRaises(ProjectValidationError):
            inspect_source(workbook_request('duplicate.xlsx', stream.getvalue()))

class HTTPSourceInspectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name))
        self.server = LabHTTPServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.host = f"127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=4)
        self.tmp.cleanup()

    def post(self, payload, *, host=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        connection.putrequest("POST", "/api/import/inspect", skip_host=True)
        connection.putheader("Host", self.host if host is None else host)
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_real_http_preview_never_writes_or_changes_saved_project(self):
        before = self.store.list()
        status, reply = self.post(request(b"ID,Name\n001,Switch\n"))
        self.assertEqual(status, 200)
        self.assertEqual(reply["tables"][0]["previewRows"][1]["cells"][0]["value"], "001")
        self.assertNotIn("project", reply)
        self.assertEqual(self.store.list(), before)

    def test_real_http_workbooks_and_saved_bytes_unchanged(self):
        from network_core.model import blank_project
        saved = self.store.save('proof', blank_project(), None)
        target = Path(self.tmp.name) / 'proof.yadilab'
        before = target.read_bytes()
        xlsx_bytes = xlsx_zip(workbook_parts({'Data': 'ID\n001\n'}))
        ods_source = ods_parts({'Data': 'ID\n001\n'})
        ods_source['content.xml'] = ods_source['content.xml'].replace(b'1024', b'1')
        for name, raw in [('source.xlsx', xlsx_bytes), ('source.ods', ods_zip(ods_source))]:
            with self.subTest(name=name):
                status, reply = self.post(workbook_request(name, raw))
                self.assertEqual(status, 200)
                self.assertEqual(reply['source']['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(reply['tables'][0]['previewRows'][1]['cells'][0]['value'], '001')
                self.assertEqual(target.read_bytes(), before)
                self.assertEqual(hashlib.sha256(before).hexdigest(), saved['sha256'])
        status, reply = self.post(workbook_request('bad.xlsx', b'not a ZIP'))
        self.assertEqual(status, 422)
        self.assertEqual(target.read_bytes(), before)

    def test_real_http_422_bad_file_and_403_bad_authority(self):
        status, payload = self.post(request(b"a,b\n1\n"))
        self.assertEqual(status, 422)
        self.assertEqual(payload["error"], "INVALID_PROJECT")
        status, payload = self.post(request(b"a\n"), host="evil.example")
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
