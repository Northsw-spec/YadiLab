"""Repository hygiene tests: no simulation correctness is certified here."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_IGNORED_PATHS = (
    ".env", ".env.*", ".venv/", "venv/", "node_modules/",
    "dist/", "build/", "__pycache__/", "*.py[cod]",
    "local-private/", "reference-binaries/", "*.pem", "*.key",
)


class RepositoryHygieneTests(unittest.TestCase):
    def test_sensitive_local_artifacts_have_ignore_rules(self):
        path = ROOT / ".gitignore"
        self.assertTrue(path.is_file(), "No .gitignore; local dev artifacts may be committed")
        contents = {s.strip() for s in path.read_text(encoding="utf-8").splitlines()}
        self.assertTrue(set(EXPECTED_IGNORED_PATHS).issubset(contents))

    def test_removing_each_ignore_rule_is_caught(self):
        lines = {s.strip() for s in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
        for item in EXPECTED_IGNORED_PATHS:
            altered = lines - {item}
            with self.subTest(rule=item):
                self.assertFalse(set(EXPECTED_IGNORED_PATHS).issubset(altered))

    def test_readiness_audit_has_truthful_blockers(self):
        audit = (ROOT / "docs/REPO_READINESS_AUDIT.md").read_text(encoding="utf-8")
        for required in ("NOT_IMPLEMENTED", "rulesets", "R1-POC", "BLOCKED",
                         "Packet Tracer", "Legacy", "LICENSE", "G0", "G6"):
            with self.subTest(required=required):
                self.assertIn(required, audit)
        self.assertIn("REPO_READINESS_AUDIT.md",
                      (ROOT / "MASTERPROMPT.md").read_text(encoding="utf-8"))

    def test_governance_workflow_is_not_misdescribed_as_runtime_oracle(self):
        workflow = (ROOT / ".github/workflows/governance.yml").read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertIn("python -m unittest discover", workflow)
        audit = (ROOT / "docs/REPO_READINESS_AUDIT.md").read_text(encoding="utf-8")
        self.assertIn("GOVERNANCE ONLY", audit)
        self.assertIn("branch protection", audit.lower())


if __name__ == "__main__":
    unittest.main()
