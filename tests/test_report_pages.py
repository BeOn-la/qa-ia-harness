from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qa_harness.common import ContractError
from qa_harness.kpi_catalog import load_kpi_catalog
from qa_harness.report_pages import (
    kpi_shown_on_page,
    list_report_pages,
    select_pages,
)


class ReportPagesTests(unittest.TestCase):
    def test_list_and_select_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pages_dir = root / "definition" / "pages"
            pages_dir.mkdir(parents=True)
            (pages_dir / "pages.json").write_text(
                json.dumps({"pageOrder": ["aaa", "bbb"]}),
                encoding="utf-8",
            )
            for pid, name in (("aaa", "Home"), ("bbb", "Pricing")):
                pdir = pages_dir / pid
                pdir.mkdir(parents=True)
                (pdir / "page.json").write_text(
                    json.dumps({"displayName": name}),
                    encoding="utf-8",
                )
            listed = list_report_pages(root)
            self.assertEqual([p.display_name for p in listed], ["Home", "Pricing"])
            one = select_pages(listed, "Pricing")
            self.assertEqual(len(one), 1)
            self.assertRaises(ContractError, select_pages, listed, "No existe")

    def test_kpi_shown_matches_variants(self):
        entry = {"dax_measure": "Assortment", "home_label": "Assortment"}
        self.assertTrue(kpi_shown_on_page(entry, {"Assortment vs Target"}))
        self.assertFalse(kpi_shown_on_page(entry, {"Stock Compliance"}))

    def test_load_kpi_catalog_minimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "kpi-catalog.yml"
            path.write_text(
                "kpis:\n"
                "  - kpi_id: demo\n"
                "    home_label: Demo\n"
                "    dax_measure: Demo Measure\n",
                encoding="utf-8",
            )
            rows = load_kpi_catalog(path)
            self.assertEqual(rows[0]["kpi_id"], "demo")


if __name__ == "__main__":
    unittest.main()
