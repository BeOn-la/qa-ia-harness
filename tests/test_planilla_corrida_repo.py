from __future__ import annotations

import unittest

from qa_harness.planilla_corrida_repo import (
    dedupe_visual_cases_for_planilla,
    filter_kpi_cases_for_planilla,
    sort_visual_cases_for_planilla,
)


class PlanillaCorridaRepoTests(unittest.TestCase):
    def test_dedupe_click_kpi_misma_hoja(self):
        casos = [
            {
                "orden_en_hoja": 4,
                "rol_interpretado": "zona clicable detalle KPI",
                "identificador_indicador": "assortment",
                "nombre_caso": "Home · zona A",
            },
            {
                "orden_en_hoja": 8,
                "rol_interpretado": "zona clicable detalle KPI",
                "identificador_indicador": "assortment",
                "nombre_caso": "Home · zona B",
            },
        ]
        out = dedupe_visual_cases_for_planilla(casos, "Home")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["orden_en_hoja"], 4)

    def test_sort_ux_al_final(self):
        casos = [
            {"orden_en_hoja": 5, "rol_interpretado": "elemento de diseño"},
            {"orden_en_hoja": 3, "rol_interpretado": "tarjeta o gráfico KPI"},
        ]
        ordered = sort_visual_cases_for_planilla(casos)
        self.assertEqual(ordered[-1]["rol_interpretado"], "elemento de diseño")

    def test_omite_kpi_fuera_de_subconjunto(self):
        casos = [
            {"tipo_caso": "alcance contractual en la hoja"},
            {
                "tipo_caso": "oráculo sql mensual del indicador",
                "identificador_indicador": "title-compliance",
            },
            {
                "tipo_caso": "oráculo sql mensual del indicador",
                "identificador_indicador": "share-of-search",
            },
        ]
        out = filter_kpi_cases_for_planilla(
            casos,
            expected_on_page={"assortment", "stock-compliance"},
            contracted={"assortment", "share-of-search", "title-compliance"},
        )
        kids = [c.get("identificador_indicador") for c in out if "oráculo" in (c.get("tipo_caso") or "")]
        self.assertNotIn("share-of-search", kids)
        self.assertNotIn("title-compliance", kids)


if __name__ == "__main__":
    unittest.main()
