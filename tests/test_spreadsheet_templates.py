"""Real downloaded schema-1.3 templates and grounded cell diagnostics.

Fixtures are independently constructed; production templates are validated
against the real XLSX/ODS parser, routing model and actual loopback HTTP.
"""
from __future__ import annotations

import base64
import copy
import csv
import hashlib
import io
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from network_core.model import ProjectValidationError, validate_project
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from network_core.spreadsheet_templates import SHEET_ORDER, SAMPLE, template_bytes
from network_core.xlsx_import import import_xlsx_workbook
from network_core.ods_import import import_ods_workbook
from spreadsheet_v13_fixture import TABLES_13
from xlsx_fixture import workbook_parts, zip_parts as zip_xlsx
from ods_fixture import ods_parts, zip_parts as zip_ods, make_ods
from xlsx_fixture import make_workbook


def request(ext, data):
    return {"filename":"any."+ext,"projectName":"Template imported",
            "contentBase64":base64.b64encode(data).decode("ascii")}


def variants(tables):
    return (
        ("xlsx", make_workbook(tables, shared_strings=True), import_xlsx_workbook),
        ("ods", make_ods(tables), import_ods_workbook),
    )


def modified(sheet, before, after):
    tables=copy.deepcopy(TABLES_13)
    if before not in tables[sheet]:
        raise AssertionError("fixture anchor missing")
    tables[sheet]=tables[sheet].replace(before, after, 1)
    return tables


