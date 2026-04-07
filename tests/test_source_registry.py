import unittest
from pathlib import Path

from ainews.source_registry import SourceRegistry


class SourceRegistryContractTestCase(unittest.TestCase):
    def test_default_sources_file_loads_and_keeps_core_mix(self) -> None:
        source_file = Path(__file__).resolve().parents[1] / "src" / "ainews" / "sources.default.json"
        registry = SourceRegistry(source_file)

        sources = registry.list_sources()

        self.assertGreaterEqual(len(sources), 8)
        self.assertEqual(len({source.id for source in sources}), len(sources))
        self.assertEqual(len({source.url for source in sources}), len(sources))
        self.assertIn("domestic", {source.region for source in sources})
        self.assertIn("international", {source.region for source in sources})

        for source in sources:
            self.assertTrue(source.id)
            self.assertTrue(source.name)
            self.assertTrue(source.url.startswith("http"))
            self.assertIn(source.kind, {"rss", "atom"})
            self.assertGreater(source.max_items, 0)
            self.assertLessEqual(source.max_items, 100)


if __name__ == "__main__":
    unittest.main()
