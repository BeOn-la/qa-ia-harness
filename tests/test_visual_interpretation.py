from __future__ import annotations

import unittest

from qa_harness.visual_interpretation import (
    PageVisualEnriched,
    effective_dax_measures,
    evaluate_visual_contextual,
    kpi_id_from_bookmark_label,
)


class VisualInterpretationTests(unittest.TestCase):
    def test_effective_measures_kpi_title_alias(self):
        v = PageVisualEnriched(
            visual_id="x",
            visual_type="card",
            query_refs=("DAX Measures.Kpi Title",),
            native_refs=("Title Compliance",),
            x=0,
            y=0,
            height=40,
            width=80,
            bookmark_ids=(),
            navigation_page_ids=(),
            action_button_kind=None,
            has_visual_link=False,
        )
        self.assertEqual(effective_dax_measures(v), ["Title Compliance"])

    def test_bookmark_maps_assortment_kpi(self):
        self.assertEqual(kpi_id_from_bookmark_label("Assortment KPI"), "assortment")

    def test_shape_row_matches_card(self):
        catalog = [
            {
                "kpi_id": "assortment",
                "home_label": "Assortment",
                "dax_measure": "Assortment",
            }
        ]
        card = PageVisualEnriched(
            visual_id="card1",
            visual_type="card",
            query_refs=("DAX Measures.Assortment",),
            native_refs=("Assortment",),
            x=200,
            y=280,
            height=50,
            width=100,
            bookmark_ids=(),
            navigation_page_ids=(),
            action_button_kind=None,
            has_visual_link=False,
        )
        shape = PageVisualEnriched(
            visual_id="sh1",
            visual_type="shape",
            query_refs=(),
            native_refs=(),
            x=100,
            y=275,
            height=60,
            width=80,
            bookmark_ids=("bm1",),
            navigation_page_ids=(),
            action_button_kind=None,
            has_visual_link=True,
        )
        band = [shape, card]
        row = evaluate_visual_contextual(
            visual=shape,
            page_display_name="Home",
            row_peers=band,
            page_spec={"validacion_alcance": "resumen_estricto_contrato"},
            contracted={"assortment"},
            expected_on_page={"assortment"},
            strict_contract=True,
            catalog=catalog,
            filter_verdicts={},
            oracle_by_kpi={},
            contract_names={"assortment": "Listed"},
            bookmark_labels={"bm1": "Assortment KPI"},
            bookmark_sections={"bm1": "32d6d7e07d5a70d2e4ab"},
            page_id_to_name={"32d6d7e07d5a70d2e4ab": "KPI Analysis"},
        )
        self.assertEqual(row["veredicto"], "correcto")
        self.assertIn("Listed", row["lectura_qa"])


if __name__ == "__main__":
    unittest.main()
