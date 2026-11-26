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
    "docs/LEGACY_UI_FIDELITY_CONTRACT.md",
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
                     "UI_REFERENCE_SOURCE_AVAILABLE", "AGENTS.md", "docs/ROADMAP.md"):
            self.assertIn(term, s)
        self.assertIn("NOT_STARTED", (ROOT / "docs/ROADMAP.md").read_text(encoding="utf-8"))


    def test_legacy_ui_baseline_is_pinned_and_required(self):
        ui = json.loads((ROOT / "docs/requirements/legacy_ui_manifest.json").read_text(encoding="utf-8"))
        baseline = "aac82926ced3dbf4cac09242530762ac3da1fe80"
        self.assertEqual(ui["reference_repository"], "Northsw-spec/YadiLab_legacy")
        self.assertEqual(ui["reference_commit_sha"], baseline)
        self.assertEqual(ui["reference_status"], "SOURCE_INSPECTED_RUNTIME_SCREENSHOTS_NOT_CAPTURED")
        self.assertFalse(ui["visual_parity_verified"])
        self.assertFalse(ui["interaction_parity_verified"])
        self.assertFalse(ui["full_legacy_ui_parity_verified"])
        self.assertFalse(ui["inventory_complete"])
        self.assertGreaterEqual(len(ui["cases"]), 55)
        ids = [x["id"] for x in ui["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        for required in (f"UI-{i:03d}" for i in range(1, 56)):
            self.assertIn(required, ids)
        for item in ui["cases"]:
            self.assertTrue(item["required"])
            self.assertEqual(item["reference_sha"], baseline)
            self.assertTrue(item["source_inspected"])
            self.assertEqual(item["new_implementation_status"], "NOT_IMPLEMENTED")
            self.assertEqual(item["rendered_golden_status"], "NOT_CAPTURED")
            self.assertEqual(item["review_status"], "NOT_VERIFIED")
            self.assertTrue(item["source_path"].startswith(("web/", "docs/", "tests/")))
        contract = (ROOT / "docs/LEGACY_UI_FIDELITY_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn(baseline, contract)
        self.assertIn("fullbreddscanvas", contract.lower())
        self.assertIn("UI_PARITY_NOT_VERIFIED", contract)
        self.assertIn("docs/LEGACY_UI_FIDELITY_CONTRACT.md", (ROOT / "MASTERPROMPT.md").read_text(encoding="utf-8"))

    def test_legacy_ui_negative_false_parity_mutations(self):
        import copy
        ui = json.loads((ROOT / "docs/requirements/legacy_ui_manifest.json").read_text(encoding="utf-8"))
        def errors(payload):
            problems = []
            if payload["reference_commit_sha"] != "aac82926ced3dbf4cac09242530762ac3da1fe80":
                problems.append("PINNED_SOURCE_SHA_CHANGED")
            cases = payload.get("cases", [])
            if any(x.get("required") is not True for x in cases):
                problems.append("UI_SCOPE_DEMOTED")
            if not {f"UI-{i:03d}" for i in range(1, 56)}.issubset({x.get("id") for x in cases}):
                problems.append("UI_SEED_REMOVED")
            if payload.get("full_legacy_ui_parity_verified") is True:
                if (not payload.get("visual_parity_verified")
                        or not payload.get("interaction_parity_verified")
                        or not payload.get("inventory_complete")
                        or any(x.get("review_status") != "UI_PARITY_VERIFIED"
                               or not x.get("behavioral_evidence")
                               or not x.get("visual_evidence")
                               for x in cases)):
                    problems.append("FALSE_UI_PARITY")
            return problems
        self.assertEqual(errors(ui), [])
        bad = copy.deepcopy(ui)
        bad["reference_commit_sha"] = "main"
        self.assertIn("PINNED_SOURCE_SHA_CHANGED", errors(bad))
        bad = copy.deepcopy(ui)
        bad["cases"][0]["required"] = False
        self.assertIn("UI_SCOPE_DEMOTED", errors(bad))
        bad = copy.deepcopy(ui)
        bad["cases"].pop()
        self.assertIn("UI_SEED_REMOVED", errors(bad))
        bad = copy.deepcopy(ui)
        bad["full_legacy_ui_parity_verified"] = True
        self.assertIn("FALSE_UI_PARITY", errors(bad))


if __name__ == "__main__":
    unittest.main()
