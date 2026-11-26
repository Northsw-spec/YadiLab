"""Brand-neutral source contract: policy tests, not a functioning GUI test."""
import ast
import json
import re
import unittest
from pathlib import Path

from core import identity
from core.metadata import public_metadata

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads(
    (ROOT / "docs/requirements/branding_policy.json").read_text(encoding="utf-8")
)
IDENTITY_PATH = ROOT / POLICY["name_declaration_path"]
EXCLUDED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".mypy_cache", ".pytest_cache", "dist", "build",
}
DOC_EXEMPT = {"README.md", "MASTERPROMPT.md", "AGENTS.md"}


def branding_violations(value: str, *, current_name: str, retired: list[str]) -> list[str]:
    """Check literal brand names plus the previous short branded symbol prefix."""
    errors = []
    for term in set(retired + [current_name]):
        if not term:
            continue
        if len(term) > 2:
            if term.casefold() in value.casefold():
                errors.append("BRANDED_SOURCE")
        else:
            # A standalone acronym or camel/snake/kebab-prefixed identifier.
            # Do not outlaw unrelated two-letter substrings inside other words.
            pattern = r"(?<![A-Za-z0-9])(?:%s)(?=$|[^A-Za-z0-9]|[A-Z]|[0-9])" % (
                re.escape(term),)
            if re.search(pattern, value) or re.search(
                pattern.replace(re.escape(term), re.escape(term.lower())), value
            ):
                errors.append("BRANDED_SHORT_SYMBOL")
    return errors


def source_files() -> list[Path]:
    extensions = set(POLICY["source_extensions"])
    selected = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        parts = path.relative_to(ROOT).parts
        if parts[0] == "docs" or parts[0] in EXCLUDED_DIRS:
            continue
        if path.name in DOC_EXEMPT or any(part in EXCLUDED_DIRS for part in parts):
            continue
        selected.append(path)
    return selected


class BrandIdentityTests(unittest.TestCase):
    def test_single_declarative_app_display_name(self):
        source = IDENTITY_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(IDENTITY_PATH))
        assignments = [
            node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name)
                    and target.id == POLICY["name_symbol"]
                    for target in node.targets)
        ]
        self.assertEqual(len(assignments), 1)
        declaration = assignments[0]
        self.assertIsInstance(declaration.value, ast.Constant)
        self.assertIsInstance(declaration.value.value, str)
        name = declaration.value.value
        self.assertTrue(name.strip())
        self.assertEqual(name, name.strip())
        self.assertLessEqual(len(name), 120)
        self.assertFalse(any(ord(c) < 32 for c in name))
        self.assertEqual(name, identity.APP_DISPLAY_NAME)
        self.assertEqual(source.casefold().count(name.casefold()), 1)
        self.assertEqual(
            sum(
                isinstance(n, ast.Constant) and isinstance(n.value, str)
                and n.value == name
                for n in ast.walk(tree)
            ),
            1,
        )

    def test_source_and_file_names_are_brand_neutral(self):
        name = identity.APP_DISPLAY_NAME
        retired = POLICY["banned_app_brand_terms"]
        all_source_files = source_files()
        self.assertIn(IDENTITY_PATH, all_source_files)
        self.assertIn(ROOT / "core/metadata.py", all_source_files)
        for path in all_source_files:
            relative = str(path.relative_to(ROOT))
            with self.subTest(path=relative):
                self.assertEqual(branding_violations(
                    relative, current_name=name, retired=retired
                ), [])
                if path == IDENTITY_PATH:
                    continue
                contents = path.read_text(encoding="utf-8")
                self.assertEqual(branding_violations(
                    contents, current_name=name, retired=retired
                ), [])

    def test_rename_is_one_declarative_value_for_public_metadata(self):
        original = identity.APP_DISPLAY_NAME
        self.assertEqual(public_metadata(), {"appDisplayName": original})
        try:
            identity.APP_DISPLAY_NAME = "Renamed Network Simulator"
            self.assertEqual(public_metadata()["appDisplayName"],
                             "Renamed Network Simulator")
            identity.APP_DISPLAY_NAME = "Next Laboratory"
            self.assertEqual(public_metadata()["appDisplayName"],
                             "Next Laboratory")
        finally:
            identity.APP_DISPLAY_NAME = original
        self.assertEqual(public_metadata(), {"appDisplayName": original})

    def test_negative_brand_literals_and_identifiers(self):
        original = identity.APP_DISPLAY_NAME
        full = POLICY["banned_app_brand_terms"][0]
        short = POLICY["banned_app_brand_terms"][1]
        for sample in (
            'const title = "' + full + '";',
            'class ' + short + 'Engine: pass',
            'const ' + short.lower() + 'Store = {};',
            '.' + short.lower() + '-button {display:none}',
            'src/' + full.lower() + '/engine.py',
            'component class ' + original,
        ):
            with self.subTest(sample=sample):
                self.assertTrue(branding_violations(
                    sample, current_name=original,
                    retired=POLICY["banned_app_brand_terms"],
                ))

    def test_manufacturer_names_are_not_prohibited(self):
        # Domain truth is not the name of the application.
        samples = [
            'class CiscoCliProfile: pass',
            'class JuniperJunosProfile: pass',
            'vendor = "Arista"',
            'model = "Catalyst 9300"',
            'device_vendor = "MikroTik"',
            'class VendorAdapter: pass',
            'class CoreEngine: pass',
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(branding_violations(
                    sample, current_name=identity.APP_DISPLAY_NAME,
                    retired=POLICY["banned_app_brand_terms"],
                ), [])

    def test_metadata_contract_is_advertised_without_fake_runtime_claim(self):
        self.assertEqual(POLICY["name_symbol"], "APP_DISPLAY_NAME")
        self.assertEqual(POLICY["name_declaration_path"], "core/identity.py")
        self.assertEqual(POLICY["metadata_provider"], "core/metadata.py")
        self.assertEqual(POLICY["future_bootstrap_route"], "GET /api/meta")
        self.assertEqual(POLICY["public_response_key"], "appDisplayName")
        docs = (ROOT / "docs/BRAND_IDENTITY_CONTRACT.md").read_text(encoding="utf-8")
        self.assertIn("NOT_IMPLEMENTED", docs)
        self.assertIn("Cisco", docs)
        self.assertIn("Juniper", docs)


if __name__ == "__main__":
    unittest.main()
