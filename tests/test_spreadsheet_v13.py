"""Schema 1.3 across independently written XLSX and ODS, with actual ping/Save."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from network_core.icmp_ping import EchoExchange
from network_core.model import ProjectValidationError
from network_core.server import LabHTTPServer
from network_core.storage import ProjectStore
from network_core.xlsx_import import import_xlsx_workbook
from network_core.ods_import import import_ods_workbook
from spreadsheet_v13_fixture import TABLES_13, expected_v13
from xlsx_fixture import make_workbook
from ods_fixture import make_ods


def request(content, ext):
    return {"filename":"document." + ext, "projectName":"V13 laboratory",
            "contentBase64":base64.b64encode(content).decode("ascii")}


def formats(tables):
    return [
        ("xlsx", make_workbook(tables, shared_strings=True, reorder=True), import_xlsx_workbook),
        ("ods", make_ods(tables, reorder=True, trailing=True), import_ods_workbook),
    ]


def change(sheet, old, new):
    changed = copy.deepcopy(TABLES_13)
    assert old in changed[sheet], f"fixture anchor missing: {sheet} {old}"
    changed[sheet] = changed[sheet].replace(old, new, 1)
    return changed


class Spreadsheet13Tests(unittest.TestCase):
    def test_both_real_zip_formats_produce_exact_same_canonical_13_model(self):
        expected = expected_v13()
        for ext, raw, importer in formats(TABLES_13):
            with self.subTest(ext=ext):
                p = importer(request(raw, ext))
                self.assertEqual(p, expected)
                self.assertEqual(p["schemaVersion"], "1.3")
                self.assertEqual([l["id"] for l in p["links"]],
                                 ["cable-a", "trunk", "router-lan", "router-wan"])
                sa = next(n for n in p["nodes"] if n["id"]=="sa")
                self.assertEqual(sa["ports"][1]["vlan"],
                                 {"mode":"trunk","allowedVlans":[10,20]})
                self.assertEqual(p["nodes"][0]["ports"][0]["mac"], "02:00:00:00:00:0A")
                self.assertEqual(p["nodes"][0]["staticRoutes"][0]["destination"],
                                 "203.0.113.0/24")

    def test_imported_network_runs_real_bidirectional_icmp_over_trunk_router_and_arp(self):
        for ext, raw, importer in formats(TABLES_13):
            with self.subTest(ext=ext):
                project = importer(request(raw, ext))
                exchange = EchoExchange(project).ping("ha","eth0","203.0.113.20",5,73,11)
                self.assertEqual(exchange["status"],"REPLIED")
                self.assertEqual(exchange["request"]["status"],"DELIVERED")
                self.assertEqual(exchange["reply"]["status"],"DELIVERED")
                ids = [
                    transmission["linkId"]
                    for hop in exchange["request"]["steps"]
                    for transmission in hop["ipv4Transmissions"]
                ]
                self.assertIn("trunk", ids)
                self.assertIn("router-lan", ids)
                self.assertIn("router-wan", ids)

    def test_unversioned_legacy_four_tab_import_remains_schema10(self):
        from test_csv_import import DEV, PORTS, LINKS, ZONES
        legacy = {"Devices":DEV, "Interfaces":PORTS, "Links":LINKS, "Zones":ZONES}
        for ext, raw, importer in formats(legacy):
            with self.subTest(ext=ext):
                p = importer(request(raw, ext))
                self.assertEqual(p["schemaVersion"],"1.0")
                self.assertEqual(p["links"][0]["id"],"cable-1")
                self.assertNotIn("mac", p["nodes"][0]["ports"][0])
                self.assertNotIn("staticRoutes", p["nodes"][0])

    def test_explicit_13_marker_required_for_extended_interfaces(self):
        bad = {k:v for k,v in TABLES_13.items() if k!="Project"}
        for ext, raw, importer in formats(bad):
            with self.subTest(ext=ext),self.assertRaises(ProjectValidationError):
                importer(request(raw, ext))

    def test_declared_static_routes_without_version_marker_rejected(self):
        bad = {k:v for k,v in TABLES_13.items() if k not in ("Project","Interfaces")}
        for ext, raw, importer in formats(bad):
            with self.subTest(ext=ext),self.assertRaises(ProjectValidationError):
                importer(request(raw, ext))

    def test_version_marker_must_be_exactly_one_row_and_13(self):
        for value in ("1.0", "1.2", "2.0", "", "01.3", "1.3\n1.3"):
            doc = change("Project","1.3",value)
            for ext,raw,importer in formats(doc):
                with self.subTest(ext=ext,marker=value),self.assertRaises(ProjectValidationError):
                    importer(request(raw,ext))

    def test_mac_duplicate_invalid_unicast_and_on_switch_fail_closed(self):
        cases=[
            change("Interfaces","02:00:00:00:00:0D","02:00:00:00:00:0A"),
            change("Interfaces","02:00:00:00:00:0A","01:00:00:00:00:0A"),
            change("Interfaces","02:00:00:00:00:0A","not-a-mac"),
            change("Interfaces","sa,host,Host access,true,,,access,10,",
                   "sa,host,Host access,true,,02:00:00:00:00:EF,access,10,"),
        ]
        for doc in cases:
            for ext,raw,importer in formats(doc):
                with self.subTest(ext=ext,case=str(doc["Interfaces"])[-80:]),self.assertRaises(ProjectValidationError):
                    importer(request(raw,ext))

    def test_access_vlan_id_invalid_empty_or_mode_conflict(self):
        cases=[
            change("Interfaces","access,10,","access,0,"),
            change("Interfaces","access,10,","access,4095,"),
            change("Interfaces","access,10,","access,010,"),
            change("Interfaces","access,10,","access,10,20"),
            change("Interfaces","access,10,","access,,"),
            change("Interfaces","access,10,",",10,"),
            change("Interfaces","access,10,","invalid,10,"),
        ]
        for doc in cases:
            for ext,raw,importer in formats(doc):
                with self.subTest(ext=ext,source=doc["Interfaces"].splitlines()[2]),self.assertRaises(ProjectValidationError):
                    importer(request(raw,ext))

    def test_trunk_vlan_invalid_duplicate_and_wrong_field(self):
        cases=[
            change("Interfaces","trunk,,10|20","trunk,,10|10"),
            change("Interfaces","trunk,,10|20","trunk,,10|0"),
            change("Interfaces","trunk,,10|20","trunk,,10|020"),
            change("Interfaces","trunk,,10|20","trunk,,"),
            change("Interfaces","trunk,,10|20","trunk,10,10|20"),
        ]
        for doc in cases:
            for ext,raw,importer in formats(doc):
                with self.subTest(ext=ext),self.assertRaises(ProjectValidationError):
                    importer(request(raw,ext))

    def test_route_wrong_next_hop_missing_port_and_unknown_device(self):
        cases=[
            change("StaticRoutes","192.0.2.1,eth0","198.51.100.1,eth0"),
            change("StaticRoutes","192.0.2.1,eth0","192.0.2.10,eth0"),
            change("StaticRoutes","192.0.2.1,eth0","192.0.2.0,eth0"),
            change("StaticRoutes","192.0.2.1,eth0","192.0.2.1,missing"),
            change("StaticRoutes","ha,to-network-b","unknown,to-network-b"),
            change("StaticRoutes","203.0.113.0/24","203.0.113.7/24"),
        ]
        for doc in cases:
            for ext,raw,importer in formats(doc):
                with self.subTest(ext=ext,route=doc["StaticRoutes"]),self.assertRaises(ProjectValidationError):
                    importer(request(raw,ext))

    def test_duplicate_route_ids_and_duplicate_facts_rejected(self):
        doc=copy.deepcopy(TABLES_13)
        doc["StaticRoutes"] += "ha,to-network-b,198.51.100.0/24,192.0.2.1,eth0\n"
        for ext,raw,importer in formats(doc):
            with self.subTest(ext=ext),self.assertRaises(ProjectValidationError):
                importer(request(raw,ext))

    def test_static_routes_on_switch_not_validated_as_forwarding(self):
        doc=copy.deepcopy(TABLES_13)
        doc["StaticRoutes"] += "sa,r-to,198.51.100.0/24,192.0.2.1,host\n"
        for ext,raw,importer in formats(doc):
            with self.subTest(ext=ext),self.assertRaises(ProjectValidationError):
                importer(request(raw,ext))

    def test_unknown_extra_column_and_duplicate_column_rejected(self):
        cases=[
            change("Interfaces","allowedVlans","unexpected"),
            change("Interfaces","vlanMode,accessVlan","vlanMode,vlanMode"),
            change("Project","schemaVersion","unexpected"),
            change("StaticRoutes","outPort","nextHop"),
            change("Interfaces","nodeId,id,name,enabled,ipv4,mac,vlanMode,accessVlan,allowedVlans",
                   "nodeId,id,name,enabled,ipv4,mac,vlanMode,accessVlan,allowedVlans,ignored"),
        ]
        for doc in cases:
            for ext,raw,importer in formats(doc):
                with self.subTest(ext=ext),self.assertRaises(ProjectValidationError):
                    importer(request(raw,ext))

    def test_empty_optional_routes_and_missing_optional_vlan_mac_valid(self):
        doc=copy.deepcopy(TABLES_13)
        doc.pop("StaticRoutes")
        doc["Interfaces"]=doc["Interfaces"].replace(
            "02:00:00:00:00:0A,,,",",,,")
        for ext,raw,importer in formats(doc):
            with self.subTest(ext=ext):
                p=importer(request(raw,ext))
                self.assertEqual(p["schemaVersion"],"1.3")
                self.assertNotIn("mac",p["nodes"][0]["ports"][0])
                self.assertNotIn("staticRoutes",p["nodes"][0])
                self.assertEqual(len(p["links"]),4)

    def test_v13_save_open_exact_model_and_sha_for_both_formats(self):
        with tempfile.TemporaryDirectory() as root:
            store=ProjectStore(Path(root))
            for ext,raw,importer in formats(TABLES_13):
                project=importer(request(raw,ext))
                self.assertFalse(list(Path(root).glob("*.yadilab")) if ext=="xlsx" else False)
                name="test-"+ext
                saved=store.save(name,project)
                data=(Path(root)/(name+".yadilab")).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),saved["sha256"])
                self.assertEqual(store.read(name)["project"],expected_v13())
                self.assertEqual(json.loads(data),project)


class Spreadsheet13HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.server=LabHTTPServer(("127.0.0.1",0),ProjectStore(self.root))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.origin=f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def post(self,ext,raw):
        req=Request(self.origin+"/api/import/"+ext,data=json.dumps(request(raw,ext)).encode(),
                    headers={"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=10) as resp:
                return resp.status,json.loads(resp.read())
        except HTTPError as err:
            return err.code,json.loads(err.read())

    def test_live_http_both_imports_return_verbatim_schema13_without_writes(self):
        for ext,raw,_ in formats(TABLES_13):
            with self.subTest(ext=ext):
                code,result=self.post(ext,raw)
                self.assertEqual(code,200)
                self.assertEqual(result["project"],expected_v13())
                self.assertEqual(list(self.root.glob("*.yadilab")),[])

    def test_live_http_invalid_route_or_version_rejected_no_mutation(self):
        self.server.store.save("original",expected_v13())
        before=(self.root/"original.yadilab").read_bytes()
        bad=[
            change("StaticRoutes","192.0.2.1,eth0","8.8.8.8,eth0"),
            change("Project","1.3","1.2"),
        ]
        for doc in bad:
            for ext,raw,_ in formats(doc):
                with self.subTest(ext=ext,doc=doc["Project"]):
                    code,result=self.post(ext,raw)
                    self.assertEqual(code,422)
                    self.assertEqual(result["error"],"INVALID_PROJECT")
        self.assertEqual((self.root/"original.yadilab").read_bytes(),before)


if __name__=="__main__":
    unittest.main()
