"""Persisted VLAN declarations in schema 1.2 with strict lossless validation."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from network_core.arp import ArpSession
from network_core.ethernet import EthernetFabric
from network_core.model import ProjectValidationError, blank_project, validate_project
from network_core.storage import ProjectStore
from test_ethernet import A, B, C, node, link
from test_vlan import two_switches, access, trunk
from test_vlan_arp import two_switch_arp


def persisted_topology():
    project, ports, macs = two_switch_arp()
    project["schemaVersion"] = "1.2"
    for n in project["nodes"]:
        for p in n["ports"]:
            key = n["id"], p["id"]
            if key in ports:
                p["vlan"] = copy.deepcopy(ports[key])
            if key in macs:
                p["mac"] = macs[key]
    return project


def get_port(project, node_id, port_id):
    node = next(n for n in project["nodes"] if n["id"] == node_id)
    return next(p for p in node["ports"] if p["id"] == port_id)


class PersistentVlanTests(unittest.TestCase):
    def test_new_defaults_to_v1_3_without_inventing_vlans_or_routes(self):
        p = blank_project("No implicit memberships")
        self.assertEqual(p["schemaVersion"], "1.3")
        self.assertEqual(p["nodes"], [])
        self.assertEqual(validate_project(p), p)

    def test_strict_schema_migration_and_legacy_document_preservation(self):
        for version in ("1.0", "1.1"):
            with self.subTest(version=version):
                legacy, _, _ = two_switch_arp()
                legacy["schemaVersion"] = version
                original = copy.deepcopy(legacy)
                self.assertEqual(validate_project(legacy), original)
                self.assertEqual(legacy, original)
                modified = copy.deepcopy(legacy)
                get_port(modified, "s1", "h")["vlan"] = access(10)
                with self.assertRaisesRegex(ProjectValidationError, "unsupported fields"):
                    validate_project(modified)
                modified["schemaVersion"] = "1.2"
                migrated = validate_project(modified)
                self.assertEqual(migrated["schemaVersion"], "1.2")
                self.assertEqual(migrated["nodes"][0], original["nodes"][0])
                self.assertEqual(migrated["links"], original["links"])
                self.assertEqual(get_port(migrated, "s1", "h")["vlan"], access(10))
        project = persisted_topology()
        project["schemaVersion"] = "2.0"
        with self.assertRaisesRegex(ProjectValidationError, "only"):
            validate_project(project)

    def test_roundtrip_explicit_access_and_trunk_preserves_identity(self):
        p = persisted_topology()
        normalized = validate_project(p)
        self.assertEqual(normalized, p)
        self.assertEqual(get_port(normalized, "s1", "h")["vlan"], access(10))
        self.assertEqual(get_port(normalized, "s1", "t")["vlan"], trunk(10, 20))
        self.assertEqual(get_port(normalized, "a", "eth0")["mac"], A)
        self.assertEqual(normalized["links"], p["links"])

    def test_absent_and_null_are_not_default_vlan_memberships(self):
        p = persisted_topology()
        del get_port(p, "s1", "t")["vlan"]
        get_port(p, "s2", "x")["vlan"] = None
        validated = validate_project(p)
        self.assertNotIn("vlan", get_port(validated, "s1", "t"))
        self.assertIsNone(get_port(validated, "s2", "x")["vlan"])
        with self.assertRaisesRegex(ProjectValidationError, "missing configuration"):
            EthernetFabric(validated)
        with self.assertRaisesRegex(ProjectValidationError, "missing configuration"):
            ArpSession(validated)

    def test_no_persisted_vlan_keeps_legacy_forwarding(self):
        p, _, macs = two_switch_arp()
        p["schemaVersion"] = "1.2"
        fabric = EthernetFabric(p, interface_macs=macs)
        self.assertEqual(fabric.inject("a", "eth0", A, "FF:FF:FF:FF:FF:FF")["status"], "SIMULATED")
        self.assertEqual(fabric.mac_table("s1"), {A: "h"})

    def test_bad_vlans_and_unknown_fields_rejected(self):
        invalid = [
            {"mode": "access", "vlan": 0},
            {"mode": "access", "vlan": 4095},
            {"mode": "access", "vlan": True},
            {"mode": "access", "vlan": 10.0},
            {"mode": "access", "vlan": "10"},
            {"mode": "access", "vlan": 10, "allowedVlans": [20]},
            {"mode": "trunk", "allowedVlans": []},
            {"mode": "trunk", "allowedVlans": [10, 10]},
            {"mode": "trunk", "allowedVlans": [10, False]},
            {"mode": "trunk", "allowedVlans": [4095]},
            {"mode": "trunk", "allowedVlans": "10,20"},
            {"mode": "trunk", "allowedVlans": [10], "native": 10},
            {"mode": "other", "vlan": 10},
            "access:10", 10, True, [],
        ]
        for wrong in invalid:
            with self.subTest(wrong=wrong):
                p = persisted_topology()
                get_port(p, "s1", "h")["vlan"] = wrong
                with self.assertRaises(ProjectValidationError):
                    validate_project(p)

    def test_endpoint_vlan_prohibited_even_when_null(self):
        for value in (None, access(10), trunk(10)):
            with self.subTest(value=value):
                p = persisted_topology()
                get_port(p, "a", "eth0")["vlan"] = value
                with self.assertRaisesRegex(ProjectValidationError, "requires a switch"):
                    validate_project(p)

    def test_persisted_vlan_can_drive_vlan_arp_without_session_map(self):
        p = persisted_topology()
        original = copy.deepcopy(p)
        fabric = EthernetFabric(p)
        self.assertEqual(fabric.inject("a", "eth0", A, "FF:FF:FF:FF:FF:FF")["status"], "SIMULATED")
        self.assertEqual(fabric.mac_table("s1", 10), {A: "h"})
        self.assertEqual(fabric.mac_table("s1", 20), {})
        self.assertEqual(p, original)
        session = ArpSession(p)
        resolved = session.resolve("a", "eth0", "192.0.2.20")
        self.assertEqual(resolved["status"], "RESOLVED")
        self.assertEqual(resolved["resolvedMac"], B)
        self.assertEqual(resolved["requestTransmissions"][1]["vlanId"], 10)
        self.assertEqual(session.resolve("a", "eth0", "192.0.2.40")["status"], "NO_REPLY")
        self.assertEqual(session.arp_table("a", "eth0"), {"192.0.2.20": B})
        self.assertEqual(p, original)

    def test_persisted_and_session_conflicts_refused(self):
        p = persisted_topology()
        with self.assertRaisesRegex(ProjectValidationError, "conflicts with persisted"):
            EthernetFabric(p, vlan_ports={("s1", "h"): access(20)})
        with self.assertRaisesRegex(ProjectValidationError, "conflicts with persisted"):
            ArpSession(p, vlan_ports={("s1", "h"): access(20)})
        # Explicit matching override is allowed and cannot mutate project.
        fabric = EthernetFabric(p, vlan_ports={("s1", "h"): access(10)})
        self.assertEqual(fabric.inject("a", "eth0", A, B)["status"], "SIMULATED")
        self.assertEqual(get_port(p, "s1", "h")["vlan"], access(10))

    def test_session_can_complete_partial_explicit_documentation(self):
        p = persisted_topology()
        del get_port(p, "s2", "t")["vlan"]
        with self.assertRaisesRegex(ProjectValidationError, "missing configuration"):
            EthernetFabric(p)
        configured = EthernetFabric(p, vlan_ports={("s2", "t"): trunk(10, 20)})
        self.assertEqual(configured.inject("a", "eth0", A, B)["status"], "SIMULATED")
        self.assertNotIn("vlan", get_port(p, "s2", "t"))
        # A detached new session remains incomplete.
        with self.assertRaisesRegex(ProjectValidationError, "missing configuration"):
            ArpSession(p)

    def test_real_disk_bytes_sha_and_restart_without_transient_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = ProjectStore(root)
            old_v1, _, _ = two_switch_arp()
            for ver, filename in (("1.0", "old10"), ("1.1", "old11")):
                legacy = copy.deepcopy(old_v1)
                legacy["schemaVersion"] = ver
                store.save(filename, legacy)
                previous = (root / (filename + ".yadilab")).read_bytes()
                self.assertEqual(ProjectStore(root).read(filename)["project"], legacy)
                self.assertEqual(previous, (root / (filename + ".yadilab")).read_bytes())
            project = persisted_topology()
            saved = store.save("vlans", project)
            raw = (root / "vlans.yadilab").read_bytes()
            self.assertEqual(saved["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(json.loads(raw)["schemaVersion"], "1.2")
            self.assertEqual(json.loads(raw)["nodes"][1]["ports"][1]["vlan"], trunk(10, 20))
            reopened = ProjectStore(root).read("vlans")
            self.assertEqual(reopened["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(reopened["project"], validate_project(project))
            session = ArpSession(reopened["project"])
            self.assertEqual(session.resolve("a", "eth0", "192.0.2.20")["status"], "RESOLVED")
            self.assertEqual(ArpSession(ProjectStore(root).read("vlans")["project"]).arp_table("a", "eth0"), {})
            for filename in ("old10", "old11"):
                self.assertEqual(ProjectStore(root).read(filename)["project"]["schemaVersion"], "1.0" if filename == "old10" else "1.1")
            self.assertEqual((root / "vlans.yadilab").read_bytes(), raw)

    def test_invalid_save_rejected_without_creating_or_changing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProjectStore(Path(temp))
            project = persisted_topology()
            first = store.save("network", project)
            existing = (Path(temp) / "network.yadilab").read_bytes()
            bad = copy.deepcopy(project)
            get_port(bad, "s1", "t")["vlan"] = {"mode": "trunk", "allowedVlans": [10, 10]}
            with self.assertRaises(ProjectValidationError):
                store.save("network", bad, expected_sha256=first["sha256"])
            self.assertEqual((Path(temp) / "network.yadilab").read_bytes(), existing)
            with self.assertRaises(ProjectValidationError):
                store.save("invalid", bad)
            self.assertFalse((Path(temp) / "invalid.yadilab").exists())


if __name__ == "__main__":
    unittest.main()