class TemplateUnitTests(unittest.TestCase):
    def test_both_really_zipped_formats_use_six_sheet_canonical_contract(self):
        projects=[]
        for ext, importer in (("xlsx",import_xlsx_workbook),("ods",import_ods_workbook)):
            with self.subTest(ext=ext):
                payload=template_bytes(ext)
                self.assertLess(len(payload),5*1024*1024)
                self.assertEqual(payload[:2],b"PK")
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    self.assertEqual(len(archive.namelist()),10 if ext=="xlsx" else 3)
                    self.assertIn("xl/workbook.xml" if ext=="xlsx" else "content.xml",
                                  archive.namelist())
                    if ext=="ods":
                        self.assertEqual(archive.namelist()[0],"mimetype")
                        self.assertEqual(archive.getinfo("mimetype").compress_type,
                                         zipfile.ZIP_STORED)
                project=importer(request(ext,payload))
                projects.append(project)
                self.assertEqual(project["schemaVersion"],"1.3")
                self.assertEqual(len(project["nodes"]),4)
                self.assertEqual(len(project["links"]),3)
                self.assertEqual([n["id"] for n in project["nodes"]],
                                 ["demo-client","demo-switch-a","demo-switch-b","demo-router"])
                self.assertEqual(project["nodes"][0]["ports"][0]["mac"],
                                 "02:00:00:00:00:0A")
                self.assertEqual(project["nodes"][1]["ports"][1]["vlan"],
                                 {"mode":"trunk","allowedVlans":[10,20]})
                self.assertEqual(project["nodes"][0]["staticRoutes"][0]["nextHop"],
                                 "192.0.2.1")
                self.assertEqual(validate_project(project),project)
        self.assertEqual(projects[0],projects[1])

    def test_templates_are_labeled_demos_not_external_network_facts(self):
        for row in SAMPLE["Devices"]:
            self.assertTrue(row[0].startswith("demo-"))
            self.assertIn("DEMO",row[1])
        for row in SAMPLE["Links"]:
            self.assertTrue(row[0].startswith("demo-"))
        self.assertIn("DEMO",SAMPLE["Zones"][0][1])
        self.assertEqual(tuple(SAMPLE),SHEET_ORDER)

    def test_reproducible_generation_and_rejected_other_suffix(self):
        self.assertEqual(template_bytes("xlsx"),template_bytes("xlsx"))
        self.assertEqual(template_bytes("ods"),template_bytes("ods"))
        with self.assertRaises(ValueError):
            template_bytes("csv")

    def test_template_zip_bytes_ignore_wall_clock_and_have_fixed_member_metadata(self):
        # Old writestr(name, ...) reads localtime and changes binary SHA
        # across the two-second ZIP timestamp boundary. Do not weaken the
        # browser's exact downloaded-file hash check; fix the writer.
        for ext in ("xlsx", "ods"):
            with self.subTest(extension=ext):
                with patch("zipfile.time.localtime",
                           side_effect=AssertionError("ZIP writer read the wall clock")):
                    first = template_bytes(ext)
                    second = template_bytes(ext)
                self.assertEqual(first, second)
                self.assertEqual(hashlib.sha256(first).hexdigest(),
                                 hashlib.sha256(second).hexdigest())
                with zipfile.ZipFile(io.BytesIO(first)) as archive:
                    for info in archive.infolist():
                        self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                        self.assertEqual(info.create_system, 3)
                        self.assertEqual(info.external_attr >> 16, 0o600)
                        if ext == "ods" and info.filename == "mimetype":
                            self.assertEqual(info.compress_type, zipfile.ZIP_STORED)

    def test_format_specific_parser_rejects_misidentified_payload(self):
        with self.assertRaises(ProjectValidationError):
            import_xlsx_workbook(request("xlsx",template_bytes("ods")))
        with self.assertRaises(ProjectValidationError):
            import_ods_workbook(request("ods",template_bytes("xlsx")))

    def test_wrong_mac_reports_actual_sheet_row_and_column(self):
        doc=modified("Interfaces","02:00:00:00:00:0A","01:00:00:00:00:0A")
        for ext,payload,importer in variants(doc):
            with self.subTest(ext=ext):
                with self.assertRaises(ProjectValidationError) as error:
                    importer(request(ext,payload))
                self.assertIn("Interfaces!F2 (mac)",str(error.exception))
                self.assertIn("endpoint MAC must be nonzero unicast",str(error.exception))

    def test_invalid_vlan_reports_access_vlan_cell(self):
        doc=modified("Interfaces","access,10,","access,0,")
        for ext,payload,importer in variants(doc):
            with self.subTest(ext=ext):
                with self.assertRaises(ProjectValidationError) as error:
                    importer(request(ext,payload))
                self.assertIn("Interfaces!H3 (accessVlan)",str(error.exception))

    def test_offlink_route_reports_exact_next_hop_cell(self):
        doc=modified("StaticRoutes","192.0.2.1,eth0","198.51.100.1,eth0")
        for ext,payload,importer in variants(doc):
            with self.subTest(ext=ext):
                with self.assertRaises(ProjectValidationError) as error:
                    importer(request(ext,payload))
                self.assertIn("StaticRoutes!D2 (nextHop)",str(error.exception))
                self.assertIn("not on the configured output interface",str(error.exception))

    def test_actual_reordered_column_not_canonical_column_number(self):
        doc=copy.deepcopy(TABLES_13)
        records=list(csv.reader(io.StringIO(doc["Interfaces"])))
        for record in records:
            record[4],record[5]=record[5],record[4]   # MAC F -> E
        out=io.StringIO(newline="")
        csv.writer(out,lineterminator="\n").writerows(records)
        doc["Interfaces"]=out.getvalue()
        doc["Interfaces"]=doc["Interfaces"].replace(
            "02:00:00:00:00:0A","01:00:00:00:00:0A",1)
        for ext,payload,importer in variants(doc):
            with self.subTest(ext=ext):
                with self.assertRaises(ProjectValidationError) as error:
                    importer(request(ext,payload))
                self.assertIn("Interfaces!E2 (mac)",str(error.exception))
                self.assertNotIn("Interfaces!F2 (mac)",str(error.exception))

    def test_duplicate_second_route_reports_second_input_record(self):
        doc=copy.deepcopy(TABLES_13)
        doc["StaticRoutes"] += "ha,to-network-b,198.51.100.0/24,192.0.2.1,eth0\n"
        for ext,payload,importer in variants(doc):
            with self.subTest(ext=ext):
                with self.assertRaises(ProjectValidationError) as error:
                    importer(request(ext,payload))
                self.assertIn("StaticRoutes!B4 (id)",str(error.exception))

    def test_version_marker_reports_specific_project_cell(self):
        doc=modified("Project","1.3","1.2")
        for ext,payload,importer in variants(doc):
            with self.subTest(ext=ext):
                with self.assertRaises(ProjectValidationError) as error:
                    importer(request(ext,payload))
                self.assertIn("Project!A2 (schemaVersion)",str(error.exception))

    def test_wrong_header_reports_sheet_header_location(self):
        doc=modified("Interfaces","allowedVlans","unknownColumn")
        for ext,payload,importer in variants(doc):
            with self.subTest(ext=ext):
                with self.assertRaises(ProjectValidationError) as error:
                    importer(request(ext,payload))
                self.assertIn("Interfaces!1 (header)",str(error.exception))

    def test_xlsx_bad_typed_value_reports_exact_cell(self):
        parts=workbook_parts(TABLES_13)
        # Named worksheet order is Project, Devices, Zones, Interfaces, Links, Routes.
        raw=parts["xl/worksheets/sheet4.xml"].decode("utf-8")
        old='<c r="F2" t="inlineStr"><is><t>02:00:00:00:00:0A</t></is></c>'
        self.assertIn(old,raw)
        parts["xl/worksheets/sheet4.xml"]=raw.replace(
            old,'<c r="F2" t="n"><v>123</v></c>',1).encode()
        with self.assertRaises(ProjectValidationError) as err:
            import_xlsx_workbook(request("xlsx",zip_xlsx(parts)))
        self.assertIn("Interfaces!F2",str(err.exception))

    def test_ods_bad_typed_value_reports_exact_cell(self):
        parts=ods_parts(TABLES_13)
        xml=parts["content.xml"].decode()
        old='<table:table-cell office:value-type="string"><text:p>02:00:00:00:00:0A</text:p></table:table-cell>'
        self.assertIn(old,xml)
        parts["content.xml"]=xml.replace(
            old,'<table:table-cell office:value-type="float" office:value="123"/>',1).encode()
        with self.assertRaises(ProjectValidationError) as err:
            import_ods_workbook(request("ods",zip_ods(parts)))
        self.assertIn("Interfaces!F2",str(err.exception))


class TemplateHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.server=LabHTTPServer(("127.0.0.1",0),ProjectStore(self.root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def test_http_download_real_bytes_then_reimport_no_autosave(self):
        for ext,importer in (("xlsx",import_xlsx_workbook),("ods",import_ods_workbook)):
            with self.subTest(ext=ext):
                with urlopen(self.url+"/api/templates/"+ext,timeout=10) as response:
                    self.assertEqual(response.status,200)
                    self.assertEqual(
                        response.headers["Content-Disposition"],
                        f'attachment; filename="network-schema13-demo.{ext}"')
                    self.assertIn("no-store",response.headers["Cache-Control"])
                    self.assertEqual(response.headers["X-Content-Type-Options"],"nosniff")
                    data=response.read()
                    self.assertEqual(int(response.headers["Content-Length"]),len(data))
                project=importer(request(ext,data))
                self.assertEqual(project["schemaVersion"],"1.3")
                self.assertEqual(project["nodes"][0]["id"],"demo-client")
                self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_http_binary_workbook_can_be_imported_via_post_then_saved(self):
        for ext in ("xlsx","ods"):
            with self.subTest(ext=ext):
                with urlopen(self.url+"/api/templates/"+ext,timeout=10) as response:
                    raw=response.read()
                payload=json.dumps(request(ext,raw)).encode()
                req=Request(self.url+"/api/import/"+ext,data=payload,
                            headers={"Content-Type":"application/json"})
                with urlopen(req,timeout=10) as response:
                    self.assertEqual(response.status,200)
                    result=json.loads(response.read())["project"]
                self.assertEqual(result["schemaVersion"],"1.3")
                previous = self.root / ("example-"+ext+".yadilab")
                self.assertFalse(previous.exists(), "import alone must not persist")
                saved=self.server.store.save("example-"+ext,result)
                saved_bytes=(self.root/("example-"+ext+".yadilab")).read_bytes()
                self.assertEqual(hashlib.sha256(saved_bytes).hexdigest(),saved["sha256"])
                self.assertEqual(self.server.store.read("example-"+ext)["project"],result)

    def test_unknown_template_url_cannot_access_other_files(self):
        for path in ("/api/templates/xls", "/api/templates/xlsx/extra", "/api/templates/unknown"):
            with self.subTest(path=path),self.assertRaises(HTTPError) as error:
                urlopen(self.url+path,timeout=10)
            self.assertEqual(error.exception.code,404)


if __name__=="__main__":
    unittest.main()
