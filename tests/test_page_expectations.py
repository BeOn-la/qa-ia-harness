from __future__ import annotations

import unittest

from qa_harness.page_expectations import audit_page_names, evaluate_scope_on_page


class PageExpectationsTests(unittest.TestCase):
    def test_home_strict_missing_and_extra(self):
        spec = {
            "tipo_hoja": "resumen_contrato",
            "interpretacion": "Resumen",
            "validacion_alcance": "resumen_estricto_contrato",
            "indicadores_esperados": "todos_los_del_contrato",
        }
        contracted = {"a", "b"}
        r = evaluate_scope_on_page(
            spec=spec,
            contracted=contracted,
            shown_kpi_ids={"a", "c"},
            catalog_ids={"a", "b", "c"},
        )
        self.assertEqual(r["veredicto_alcance"], "fallido")
        self.assertEqual(r["indicadores_contrato_faltantes_en_hoja"], ["b"])
        self.assertEqual(r["indicadores_fuera_de_contrato_en_hoja"], ["c"])

    def test_tooltip_no_aplica(self):
        spec = {
            "tipo_hoja": "ayuda_contextual",
            "interpretacion": "Tooltip",
            "validacion_alcance": "no_aplica",
            "indicadores_esperados": [],
        }
        r = evaluate_scope_on_page(
            spec=spec,
            contracted={"a"},
            shown_kpi_ids=set(),
            catalog_ids={"a"},
        )
        self.assertEqual(r["veredicto_alcance"], "no aplica")


    def test_audit_page_names_mismatch(self):
        exp = {"hojas": {"Home": {}, "Otra": {}}}
        r = audit_page_names(exp, ["Home", "Pricing"])
        self.assertFalse(r["nombres_alineados"])
        self.assertEqual(r["hojas_en_informe_sin_definicion"], ["Pricing"])
        self.assertEqual(r["definiciones_sin_hoja_en_informe"], ["Otra"])


if __name__ == "__main__":
    unittest.main()
