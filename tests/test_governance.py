"""Governance tests for a PLANNED product. NOT protocol implementation tests."""
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
    "docs/LEGACY_UI_FIDELITY_CONTRACT.md", "docs/REPO_READINESS_AUDIT.md",
    "docs/PT_DOCUMENTATION_BASELINE_POLICY.md",
]

# These fields are obsolete as mandatory release predicates. Voluntary direct
# comparison evidence may be recorded outside the required source catalog.
OBSOLETE_BINARY_FIELDS = {"binary_baseline", "pt_binary_result", "pt_build_sha256"}


def check_scope(data):
    errors = []
    if OBSOLETE_BINARY_FIELDS.intersection(data):
        errors.append("LEGACY_BINARY_GATE")
    documentation = data.get("documentation_baseline", {})
    if not isinstance(documentation, dict):
        documentation = {}
        errors.append("MISSING_DOCUMENTATION_BASELINE")
    if not str(documentation.get("documentation_entry", "")).startswith("https://"):
        errors.append("MISSING_DOCUMENTATION_ENTRY")
    if data.get("exceptions") != EXCEPTIONS:
        errors.append("INVALID_SCOPE_EXCEPTION")
    families = data.get("families", [])
    ids = [f.get("id") for f in families]
    if not MIN_IDS.issubset(set(ids)) or len(ids) != len(set(ids)):
        errors.append("FAMILY_LOSS_OR_DUPLICATE")
    case_ids = set()
    for family in families:
        if family.get("required") is not True or not family.get("cases"):
            errors.append("MISSING_REQUIRED_FAMILY")
        if not str(family.get("source_category", "")).startswith("https://"):
            errors.append("MISSING_FAMILY_SOURCE")
        for case in family.get("cases", []):
            if OBSOLETE_BINARY_FIELDS.intersection(case):
                errors.append("LEGACY_BINARY_GATE")
            cid = case.get("id", "")
            if not isinstance(cid, str) or not re.fullmatch(
                    re.escape(family.get("id", "")) + r"-\d{3}", cid
            ) or cid in case_ids:
                errors.append("DUPLICATE_OR_INVALID_CASE_ID")
            case_ids.add(cid)
            if case.get("required") is not True:
                errors.append("REQUIRED_CASE_REMOVED")
            status = case.get("source_status")
            if status not in {"DOC_CANDIDATE", "DOC_VERIFIED", "SOURCE_UNCERTAIN"}:
                errors.append("MISSING_SOURCE_STATUS")
            if status == "DOC_VERIFIED" and (
                not case.get("source_evidence")
                or not case.get("source_revision")
                or case.get("source_revision") == "UNVERIFIED"
            ):
                errors.append("FAKE_DOCUMENTATION_VERIFICATION")
            if case.get("implementation_status") == "VERIFIED_NATIVE":
                if (case.get("standard_oracle") != "PASS"
                        or not case.get("evidence_urls")
                        or not case.get("implementation_commit_sha")):
                    errors.append("FAKE_NATIVE_VERIFICATION")
    if data.get("inventory_complete") is True:
        if (documentation.get("inventory_audit_status") != "COMPLETE"
                or not documentation.get("inventory_audit_evidence_urls")
                or any(f.get("discovery_complete") is not True for f in families)
                or any(c.get("source_status") != "DOC_VERIFIED"
                       for f in families for c in f.get("cases", []))):
            errors.append("FAKE_COMPLETE_INVENTORY")
    gates = data.get("gate_evidence", {})
    def passed(name):
        record = gates.get(name, {})
        return (isinstance(record, dict) and record.get("status") == "PASS"
                and bool(record.get("evidence_urls")))
    if data.get("documented_scope_verified") is True:
        if (data.get("inventory_complete") is not True
                or not all(passed("G" + str(i)) for i in range(6))
                or any(c.get("source_status") != "DOC_VERIFIED"
                       or c.get("implementation_status") != "VERIFIED_NATIVE"
                       or c.get("standard_oracle") != "PASS"
                       for f in families for c in f.get("cases", []))):
            errors.append("FAKE_DOCUMENTED_SCOPE_VERIFICATION")
    if data.get("exceeds_documented_scope_verified") is True:
        if data.get("documented_scope_verified") is not True or not passed("G6"):
            errors.append("FAKE_SUPERIORITY")
    if data.get("release_status") == "DOCUMENTED_PT_SCOPE_VERIFIED":
        if data.get("documented_scope_verified") is not True:
            errors.append("FAKE_RELEASE")
    if data.get("release_status") == "EXCEEDS_DOCUMENTED_PT_SCOPE":
        if data.get("exceeds_documented_scope_verified") is not True:
            errors.append("FAKE_RELEASE")
    if data.get("release_status") in ("FULL_PARITY_VERIFIED", "EXCEEDS_PT_VERIFIED"):
        errors.append("AMBIGUOUS_BINARY_PARITY_CLAIM")
    return errors


