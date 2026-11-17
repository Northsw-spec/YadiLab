"""Regression: presentation branding comes from exactly one configuration value."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from network_core import config

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "network_core" / "config.py"
TEXT_SUFFIXES = {".py", ".js", ".html", ".css", ".md", ".json", ".yml", ".yaml", ".csv"}


class NamingContractTests(unittest.TestCase):
    def test_single_declarative_display_name(self):
        self.assertIs(type(config.APP_NAME), str)
        self.assertTrue(config.APP_NAME.strip())
        declaration = re.compile(r"^\s*APP_NAME\s*=", re.MULTILINE)
        config_text = CONFIG_PATH.read_text(encoding="utf-8")
        self.assertEqual(len(declaration.findall(config_text)), 1)
        for file in ROOT.rglob("*"):
            if not self._source(file) or file == CONFIG_PATH:
                continue
            content = file.read_text(encoding="utf-8")
            self.assertNotRegex(content, declaration,
                                f"Unexpected product name declaration: {file.relative_to(ROOT)}")
            self.assertNotIn(config.APP_NAME, content,
                             f"Hardcoded current display name: {file.relative_to(ROOT)}")

    def test_no_retired_brand_remnants(self):
        # Assemble the former identifier so tests do not reintroduce the
        # retired brand as an apparent literal in the source tree.
        former = "".join(("ya", "di", "lab"))
        name = re.compile(r"\b" + former + r"(?:[-_ ]+[a-z0-9]+)?\b", re.IGNORECASE)
        extension = re.compile(r"\." + former + r"\b", re.IGNORECASE)
        for file in ROOT.rglob("*"):
            if not self._source(file):
                continue
            relative = file.relative_to(ROOT)
            self.assertIsNone(name.search(extension.sub("", str(relative))),
                              f"Retired brand in path: {relative}")
            content = extension.sub("", file.read_text(encoding="utf-8"))
            self.assertIsNone(name.search(content),
                              f"Retired brand in file: {relative}")

    @staticmethod
    def _source(file: Path) -> bool:
        if not file.is_file() or any(part in {".git", "__pycache__", ".pytest_cache", "node_modules"}
                                      for part in file.parts):
            return False
        return file.suffix in TEXT_SUFFIXES or file.name in {"AGENTS.md", "README.md", ".gitignore"}


if __name__ == "__main__":
    unittest.main()
