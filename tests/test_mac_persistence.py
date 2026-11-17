"""Schema 1.0/1.1 and real disk/session behavior for explicit NIC MACs."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from network_core.arp import ArpSession
from network_core.ethernet import EthernetFabric
from network_core.ethernet_frame import EthernetFrame
from network_core.model import ProjectValidationError, validate_project
from network_core.storage import ProjectStore
from test_arp import network
from test_ethernet import A, B
from test_model import example


def with_persisted_macs():
    p = network()
    p["schemaVersion"] = "1.1"
    p["nodes"][0]["ports"][0]["mac"] = A.lower()
    p["nodes"][2]["ports"][0]["mac"] = B
    return p


class MacSchemaTests(unittest.TestCase):
    def test_legacy_v1_0_unchanged_and_requires_explicit_upgrade(self):
        old = example()
        old["schemaVersion"] = "1.0"
        self.assertEqual(validate_project(old), old)
        changed = copy.deepcopy(old)
        changed["nodes"][0]["ports"][0]["mac"] = A
        with self.assertRaisesRegex(ProjectValidationError, "unsupported fields"):
            validate_project(changed)
        changed["schemaVersion"] = "1.1"
        self.assertEqual(validate_project(changed)["nodes"][0]["ports"][0]["mac"], A)
        self.assertEqual(changed["links"], old["links"])

    def test_v1_1_normalization_and_optional_mac(self):
        p = with_persisted_macs()
        normalized = validate_project(p)
        self.assertEqual(normalized["schemaVersion"], "1.1")
        self.assertEqual(normalized["nodes"][0]["ports"][0]["mac"], A)
        self.assertEqual(normalized["nodes"][2]["ports"][0]["mac"], B)
        self.assertNotIn("mac", normalized["nodes"][1]["ports"][0])
        normalized["nodes"][2]["ports"][0]["mac"] = None
        self.assertIsNone(validate_project(normalized)["nodes"][2]["ports"][0]["mac"])
        self.assertEqual(validate_project(normalized), normalized)

    def test_invalid_mac_rejected_not_discarded(self):
        for address in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF",
                        "01:00:5E:00:00:01", "02-00-00-00-00-01",
                        "02:00:00:00:00", "", "zz:00:00:00:00:01", 12, {}, True):
            with self.subTest(address=address):
                p = with_persisted_macs()
                p["nodes"][0]["ports"][0]["mac"] = address
                with self.assertRaises(ProjectValidationError):
                    validate_project(p)

    def test_duplicate_project_mac_rejected_without_normalization_bypass(self):
        p = with_persisted_macs()
        p["nodes"][2]["ports"][0]["mac"] = A
        with self.assertRaisesRegex(ProjectValidationError, "duplicate endpoint MAC"):
            validate_project(p)

    def test_switch_mac_rejected_and_unknown_fields_fail_closed(self):
        p = with_persisted_macs()
        p["nodes"][1]["ports"][0]["mac"] = A
        with self.assertRaisesRegex(ProjectValidationError, "switch ports"):
            validate_project(p)
        p = with_persisted_macs()
        p["nodes"][0]["ports"][0]["invented"] = "data"
        with self.assertRaisesRegex(ProjectValidationError, "unsupported fields"):
            validate_project(p)

    def test_new_version_or_absent_field_never_default_mac(self):
        p = with_persisted_macs()
        p["schemaVersion"] = "2.0"
        with self.assertRaisesRegex(ProjectValidationError, "only"):
            validate_project(p)
        p = example()
        p["schemaVersion"] = "1.1"
        self.assertTrue(all("mac" not in port for n in validate_project(p)["nodes"] for port in n["ports"]))

    def test_real_bytes_hash_restart_and_no_implicit_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            first = ProjectStore(Path(temp))
            legacy = example()
            legacy["schemaVersion"] = "1.0"
            first.save("legacy", legacy)
            legacy_sha = (Path(temp) / "legacy.yadilab").read_bytes()
            self.assertEqual(ProjectStore(Path(temp)).read("legacy")["project"], legacy)
            self.assertEqual((Path(temp) / "legacy.yadilab").read_bytes(), legacy_sha)
            edited = with_persisted_macs()
            result = first.save("macs", edited)
            path = Path(temp) / "macs.yadilab"
            raw = path.read_bytes()
            self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(json.loads(raw)["nodes"][0]["ports"][0]["mac"], A)
            reloaded = ProjectStore(Path(temp)).read("macs")
            self.assertEqual(reloaded["project"], validate_project(edited))
            self.assertEqual(reloaded["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual((Path(temp) / "legacy.yadilab").read_bytes(), legacy_sha)
            bad = copy.deepcopy(edited)
            bad["nodes"][2]["ports"][0]["mac"] = A
            with self.assertRaises(ProjectValidationError):
                first.save("bad", bad)
            self.assertFalse((Path(temp) / "bad.yadilab").exists())

    def test_saved_identity_used_by_ethernet_and_arp_but_cache_not_saved(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ProjectStore(Path(temp))
            store.save("macs", with_persisted_macs())
            saved = ProjectStore(Path(temp)).read("macs")["project"]
            original = copy.deepcopy(saved)
            fabric = EthernetFabric(saved)
            self.assertEqual(fabric.bound_macs(), {("a", "eth0"): A, ("b", "eth0"): B})
            frame = EthernetFrame(B, A, 0x88B5, b"test")
            self.assertEqual(fabric.inject_frame("a", "eth0", frame)["status"], "SIMULATED")
            self.assertEqual(fabric.mac_table("sw"), {A: "p1"})
            with self.assertRaisesRegex(ProjectValidationError, "conflicts with persisted"):
                EthernetFabric(saved, interface_macs={("a", "eth0"): B})
            self.assertEqual(EthernetFabric(saved, interface_macs={("a", "eth0"): A}).bound_macs(),
                             {("a", "eth0"): A, ("b", "eth0"): B})
            session = ArpSession(saved)
            result = session.resolve("a", "eth0", "192.0.2.20")
            self.assertEqual(result["status"], "RESOLVED")
            self.assertEqual(result["resolvedMac"], B)
            self.assertEqual(session.arp_table("a", "eth0"), {"192.0.2.20": B})
            self.assertEqual(saved, original)
            reopened = ProjectStore(Path(temp)).read("macs")["project"]
            self.assertEqual(reopened, original)
            self.assertEqual(ArpSession(reopened).arp_table("a", "eth0"), {})


if __name__ == "__main__":
    unittest.main()