class GovernanceTests(unittest.TestCase):
    def test_required_documents(self):
        for path in DOCS:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_manifest_has_source_not_binary_evidence(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(check_scope(data), [])
        self.assertGreaterEqual(len(data["families"]), 36)
        self.assertGreaterEqual(sum(len(f["cases"]) for f in data["families"]), 108)
        self.assertNotIn("binary_baseline", data)
        self.assertIn("documentation_baseline", data)
        self.assertTrue(data["documentation_baseline"]["documentation_entry"].startswith("https://"))
        for family in data["families"]:
            for case in family["cases"]:
                self.assertIn("source_status", case)
                self.assertIn("source_evidence", case)
                self.assertIn("source_revision", case)
                self.assertFalse(OBSOLETE_BINARY_FIELDS.intersection(case))

    def test_mutation_probes_block_fake_claims(self):
        import copy
        original = json.loads(MANIFEST.read_text(encoding="utf-8"))
        edits = [
            (lambda d: d["families"].pop(0), "FAMILY_LOSS_OR_DUPLICATE"),
            (lambda d: d["families"][0].update(required=False), "MISSING_REQUIRED_FAMILY"),
            (lambda d: d["families"][0]["cases"][0].update(required=False), "REQUIRED_CASE_REMOVED"),
            (lambda d: d.update(inventory_complete=True), "FAKE_COMPLETE_INVENTORY"),
            (lambda d: d.update(documented_scope_verified=True), "FAKE_DOCUMENTED_SCOPE_VERIFICATION"),
            (lambda d: d.update(exceeds_documented_scope_verified=True), "FAKE_SUPERIORITY"),
            (lambda d: d["families"][0]["cases"][0].update(implementation_status="VERIFIED_NATIVE"), "FAKE_NATIVE_VERIFICATION"),
            (lambda d: d["families"][0]["cases"][0].update(source_status="DOC_VERIFIED"), "FAKE_DOCUMENTATION_VERIFICATION"),
            (lambda d: d["families"][0]["cases"][0].update(pt_binary_result="PT_RUN_PASS"), "LEGACY_BINARY_GATE"),
            (lambda d: d.update(binary_baseline={"version_verified": True}), "LEGACY_BINARY_GATE"),
            (lambda d: d["exceptions"].append("multiuser"), "INVALID_SCOPE_EXCEPTION"),
            (lambda d: d.update(release_status="FULL_PARITY_VERIFIED"), "AMBIGUOUS_BINARY_PARITY_CLAIM"),
        ]
        for mutate, expected in edits:
            data = copy.deepcopy(original)
            mutate(data)
            with self.subTest(expected=expected):
                self.assertIn(expected, check_scope(data))

    def test_documentation_policy_is_not_an_installed_binary_requirement(self):
        document = (ROOT / "docs/PT_DOCUMENTATION_BASELINE_POLICY.md").read_text(encoding="utf-8")
        self.assertIn("INTE NÖDVÄNDIGT", document)
        self.assertIn("DOC_VERIFIED", document)
        self.assertIn("VERIFIED_NATIVE", document)
        release = (ROOT / "docs/RELEASE_GATES.md").read_text(encoding="utf-8")
        self.assertIn("FRIVILLIG", release)
        self.assertIn("DOCUMENTED_PT_SCOPE_VERIFIED", release)
        self.assertIn("EXCEEDS_DOCUMENTED_PT_SCOPE", release)
        self.assertIn("PT_DOCUMENTATION_BASELINE_POLICY.md",
                      (ROOT / "MASTERPROMPT.md").read_text(encoding="utf-8"))

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
        self.assertEqual(ui["reference_url"].split("/tree/")[0],
                         "https://github.com/" + ui["reference_repository"])
        self.assertEqual(ui["reference_commit_sha"], baseline)
        self.assertIn(ui["reference_status"], (
            "SOURCE_INSPECTED_RUNTIME_SCREENSHOTS_NOT_CAPTURED",
            "SOURCE_AND_RENDERED_BASELINE_VERIFIED",
        ))
        # These flags may become True in future code PRs, but only with evidence.
        if ui["visual_parity_verified"]:
            self.assertTrue(ui.get("legacy_golden_evidence"))
            self.assertTrue(all(c.get("visual_evidence") for c in ui["cases"]))
        if ui["interaction_parity_verified"]:
            self.assertTrue(all(c.get("behavioral_evidence") for c in ui["cases"]))
        if ui["full_legacy_ui_parity_verified"]:
            self.assertTrue(ui["visual_parity_verified"])
            self.assertTrue(ui["interaction_parity_verified"])
            self.assertTrue(ui["inventory_complete"])
            self.assertTrue(all(c.get("review_status") == "UI_PARITY_VERIFIED" for c in ui["cases"]))
        self.assertGreaterEqual(len(ui["cases"]), 55)
        ids = [x["id"] for x in ui["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        for required in (f"UI-{i:03d}" for i in range(1, 56)):
            self.assertIn(required, ids)
        for item in ui["cases"]:
            self.assertTrue(item["required"])
            self.assertEqual(item["reference_sha"], baseline)
            self.assertTrue(item["source_inspected"])
            self.assertIsInstance(item["new_implementation_status"], str)
            self.assertIsInstance(item["rendered_golden_status"], str)
            self.assertIsInstance(item["review_status"], str)
            if item["review_status"] == "UI_PARITY_VERIFIED":
                self.assertTrue(item.get("behavioral_evidence"))
                self.assertTrue(item.get("visual_evidence"))
                self.assertNotEqual(item["new_implementation_status"], "NOT_IMPLEMENTED")
                self.assertNotEqual(item["rendered_golden_status"], "NOT_CAPTURED")
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
            if payload.get("visual_parity_verified") is True:
                if (not payload.get("legacy_golden_evidence")
                        or any(not x.get("visual_evidence") for x in cases)):
                    problems.append("FALSE_VISUAL_PARITY")
            if payload.get("interaction_parity_verified") is True:
                if any(not x.get("behavioral_evidence") for x in cases):
                    problems.append("FALSE_INTERACTION_PARITY")
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
        bad = copy.deepcopy(ui)
        bad["visual_parity_verified"] = True
        self.assertIn("FALSE_VISUAL_PARITY", errors(bad))
        bad = copy.deepcopy(ui)
        bad["interaction_parity_verified"] = True
        self.assertIn("FALSE_INTERACTION_PARITY", errors(bad))


if __name__ == "__main__":
    unittest.main()
