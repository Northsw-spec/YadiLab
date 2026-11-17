"""Project -> actual XLSX/ODS -> import identity, strict negative and HTTP checks."""
from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.csv_import import import_csv_tables
from network_core.model import ProjectValidationError, validate_project
from network_core.server import LabHTTPServer
from network_core.spreadsheet_export import export_workbook
from network_core.storage import ProjectStore
from network_core.xlsx_import import import_xlsx_workbook
from network_core.ods_import import import_ods_workbook
from spreadsheet_v13_fixture import expected_v13
from test_csv_import import source


def reimport(data: bytes, extension: str, name: str):
    callback = import_xlsx_workbook if extension == "xlsx" else import_ods_workbook
    return callback({
        "filename": "document." + extension, "projectName": name,
        "contentBase64": base64.b64encode(data).decode("ascii"),
    })


class ProjectSpreadsheetExportTests(unittest.TestCase):
    def test_schema13_actual_zip_roundtrip_macs_vlans_routes_links_identity(self):
        original = expected_v13()
        before = json.dumps(original, sort_keys=True)
        for extension in ("xlsx", "ods"):
            with self.subTest(extension=extension):
                data = export_workbook(original, extension)
                self.assertEqual(data[:2], b"PK")
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    self.assertIn("xl/workbook.xml" if extension == "xlsx"
                                  else "content.xml", archive.namelist())
                    if extension == "ods":
                        self.assertEqual(archive.namelist()[0], "mimetype")
                        self.assertEqual(archive.getinfo("mimetype").compress_type,
                                         zipfile.ZIP_STORED)
                restored = reimport(data, extension, original["name"])
                self.assertEqual(restored, original)
                self.assertEqual(restored["nodes"][0]["staticRoutes"][0]["id"], "to-network-b")
                self.assertEqual(restored["nodes"][1]["ports"][1]["vlan"]["allowedVlans"], [10,20])
                self.assertEqual(restored["links"][1]["a"], {"node":"sa","port":"uplink"})
        self.assertEqual(json.dumps(original, sort_keys=True), before)

    def test_schema10_stays_legacy_and_recovers_original_ids(self):
        original = import_csv_tables({**source(), "projectName": "Legacy roundtrip"})
        self.assertEqual(original["schemaVersion"], "1.0")
        for extension in ("xlsx","ods"):
            with self.subTest(extension=extension):
                raw=export_workbook(original,extension)
                restored=reimport(raw,extension,original["name"])
                self.assertEqual(restored,original)
                self.assertEqual(restored["schemaVersion"],"1.0")
                self.assertEqual(restored["links"][0]["b"],{"node":"sw-a","port":"gi1"})

    def test_unicode_xml_entities_multiline_labels_and_disabled_facts(self):
        original=copy.deepcopy(expected_v13())
        original["name"]="Export & import <test>"
        original["nodes"][0]["label"]="Södra\nrummet & <väst> \t enhet"
        original["nodes"][1]["ports"][0]["name"]='Ändpunkt "alpha" & beta'
        original["zones"][0]["label"]="Zon \t A\nB"
        original["links"][0]["enabled"]=False
        original["nodes"][0]["ports"][0]["enabled"]=False
        original=validate_project(original)
        for extension in ("xlsx","ods"):
            with self.subTest(extension=extension):
                data=export_workbook(original,extension)
                self.assertEqual(reimport(data,extension,original["name"]),original)

    def test_missing_optional_sections_no_routes_and_no_implicit_facts(self):
        sample=copy.deepcopy(expected_v13())
        for node in sample["nodes"]:
            node.pop("staticRoutes",None)
            for port in node["ports"]:
                port.pop("mac",None)
                port.pop("vlan",None)
        sample["links"]=[]
        sample["zones"]=[{"id":"office","label":"Office network"}]
        sample=validate_project(sample)
        for extension in ("xlsx","ods"):
            with self.subTest(extension=extension):
                restored=reimport(export_workbook(sample,extension),extension,sample["name"])
                self.assertEqual(restored,sample)
                self.assertEqual(restored["links"],[])

    def test_export_requires_at_least_one_declared_node(self):
        value={"schemaVersion":"1.3","name":"Empty","zones":[],"nodes":[],"links":[]}
        for extension in ("xlsx","ods"):
            with self.assertRaisesRegex(ProjectValidationError,"at least one declared device"):
                export_workbook(value,extension)

    def test_explicit_null_optional_mac_and_vlan_are_rejected(self):
        for field,node_index,port_index in (("mac",0,0),("vlan",1,0)):
            model=copy.deepcopy(expected_v13())
            model["nodes"][node_index]["ports"][port_index][field]=None
            model=validate_project(model)
            for extension in ("xlsx","ods"):
                with self.subTest(field=field,extension=extension), self.assertRaisesRegex(
                    ProjectValidationError, "explicit null optional"):
                    export_workbook(model,extension)

    def test_explicit_empty_static_routes_are_rejected(self):
        original=copy.deepcopy(expected_v13())
        original["nodes"][1]["staticRoutes"]=[]
        original=validate_project(original)
        for extension in ("xlsx","ods"):
            with self.assertRaisesRegex(ProjectValidationError,"explicit empty staticRoutes"):
                export_workbook(original,extension)

    def test_legacy_11_12_rejected_without_migration(self):
        for version in ("1.1","1.2"):
            original=import_csv_tables({**source(),"projectName":"Older version"})
            original["schemaVersion"]=version
            original=validate_project(original)
            for extension in ("xlsx","ods"):
                with self.subTest(version=version,extension=extension), self.assertRaisesRegex(
                    ProjectValidationError, "no automatic migration"):
                    export_workbook(original,extension)

    def test_invalid_unknown_fields_and_bad_format_rejected(self):
        valid=expected_v13()
        with self.assertRaises(ProjectValidationError):
            export_workbook({**valid,"notKnown":"value"},"xlsx")
        for format in ("csv", "xls", "", "XLSX", None, 2):
            with self.subTest(format=format),self.assertRaises(ProjectValidationError):
                export_workbook(valid,format)

    def test_binary_export_deterministic_same_input_not_modified(self):
        original=expected_v13()
        for extension in ("xlsx","ods"):
            with self.subTest(extension=extension):
                self.assertEqual(hashlib.sha256(export_workbook(original,extension)).hexdigest(),
                                 hashlib.sha256(export_workbook(original,extension)).hexdigest())

    def test_invalid_control_character_rejected_without_silent_loss(self):
        original=copy.deepcopy(expected_v13())
        original["nodes"][0]["label"]="Control\vcharacter"
        for extension in ("xlsx","ods"):
            with self.assertRaisesRegex(ProjectValidationError,"control character"):
                export_workbook(original,extension)

    def test_no_hidden_save_and_explicit_disk_bytes_sha_across_restart(self):
        with tempfile.TemporaryDirectory() as root:
            project=expected_v13()
            for extension in ("xlsx","ods"):
                raw=export_workbook(project,extension)
                self.assertEqual(list(Path(root).glob("*.yadilab")),[])
                restored=reimport(raw,extension,project["name"])
                store=ProjectStore(Path(root))
                saved=store.save("roundtrip-"+extension,restored)
                disk=(Path(root)/("roundtrip-"+extension+".yadilab")).read_bytes()
                self.assertEqual(saved["sha256"],hashlib.sha256(disk).hexdigest())
                reopened=ProjectStore(Path(root)).read("roundtrip-"+extension)["project"]
                self.assertEqual(reopened,project)
                # Only the saved file was written, never a workbook.
                self.assertEqual(list(Path(root).glob("*.xlsx")),[])
                self.assertEqual(list(Path(root).glob("*.ods")),[])


