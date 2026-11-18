"""Keep the browser entrypoint's small native ES module graph acyclic."""
from pathlib import Path
import re
import unittest


WEB = Path(__file__).resolve().parent.parent / "web"
IMPORT = re.compile(r"(?m)^import\s+[^\n]+?\s+from\s+['\"]([^'\"]+)['\"]\s*;")


class WebImportGraphTests(unittest.TestCase):
    def test_entrypoint_imports_exist_and_have_no_cycles(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        scripts = re.findall(r'<script\s+type="module"\s+src="([^"]+)"', html)
        self.assertEqual(scripts, ["/app.js"])

        graph = {}
        for source in WEB.rglob("*.js"):
            targets = []
            for specifier in IMPORT.findall(source.read_text(encoding="utf-8")):
                self.assertTrue(specifier.startswith("."), (source, specifier))
                target = (source.parent / specifier).resolve()
                self.assertTrue(target.is_relative_to(WEB.resolve()), (source, target))
                self.assertTrue(target.is_file(), (source, target))
                targets.append(target)
            graph[source.resolve()] = targets

        visited, active = set(), set()

        def visit(source):
            self.assertNotIn(source, active, f"circular ES import through {source}")
            if source in visited:
                return
            active.add(source)
            for target in graph[source]:
                visit(target)
            active.remove(source)
            visited.add(source)

        visit((WEB / "app.js").resolve())
        self.assertEqual(visited, set(graph), "orphan JavaScript module outside entrypoint graph")


if __name__ == "__main__":
    unittest.main()
