from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qa_harness.report_visuals import (
    evaluate_visual,
    list_visuals_on_page,
    PageVisual,
)


class ReportVisualsTests(unittest.TestCase):
    def test_list_visuals_minimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vid = root / "definition" / "pages" / "p1" / "visuals" / "abc123"
            vid.mkdir(parents=True)
            (vid / "visual.json").write_text(
                json.dumps(
                    {
                        "visual": {
                            "visualType": "card",
                            "query": {
                                "queryState": {
                                    "Values": {
                                        "projections": [
                                            {"queryRef": "DAX Measures.Assortment"}
                                        ]
                                    }
                                }
                            },
                        },
                        "name": "abc123",
                    }
                ),
                encoding="utf-8",
            )
            rows = list_visuals_on_page(root, "p1")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].visual_type, "card")

    def test_decorative_no_aplica(self):
        v = PageVisual("x", "shape", ())
        row = evaluate_visual(
            visual=v,
            page_spec=None,
            contracted={"a"},
            expected_on_page={"a"},
            strict_contract=True,
            catalog=[],
            catalog_ids=set(),
            filter_verdicts={},
            oracle_by_kpi={},
        )
        self.assertEqual(row["veredicto"], "no aplica")


if __name__ == "__main__":
    unittest.main()