class ProjectSpreadsheetExportHTTPTests(unittest.TestCase):
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

    def post(self, body):
        req=Request(self.url+"/api/export/spreadsheet",data=json.dumps(body).encode(),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=15) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as error:
            return error.code,json.loads(error.read())

    def test_http_both_file_formats_exact_reimport_without_auto_save(self):
        original=expected_v13()
        saved=self.server.store.save("old",original)
        old_bytes=(self.root/"old.yadilab").read_bytes()
        for extension in ("xlsx","ods"):
            with self.subTest(extension=extension):
                code,data=self.post({"format":extension,"project":original})
                self.assertEqual(code,200)
                self.assertEqual(data["filename"],"network-documentation."+extension)
                content=base64.b64decode(data["contentBase64"],validate=True)
                self.assertEqual(content[:2],b"PK")
                self.assertEqual(reimport(content,extension,original["name"]),original)
                self.assertEqual(list(self.root.glob("*.yadilab")),[self.root/"old.yadilab"])
                self.assertEqual((self.root/"old.yadilab").read_bytes(),old_bytes)
        self.assertEqual(self.server.store.read("old")["sha256"],saved["sha256"])

    def test_http_uses_actual_unsaved_request_not_previous_disk_data(self):
        baseline=expected_v13()
        self.server.store.save("previous",baseline)
        old_bytes=(self.root/"previous.yadilab").read_bytes()
        modified=copy.deepcopy(baseline)
        modified["nodes"][0]["label"]="Unsaved working label"
        code,response=self.post({"format":"ods","project":modified})
        self.assertEqual(code,200)
        data=base64.b64decode(response["contentBase64"])
        restored=reimport(data,"ods",modified["name"])
        self.assertEqual(restored["nodes"][0]["label"],"Unsaved working label")
        self.assertEqual((self.root/"previous.yadilab").read_bytes(),old_bytes)

    def test_http_bad_export_preserves_existing_sha(self):
        original=expected_v13()
        self.server.store.save("original",original)
        old=(self.root/"original.yadilab").read_bytes()
        broken=copy.deepcopy(original)
        broken["nodes"][0]["ports"][0]["mac"]=None
        for request in (
            {"format":"ods","project":broken},
            {"format":"xls","project":original},
            {"format":"xlsx","project":{}},
            {"format":"xlsx","project":original,"unexpected":123},
        ):
            with self.subTest(request=str(request)[:40]):
                code,response=self.post(request)
                self.assertEqual(code,422)
                self.assertEqual(response["error"],"INVALID_PROJECT")
                self.assertEqual((self.root/"original.yadilab").read_bytes(),old)


if __name__=="__main__":
    unittest.main()
