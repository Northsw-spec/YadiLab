"""Real OOXML/XLSX import: exact identities or fail closed, no hidden Save."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.model import ProjectValidationError, topology_trace
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from network_core.xlsx_import import import_xlsx_workbook
from network_core.csv_import import import_csv_tables
from test_csv_import import source, DEV, PORTS, LINKS, ZONES
from xlsx_fixture import STANDARD_SHEETS, make_workbook, workbook_parts, zip_parts


def request(data: bytes, name: str="Excel canonical lab", filename="network.xlsx") -> dict:
    return {"projectName":name,"filename":filename,
            "contentBase64":base64.b64encode(data).decode("ascii")}


def modify(part: str, original: str, replacement: str) -> bytes:
    files=workbook_parts()
    raw=files[part].decode("utf-8")
    if raw.count(original) != 1:
        raise AssertionError(f"Fixture anchor absent or repeated: {part}: {original[:80]}")
    files[part]=raw.replace(original,replacement).encode("utf-8")
    return zip_parts(files)


class XlsxFunctionalTests(unittest.TestCase):
    def test_real_zip_inline_strings_numeric_positions_boolean_states(self):
        raw=make_workbook()
        self.assertEqual(raw[:2],b"PK")
        with zipfile.ZipFile(__import__("io").BytesIO(raw)) as z:
            self.assertIn("xl/workbook.xml",z.namelist())
            self.assertIn("xl/worksheets/sheet2.xml",z.namelist())
        p=import_xlsx_workbook(request(raw,"Excel lab"))
        self.assertEqual(p["schemaVersion"],"1.0")
        self.assertEqual(p["name"],"Excel lab")
        self.assertEqual([n["id"] for n in p["nodes"]],["pc-a","sw-a"])
        self.assertEqual(p["nodes"][0]["x"],80.0)
        self.assertEqual(p["nodes"][0]["ports"][0]["enabled"],True)
        self.assertEqual(p["nodes"][0]["ports"][0]["ipv4"],"192.0.2.5/24")
        self.assertEqual(p["links"][0]["id"],"cable-1")
        self.assertEqual(p["links"][0]["a"],{"node":"pc-a","port":"eth0"})
        self.assertEqual(p["links"][0]["b"],{"node":"sw-a","port":"gi1"})
        self.assertEqual(p["zones"][0]["id"],"office")
        self.assertEqual(topology_trace(p,"pc-a","sw-a")["status"],"PATH_PRESENT")
        # Independently constructed real XLSX matches the existing CSV import.
        self.assertEqual(p,import_csv_tables({
            **source(),"projectName":"Excel lab"
        }))

    def test_reordered_sheets_shared_strings_utf8_multiline_reordered_columns(self):
        sheets=copy.deepcopy(STANDARD_SHEETS)
        sheets["Devices"]=(
            'label,id,kind,zoneId,y,x\n'
            '"Klient, södra\nkontoret",pc-a,host,office,120,80\n'
            'Växel,sw-a,switch,office,120,320\n'
        )
        workbook=make_workbook(sheets,shared_strings=True,reorder=True)
        p=import_xlsx_workbook(request(workbook))
        self.assertEqual(p["nodes"][0]["label"],"Klient, södra\nkontoret")
        self.assertEqual(p["nodes"][1]["label"],"Växel")
        self.assertEqual([n["id"] for n in p["nodes"]],["pc-a","sw-a"])
        self.assertEqual(p["links"][0]["id"],"cable-1")

    def test_required_devices_only_no_inferred_ports_or_links(self):
        p=import_xlsx_workbook(request(make_workbook({"Devices":DEV.replace(",office",",")})))
        self.assertEqual(len(p["nodes"]),2)
        self.assertEqual(p["links"],[])
        self.assertTrue(all(not n["ports"] for n in p["nodes"]))

    def test_optional_empty_tables_are_valid(self):
        sheets={"Devices": DEV.replace(",office",","),
                "Interfaces":"nodeId,id,name,enabled,ipv4\n",
                "Links":"id,aNode,aPort,bNode,bPort,enabled\n"}
        p=import_xlsx_workbook(request(make_workbook(sheets)))
        self.assertEqual(p["links"],[])
        self.assertEqual(len(p["nodes"]),2)

    def test_invalid_cross_references_duplicate_identifiers_and_headers(self):
        tests=[
            {"Devices":DEV + "pc-a,Duplicate,host,8,10,office\n",
             "Interfaces":PORTS,"Links":LINKS,"Zones":ZONES},
            {"Devices":DEV,"Interfaces":PORTS.replace("sw-a,gi1","absent,gi1"),
             "Links":LINKS,"Zones":ZONES},
            {"Devices":DEV,"Interfaces":PORTS,"Links":LINKS.replace("sw-a,gi1","sw-a,missing"),
             "Zones":ZONES},
            {"Devices":DEV,"Interfaces":PORTS,"Links":LINKS.replace("cable-1,","cable-1,") +
             "cable-1,pc-a,eth0,sw-a,gi1,true\n","Zones":ZONES},
            {"Devices":DEV.replace("zoneId","unknown"),"Interfaces":PORTS,"Links":LINKS,"Zones":ZONES},
            {"Interfaces":PORTS,"Links":LINKS,"Zones":ZONES},
            {"Devices":DEV,"Unexpected":"id,label\nabc,def\n"},
        ]
        for sheet_set in tests:
            with self.subTest(sheets=str(sheet_set)[:80]),self.assertRaises(ProjectValidationError):
                import_xlsx_workbook(request(make_workbook(sheet_set)))

    def test_numeric_identifier_rejected_no_loss_of_leading_zeros(self):
        raw=modify("xl/worksheets/sheet1.xml",
                   '<c r="A2" t="inlineStr"><is><t>pc-a</t></is></c>',
                   '<c r="A2" t="n"><v>12</v></c>')
        with self.assertRaisesRegex(ProjectValidationError,"identifiers must be text"):
            import_xlsx_workbook(request(raw))

    def test_formula_and_cached_result_never_accepted_as_facts(self):
        for replace_with in (
            '<c r="D2"><f>1+1</f><v>2</v></c>',
            '<c r="D2" t="str"><v>80</v></c>',
            '<c r="D2" t="e"><v>#REF!</v></c>',
        ):
            with self.subTest(replace_with=replace_with):
                raw=modify("xl/worksheets/sheet1.xml",
                           '<c r="D2" t="n"><v>80</v></c>',replace_with)
                with self.assertRaises(ProjectValidationError):
                    import_xlsx_workbook(request(raw))

    def test_hidden_sheet_row_and_column_rejected(self):
        for data in (
            modify("xl/workbook.xml",'name="Devices" sheetId="1"',
                   'name="Devices" state="hidden" sheetId="1"'),
            modify("xl/worksheets/sheet1.xml",'<row r="2">',
                   '<row r="2" hidden="1">'),
            modify("xl/worksheets/sheet1.xml",'<sheetData>',
                   '<cols><col min="1" max="1" hidden="1"/></cols><sheetData>'),
        ):
            with self.subTest(marker=data[:30]),self.assertRaises(ProjectValidationError):
                import_xlsx_workbook(request(data))

    def test_blank_row_extra_column_and_duplicate_cell_rejected(self):
        for raw in (
            modify("xl/worksheets/sheet1.xml",'<row r="2">',
                   '<row r="99">'),
            modify("xl/worksheets/sheet1.xml",'<row r="2">',
                   '<row r="2"><c r="G2" t="inlineStr"><is><t>extra</t></is></c>'),
            modify("xl/worksheets/sheet1.xml",'<row r="2">',
                   '<row r="2"><c r="A2" t="inlineStr"><is><t>repeated</t></is></c>'),
            modify("xl/worksheets/sheet1.xml",'<row r="2">',
                   '<row r="2" hidden="true">'),
        ):
            with self.assertRaises(ProjectValidationError):
                import_xlsx_workbook(request(raw))

    def test_external_relationship_and_unsupported_workbook_object_rejected(self):
        for raw in (
            modify("xl/_rels/workbook.xml.rels",
                   'Target="worksheets/sheet1.xml"',
                   'Target="https://example.com" TargetMode="External"'),
            modify("xl/worksheets/sheet1.xml",'<sheetData>',
                   '<mergeCells><mergeCell ref="A1:B1"/></mergeCells><sheetData>'),
        ):
            with self.assertRaises(ProjectValidationError):
                import_xlsx_workbook(request(raw))
        parts=workbook_parts()
        parts["xl/externalLinks/externalLink1.xml"]=b"<externalLink/>"
        with self.assertRaisesRegex(ProjectValidationError,"unsupported workbook parts"):
            import_xlsx_workbook(request(zip_parts(parts)))

    def test_bad_shared_string_indices_and_unknown_types_fail_closed(self):
        shared=workbook_parts(shared_strings=True)
        part="xl/worksheets/sheet1.xml"
        old=shared[part].decode()
        self.assertIn('t="s"><v>0</v>',old)
        shared[part]=old.replace('t="s"><v>0</v>',
                                 't="s"><v>999999</v>',1).encode()
        with self.assertRaisesRegex(ProjectValidationError,"shared-string"):
            import_xlsx_workbook(request(zip_parts(shared)))
        shared=workbook_parts(shared_strings=True)
        shared.pop("xl/sharedStrings.xml")
        with self.assertRaises(ProjectValidationError):
            import_xlsx_workbook(request(zip_parts(shared)))

    def test_wrong_package_and_bad_base64_rejected(self):
        for value in (
            {},None,[],{"filename":"fake.xlsx","projectName":"Example","contentBase64":"not base64"},
            request(b"this is not an XLSX ZIP"),
            request(b""),
            request(make_workbook(),filename="../not.xlsx"),
            request(make_workbook(),filename="data.xls"),
            request(make_workbook(),name=""),
            {**request(make_workbook()),"unknown":"not-supported"},
        ):
            with self.subTest(value=str(value)[:80]),self.assertRaises(ProjectValidationError):
                import_xlsx_workbook(value)

    def test_zip_duplicate_part_rejected(self):
        raw=make_workbook()
        with zipfile.ZipFile(__import__("io").BytesIO(raw)) as archive:
            values={f:archive.read(f) for f in archive.namelist()}
        out=__import__("io").BytesIO()
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as archive:
                for name,contents in values.items():
                    archive.writestr(name,contents)
                archive.writestr("xl/workbook.xml",values["xl/workbook.xml"])
        with self.assertRaisesRegex(ProjectValidationError,"duplicate ZIP parts"):
            import_xlsx_workbook(request(out.getvalue()))


class XlsxHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.server=LabHTTPServer(("127.0.0.1",0),ProjectStore(self.root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def post(self,body):
        req=Request(self.base+"/api/import/xlsx",data=json.dumps(body).encode("utf-8"),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=10) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as exc:
            return exc.code,json.loads(exc.read())

    def test_http_real_excel_import_requires_explicit_later_save(self):
        raw=make_workbook(shared_strings=True,reorder=True)
        code,response=self.post(request(raw,"Saved only on consent"))
        self.assertEqual(code,200)
        p=response["project"]
        self.assertEqual(p["name"],"Saved only on consent")
        self.assertEqual(p["links"][0]["id"],"cable-1")
        self.assertEqual(list(self.root.glob("*.yadilab")),[])
        saved=self.server.store.save("xlsx-review",p)
        actual=(self.root/"xlsx-review.yadilab").read_bytes()
        self.assertEqual(saved["sha256"],hashlib.sha256(actual).hexdigest())
        self.assertEqual(self.server.store.read("xlsx-review")["project"],p)

    def test_http_bad_workbook_rejected_and_saved_bytes_unchanged(self):
        p=import_xlsx_workbook(request(make_workbook()))
        saved=self.server.store.save("lab",p)
        original=(self.root/"lab.yadilab").read_bytes()
        for file in (
            make_workbook({"Links":LINKS}),
            modify("xl/worksheets/sheet1.xml",'<row r="2">','<row r="2" hidden="1">'),
            b"not zip",
        ):
            with self.subTest(file=file[:10]):
                code,result=self.post(request(file))
                self.assertEqual(code,422)
                self.assertEqual(result["error"],"INVALID_PROJECT")
        self.assertEqual((self.root/"lab.yadilab").read_bytes(),original)
        self.assertEqual(self.server.store.read("lab")["sha256"],saved["sha256"])
        self.assertEqual(list(self.root.glob("*.yadilab")), [self.root/"lab.yadilab"])


if __name__=="__main__":
    unittest.main()
