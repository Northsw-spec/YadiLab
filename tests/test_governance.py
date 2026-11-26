"""Governance tests for a PLANNED product. Not protocol implementation tests."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/requirements/pt_scope.json"
MIN_IDS = {f"PT-F{i:02}" for i in range(1, 37)}
EXCEPTIONS = ["non_linux_operating_system_ports", "new_keyboard_only_accessibility_requirements"]
DOCS = [
    "README.md", "MASTERPROMPT.md", "AGENTS.md", "docs/ROADMAP.md",
    "docs/ARCHITECTURE.md", "docs/PRODUCT_SCOPE.md", "docs/PROTOCOL_CATALOG.md",
    "docs/PROJECT_DATA_CONTRACT.md", "docs/UI_ELK_CONTRACT.md",
    "docs/IMPORT_CONTRACT.md", "docs/RESEARCH_WAVES.md", "docs/SECURITY_LEGAL.md",
    "docs/DECISIONS.md", "docs/VERIFICATION.md", "docs/RELEASE_GATES.md",
]

def check_scope(data):
    errors = []
    families = data.get("families", [])
    ids = [f.get("id") for f in families]
    if not MIN_IDS.issubset(set(ids)) or len(ids) != len(set(ids)):
        errors.append("FAMILY_LOSS_OR_DUPLICATE")
    if data.get("exceptions") != EXCEPTIONS:
        errors.append("INVALID_SCOPE_EXCEPTION")
    cases_seen = set()
    for family in families:
        if family.get("required") is not True or not family.get("cases"):
            errors.append("MISSING_REQUIRED_FAMILY")
        for case in family.get("cases", []):
            case_id = case.get("id", "")
            if (not re.fullmatch(re.escape(family.get("id", "")) + r"-\d{3}", case_id)
                    or case_id in cases_seen):
                errors.append("DUPLICATE_OR_INVALID_CASE_ID")
            cases_seen.add(case_id)
            if case.get("required") is not True:
                errors.append("REQUIRED_CASE_REMOVED")
            if case.get("yadilab_result") == "VERIFIED_NATIVE":
                if (case.get("standard_oracle") != "PASS"
                        or not case.get("evidence_urls")
                        or not case.get("yadilab_commit_sha")):
                    errors.append("FAKE_NATIVE_VERIFICATION")
            if case.get("pt_binary_result") == "PT_RUN_PASS":
                if (not data.get("binary_baseline", {}).get("version_verified")
                        or not data.get("binary_baseline", {}).get("installed_binary_sha256")
                        or not case.get("pt_build_sha256")
                        or not case.get("evidence_urls")):
                    errors.append("FAKE_PT_COMPARISON")
    if data.get("inventory_complete") is True:
        if (not data.get("binary_baseline", {}).get("version_verified")
                or not data.get("binary_baseline", {}).get("installed_binary_sha256")
                or any(f.get("discovery_complete") is not True for f in families)):
            errors.append("FAKE_COMPLETE_INVENTORY")
    gates = data.get("gate_evidence", {})
    def has_gate(name):
        record = gates.get(name, {})
        return (isinstance(record, dict) and record.get("status") == "PASS"
                and bool(record.get("evidence_urls")))
    if data.get("full_parity_verified") is True:
        if (data.get("inventory_complete") is not True
                or not all(has_gate("G"+str(i)) for i in range(6))
                or any(c.get("pt_binary_result") != "PT_RUN_PASS"
                       or c.get("yadilab_result") != "VERIFIED_NATIVE"
                       or c.get("standard_oracle") != "PASS"
                       for f in families for c in f.get("cases", []))):
            errors.append("FAKE_FULL_PARITY")
    if data.get("exceeds_pt_verified") is True:
        if data.get("full_parity_verified") is not True or not has_gate("G6"):
            errors.append("FAKE_SUPERIORITY")
    if data.get("release_status") == "FULL_PARITY_VERIFIED" and not data.get("full_parity_verified"):
        errors.append("FAKE_RELEASE")
    if data.get("release_status") == "EXCEEDS_PT_VERIFIED" and not data.get("exceeds_pt_verified"):
        errors.append("FAKE_RELEASE")
    return errors

class GovernanceTests(unittest.TestCase):
    def test_required_documents(self):
        for path in DOCS:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_manifest_all_required_unverified(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(check_scope(data), [])
        self.assertGreaterEqual(len(data["families"]), 36)
        self.assertGreaterEqual(sum(len(f["cases"]) for f in data["families"]), 108)
        self.assertEqual(data["release_status"], "NOT_VERIFIED")
        self.assertFalse(data["inventory_complete"])
        self.assertFalse(data["full_parity_verified"])
        self.assertFalse(data["exceeds_pt_verified"])

    def test_mutation_probes_block_fake_claims(self):
        import copy
        original = json.loads(MANIFEST.read_text(encoding="utf-8"))
        edits = [
            (lambda d: d["families"].pop(0), "FAMILY_LOSS_OR_DUPLICATE"),
            (lambda d: d["families"][0].update(required=False), "MISSING_REQUIRED_FAMILY"),
            (lambda d: d["families"][0]["cases"][0].update(required=False), "REQUIRED_CASE_REMOVED"),
            (lambda d: d.update(inventory_complete=True), "FAKE_COMPLETE_INVENTORY"),
            (lambda d: d.update(full_parity_verified=True), "FAKE_FULL_PARITY"),
            (lambda d: d.update(exceeds_pt_verified=True), "FAKE_SUPERIORITY"),
            (lambda d: d["families"][0]["cases"][0].update(yadilab_result="VERIFIED_NATIVE"), "FAKE_NATIVE_VERIFICATION"),
            (lambda d: d["families"][0]["cases"][0].update(pt_binary_result="PT_RUN_PASS"), "FAKE_PT_COMPARISON"),
            (lambda d: d["exceptions"].append("multiuser"), "INVALID_SCOPE_EXCEPTION"),
        ]
        for mutate, error in edits:
            data = copy.deepcopy(original)
            mutate(data)
            with self.subTest(error=error):
                self.assertIn(error, check_scope(data))

    def test_markdown_links_resolve(self):
        for name in DOCS:
            file = ROOT / name
            text = file.read_text(encoding="utf-8")
            for dest in re.findall(r"\]\(([^)\n]+)\)", text):
                dest = dest.strip().split(" ")[0].split("#")[0]
                if not dest or dest.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (file.parent / dest).resolve()
                with self.subTest(file=name, target=dest):
                    self.assertTrue(resolved.is_relative_to(ROOT))
                    self.assertTrue(resolved.is_file())

    def test_master_truth_labels_not_runtime_claims(self):
        s = (ROOT / "MASTERPROMPT.md").read_text(encoding="utf-8")
        for term in ("NOT_IMPLEMENTED", "BLOCKED_LEGAL_OR_SPEC",
                     "UI_REFERENCE_MISSING", "AGENTS.md", "docs/ROADMAP.md"):
            self.assertIn(term, s)
        self.assertIn("NOT_STARTED", (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
