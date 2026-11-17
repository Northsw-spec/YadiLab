import json
import unittest
from pathlib import Path

from network_core.model import topology_trace, validate_project


class DocumentedExampleTests(unittest.TestCase):
    def test_committed_example_matches_exact_model(self):
        fixture = Path(__file__).resolve().parent.parent / 'examples/explicit-three-device-demo.yadilab'
        data = json.loads(fixture.read_text(encoding='utf-8'))
        self.assertEqual(validate_project(data), data)
        self.assertEqual(len(data['nodes']), 3)
        self.assertEqual(len(data['links']), 2)
        self.assertEqual([hop['linkId'] for hop in topology_trace(data, 'pc-1','pc-2')['hops']],
                         ['cable-1','cable-2'])


if __name__ == '__main__':
    unittest.main()
