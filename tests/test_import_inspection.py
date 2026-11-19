"""Source-faithful CSV inspection: real bytes, strict negative tests and HTTP isolation."""
import base64
import hashlib
import http.client
import json
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

    def test_non_csv_workbook_explicitly_unavailable_in_first_delivery(self):
        request_value = request(b"data", name="x.xlsx")
        del request_value["csvDelimiter"]
        with self.assertRaises(ProjectValidationError):
            inspect_source(request_value)


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

    def test_real_http_422_bad_file_and_403_bad_authority(self):
        status, payload = self.post(request(b"a,b\n1\n"))
        self.assertEqual(status, 422)
        self.assertEqual(payload["error"], "INVALID_PROJECT")
        status, payload = self.post(request(b"a\n"), host="evil.example")
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
