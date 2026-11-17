"""Strict ODS real ZIP/XML import and non-lossy canonical CSV interchange."""
from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import tempfile
import threading
import unittest
import warnings
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from network_core.csv_import import import_csv_tables
from network_core.model import ProjectValidationError, topology_trace
from network_core.ods_import import import_ods_workbook
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from ods_fixture import BASE_SHEETS, MIME, make_ods, ods_parts, zip_parts
from test_csv_import import source, DEV, PORTS, LINKS, ZONES


def body(raw: bytes, name: str="Documented ODS", filename: str="lab.ods") -> dict:
    return {"projectName":name, "filename":filename,
            "contentBase64":base64.b64encode(raw).decode("ascii")}


def patch(path: str, old: str, new: str, sheets=None) -> bytes:
    parts=ods_parts(sheets)
    data=parts[path].decode("utf-8")
    if old not in data:
        raise AssertionError(f"fixture anchor missing: {old[:65]}")
    parts[path]=data.replace(old,new,1).encode("utf-8")
    return zip_parts(parts)


class OdsFunctionalTests(unittest.TestCase):
    def test_real_zip_package_mime_manifest_and_exact_source_identifiers(self):
        raw=make_ods()
        self.assertEqual(raw[:2],b"PK")
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(z.namelist()[0],"mimetype")
            self.assertEqual(z.getinfo("mimetype").compress_type,zipfile.ZIP_STORED)
            self.assertEqual(z.read("mimetype"),MIME.encode())
            self.assertIn("META-INF/manifest.xml",z.namelist())
        doc=import_ods_workbook(body(raw,"ODS test"))
        expected=import_csv_tables({**source(), "projectName":"ODS test"})
        self.assertEqual(doc,expected)
        self.assertEqual(doc["schemaVersion"],"1.0")
        self.assertEqual([n["id"] for n in doc["nodes"]],["pc-a","sw-a"])
        self.assertEqual(doc["links"][0]["a"],{"node":"pc-a","port":"eth0"})
        self.assertEqual(doc["links"][0]["b"],{"node":"sw-a","port":"gi1"})
        self.assertEqual(doc["nodes"][0]["ports"][0]["ipv4"],"192.0.2.5/24")
        self.assertEqual(topology_trace(doc,"pc-a","sw-a")["status"],"PATH_PRESENT")

    def test_reordered_sheets_headers_unicode_multiline_and_trailing_empty_cells(self):
        altered=dict(BASE_SHEETS)
        altered["Devices"]=(
            'label,id,kind,y,x,zoneId\n'
            '"Serverrum\nöstra",pc-a,host,120,80,office\n'
            '"Växel, C",sw-a,switch,120,320,office\n'
        )
        doc=import_ods_workbook(body(make_ods(altered,reorder=True,trailing=True,styles=True)))
        self.assertEqual(doc["nodes"][0]["label"],"Serverrum\nöstra")
        self.assertEqual(doc["nodes"][1]["label"],"Växel, C")
        self.assertEqual(doc["nodes"][0]["x"],80)
        self.assertEqual(doc["nodes"][0]["y"],120)
        self.assertEqual(doc["links"][0]["id"],"cable-1")

    def test_required_devices_only_does_not_infer_ports_links_or_zones(self):
        sheets={"Devices":DEV.replace(",office",",")}
        doc=import_ods_workbook(body(make_ods(sheets)))
        self.assertEqual(len(doc["nodes"]),2)
        self.assertEqual(doc["zones"],[])
        self.assertEqual(doc["links"],[])
        self.assertTrue(all(not n["ports"] for n in doc["nodes"]))

    def test_empty_optional_tables_and_disabled_link(self):
        sheets={
            "Devices":DEV.replace(",office",","),
            "Interfaces":"nodeId,id,name,enabled,ipv4\n",
            "Links":"id,aNode,aPort,bNode,bPort,enabled\n",
        }
        doc=import_ods_workbook(body(make_ods(sheets)))
        self.assertEqual(doc["links"],[])
        disabled=dict(BASE_SHEETS)
        disabled["Links"]=LINKS.replace("true","false")
        d=import_ods_workbook(body(make_ods(disabled)))
        self.assertFalse(d["links"][0]["enabled"])
        self.assertEqual(topology_trace(d,"pc-a","sw-a")["status"],"NO_PATH")

    def test_invalid_references_duplicate_identifiers_headers_and_unknown_sheets(self):
        mutations=[
            {"Devices":DEV+"pc-a,Duplicated,host,8,10,office\n",
             "Interfaces":PORTS,"Links":LINKS,"Zones":ZONES},
            {"Devices":DEV,"Interfaces":PORTS.replace("sw-a,gi1","absent,gi1"),
             "Links":LINKS,"Zones":ZONES},
            {"Devices":DEV,"Interfaces":PORTS,"Links":LINKS.replace("sw-a,gi1","sw-a,nope"),
             "Zones":ZONES},
            {"Devices":DEV.replace("zoneId","wrong"),"Interfaces":PORTS,
             "Links":LINKS,"Zones":ZONES},
            {"Interfaces":PORTS,"Links":LINKS,"Zones":ZONES},
            {"Devices":DEV,"NetworkInventory":"id,name\nfoo,bar\n"},
            {"Devices":DEV,"Zones":ZONES.replace("office,Office","other,Other")},
        ]
        for sheets in mutations:
            with self.subTest(sheets=list(sheets)),self.assertRaises(ProjectValidationError):
                import_ods_workbook(body(make_ods(sheets)))

    def test_cell_formula_and_numeric_identity_rejected(self):
        for bad in (
            patch("content.xml",
                '<table:table-cell office:value-type="string"><text:p>pc-a</text:p></table:table-cell>',
                '<table:table-cell table:formula="of:=1+1" office:value-type="string"><text:p>pc-a</text:p></table:table-cell>'),
            patch("content.xml",
                '<table:table-cell office:value-type="string"><text:p>pc-a</text:p></table:table-cell>',
                '<table:table-cell office:value-type="float" office:value="12"><text:p>12</text:p></table:table-cell>'),
            patch("content.xml",
                '<table:table-cell office:value-type="string"><text:p>pc-a</text:p></table:table-cell>',
                '<table:covered-table-cell/>'),
        ):
            with self.subTest(bad=bad[:16]),self.assertRaises(ProjectValidationError):
                import_ods_workbook(body(bad))

    def test_hidden_sheet_row_column_rejected(self):
        for bad in (
            patch("content.xml",'<table:table table:name="Devices">',
                  '<table:table table:name="Devices" table:visibility="collapse">'),
            patch("content.xml",'<table:table-column table:number-columns-repeated="1024"/>',
                  '<table:table-column table:number-columns-repeated="1024" table:visibility="collapse"/>'),
            patch("content.xml",
                  '<table:table-row><table:table-cell office:value-type="string"><text:p>pc-a',
                  '<table:table-row table:visibility="filter"><table:table-cell office:value-type="string"><text:p>pc-a'),
        ):
            with self.assertRaises(ProjectValidationError):
                import_ods_workbook(body(bad))

    def test_bad_boolean_date_type_repeated_populated_data_and_extra_value(self):
        for bad in (
            patch("content.xml",'<table:table-cell office:value-type="boolean" office:boolean-value="true"/>',
                  '<table:table-cell office:value-type="boolean" office:boolean-value="maybe"/>'),
            patch("content.xml",'<table:table-cell office:value-type="string"><text:p>pc-a</text:p></table:table-cell>',
                  '<table:table-cell office:value-type="date" office:date-value="2026-11-17"/>'),
            patch("content.xml",'<table:table-cell office:value-type="string"><text:p>pc-a</text:p></table:table-cell>',
                  '<table:table-cell office:value-type="string" table:number-columns-repeated="2"><text:p>pc-a</text:p></table:table-cell>'),
            patch("content.xml",'<table:table-cell office:value-type="string"><text:p>pc-a</text:p></table:table-cell>',
                  '<table:table-cell office:value-type="string"><text:p>pc-a</text:p></table:table-cell><table:table-cell office:value-type="string"><text:p>unexpected</text:p></table:table-cell>'),
        ):
            with self.assertRaises(ProjectValidationError):
                import_ods_workbook(body(bad))

    def test_trailing_blank_rows_cannot_hide_later_populated_row(self):
        bad=patch("content.xml",
            '<table:table-row><table:table-cell office:value-type="string"><text:p>pc-a',
            '<table:table-row table:number-rows-repeated="2"><table:table-cell office:value-type="string"><text:p>pc-a')
        with self.assertRaises(ProjectValidationError):
            import_ods_workbook(body(bad))

    def test_external_file_macro_encrypted_manifest_and_unknown_xml_rejected(self):
        parts=ods_parts()
        parts["Basic/script.xba"]=b"<script/>"
        with self.assertRaisesRegex(ProjectValidationError,"unsupported package parts"):
            import_ods_workbook(body(zip_parts(parts)))
        bad=patch("META-INF/manifest.xml",
            '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>',
            '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"><manifest:encryption-data/></manifest:file-entry>')
        with self.assertRaises(ProjectValidationError):
            import_ods_workbook(body(bad))
        bad=patch("content.xml",'<office:body>',
                  '<office:scripts/><office:body>')
        with self.assertRaises(ProjectValidationError):
            import_ods_workbook(body(bad))

    def test_broken_archive_wrong_mime_manifest_and_duplicate_members(self):
        wrong=[
            b"",b"not a ZIP",
            zip_parts({**ods_parts(),"mimetype":b"application/vnd.oasis.opendocument.text"}),
            zip_parts({k:v for k,v in ods_parts().items() if k!="META-INF/manifest.xml"}),
            patch("META-INF/manifest.xml",
                'manifest:full-path="/" manifest:media-type="'+MIME+'"',
                'manifest:full-path="/" manifest:media-type="application/octet-stream"'),
        ]
        raw=ods_parts()
        out=io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(out,"w") as z:
                z.writestr("mimetype",raw["mimetype"],compress_type=zipfile.ZIP_STORED)
                z.writestr("content.xml",raw["content.xml"])
                z.writestr("content.xml",raw["content.xml"])
                z.writestr("META-INF/manifest.xml",raw["META-INF/manifest.xml"])
        wrong.append(out.getvalue())
        for value in wrong:
            with self.subTest(value=value[:12]),self.assertRaises(ProjectValidationError):
                import_ods_workbook(body(value))

    def test_bad_request_shape_filename_base64_and_size_rejected(self):
        raw=make_ods()
        values=[
            {},None,[],body(raw,filename="../lab.ods"),body(raw,filename="a.xlsx"),
            body(raw,name=""),body(raw,name="A"*121),
            {**body(raw),"unexpected":123},
            {"filename":"x.ods","projectName":"ok","contentBase64":"not b64"},
            {"filename":"x.ods","projectName":"ok","contentBase64":8},
        ]
        for value in values:
            with self.subTest(value=str(value)[:30]),self.assertRaises(ProjectValidationError):
                import_ods_workbook(value)

    def test_malformed_xml_missing_header_and_unsupported_markup(self):
        bad=ods_parts()
        bad["content.xml"]=b'<office:bad'
        with self.assertRaises(ProjectValidationError):
            import_ods_workbook(body(zip_parts(bad)))
        bad=patch("content.xml",'<text:p>pc-a</text:p>',
                  '<text:p><text:a xlink:href="https://example.org" xmlns:xlink="http://www.w3.org/1999/xlink">pc-a</text:a></text:p>')
        with self.assertRaises(ProjectValidationError):
            import_ods_workbook(body(bad))


class OdsHTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.server=LabHTTPServer(("127.0.0.1",0),ProjectStore(self.root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown();self.server.server_close()
        self.thread.join(timeout=5);self.tmp.cleanup()

    def post(self,value):
        req=Request(self.url+"/api/import/ods",data=json.dumps(value).encode(),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=10) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as exc:
            return exc.code,json.loads(exc.read())

    def test_http_ods_preserves_ids_no_autosave_and_explicit_save(self):
        code,result=self.post(body(make_ods(reorder=True,trailing=True),"ODS HTTP"))
        self.assertEqual(code,200)
        project=result["project"]
        self.assertEqual(project["name"],"ODS HTTP")
        self.assertEqual(project["links"][0]["id"],"cable-1")
        self.assertEqual(list(self.root.glob("*.yadilab")),[])
        save=self.server.store.save("from-ods",project)
        raw=(self.root/"from-ods.yadilab").read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),save["sha256"])
        self.assertEqual(self.server.store.read("from-ods")["project"],project)

    def test_http_bad_files_rejected_without_changing_existing_bytes(self):
        valid=import_ods_workbook(body(make_ods()))
        saved=self.server.store.save("previous",valid)
        before=(self.root/"previous.yadilab").read_bytes()
        for raw in (
            b"this-is-not-ods",
            make_ods({"Links":LINKS}),
            patch("content.xml",'<table:table table:name="Devices">',
                  '<table:table table:name="Devices" table:visibility="collapse">'),
        ):
            with self.subTest(raw=raw[:12]):
                status,response=self.post(body(raw))
                self.assertEqual(status,422)
                self.assertEqual(response["error"],"INVALID_PROJECT")
        self.assertEqual((self.root/"previous.yadilab").read_bytes(),before)
        self.assertEqual(self.server.store.read("previous")["sha256"],saved["sha256"])


if __name__ == "__main__":
    unittest.main()
