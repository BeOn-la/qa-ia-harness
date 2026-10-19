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


    def test_image_link_home(self):
        catalog: list[dict] = []
        image = PageVisualEnriched(
            visual_id="homeico",
            visual_type="image",
            query_refs=(),
            native_refs=(),
            x=20,
            y=0,
            height=45,
            width=50,
            bookmark_ids=(),
            navigation_page_ids=("db20709b2ae5db63007a",),
            action_button_kind=None,
            has_visual_link=True,
            visual_link_kind="page_navigation",
        )
        row = evaluate_visual_contextual(
            visual=image,
            page_display_name="KPI Analysis",
            row_peers=[image],
            page_spec=None,
            contracted=set(),
            expected_on_page=set(),
            strict_contract=False,
            catalog=catalog,
            filter_verdicts={},
            oracle_by_kpi={},
            contract_names={},
            bookmark_labels={},
            bookmark_sections={},
            page_id_to_name={"db20709b2ae5db63007a": "Home"},
        )
        self.assertEqual(row["rol_interpretado"], "navegación a Home")
        self.assertEqual(row["veredicto"], "correcto")

    def test_title_dinamico_no_falla(self):
        card = PageVisualEnriched(
            visual_id="t1",
            visual_type="card",
            query_refs=("DAX Measures.Titulo dinamico",),
            native_refs=("Titulo dinamico",),
            x=0,
            y=0,
            height=40,
            width=80,
            bookmark_ids=(),
            navigation_page_ids=(),
            action_button_kind=None,
            has_visual_link=False,
        )
        row = evaluate_visual_contextual(
            visual=card,
            page_display_name="KPI Analysis",
            row_peers=[card],
            page_spec=None,
            contracted=set(),
            expected_on_page=set(),
            strict_contract=False,
            catalog=[],
            filter_verdicts={},
            oracle_by_kpi={},
            contract_names={},
            bookmark_labels={},
            bookmark_sections={},
            page_id_to_name={},
        )
        self.assertEqual(row["rol_interpretado"], "título dinámico del detalle")
        self.assertEqual(row["veredicto"], "correcto")

    def test_action_back(self):
        btn = PageVisualEnriched(
            visual_id="back1",
            visual_type="actionButton",
            query_refs=(),
            native_refs=(),
            x=70,
            y=0,
            height=45,
            width=70,
            bookmark_ids=(),
            navigation_page_ids=(),
            action_button_kind=None,
            has_visual_link=True,
            visual_link_kind="back",
        )
        row = evaluate_visual_contextual(
            visual=btn,
            page_display_name="KPI Analysis",
            row_peers=[btn],
            page_spec=None,
            contracted=set(),
            expected_on_page=set(),
            strict_contract=False,
            catalog=[],
            filter_verdicts={},
            oracle_by_kpi={},
            contract_names={},
            bookmark_labels={},
            bookmark_sections={},
            page_id_to_name={},
        )
        self.assertEqual(row["rol_interpretado"], "navegación atrás")


if __name__ == "__main__":
    unittest.main()
