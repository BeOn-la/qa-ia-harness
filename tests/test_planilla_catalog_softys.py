import json
import unittest
from pathlib import Path

from qa_harness.planilla_qa import load_planilla_catalog, load_tablero_aliases

SOFTYS_CATALOG = (
    Path(__file__).resolve().parents[2]
    / "beon-pbi"
    / "Softys"
    / "qa"
    / "manual-cases"
    / "planilla-catalog.json"
)


@unittest.skipUnless(SOFTYS_CATALOG.is_file(), "catálogo Softys no presente en workspace")
class TestSoftysPlanillaCatalog(unittest.TestCase):
    def test_catalog_size_and_rows(self):
        catalog = load_planilla_catalog(SOFTYS_CATALOG)
        cases = catalog["cases"]
        self.assertGreaterEqual(len(cases), 200)
        self.assertEqual(cases[0]["sheet_row"], 3)
        self.assertEqual(cases[-1]["sheet_row"], cases[0]["sheet_row"] + len(cases) - 1)

    def test_aliases_file(self):
        aliases = load_tablero_aliases(SOFTYS_CATALOG.parent.parent / "planilla-tablero-aliases.json")
        self.assertIn("base business execution", aliases)


if __name__ == "__main__":
    unittest.main()
