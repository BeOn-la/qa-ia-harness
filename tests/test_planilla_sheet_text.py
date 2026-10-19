import unittest

from qa_harness.planilla_qa import (
    _normalizar_tipo_prueba_catalogo,
    _observaciones_para_desarrollo,
    _sanitizar_texto_planilla,
)


class TestPlanillaSheetText(unittest.TestCase):
    def test_sanitize_removes_harness_paths(self):
        raw = (
            "Ver test-evidence/visuales-por-hoja y scope-kpis.json; "
            "identificador interno de QA: price-check-compliance"
        )
        out = _sanitizar_texto_planilla(raw)
        self.assertNotIn("test-evidence", out.lower())
        self.assertNotIn("scope-kpis", out.lower())
        self.assertNotIn("price-check", out.lower())

    def test_tipo_prueba_only_capsules(self):
        self.assertEqual(_normalizar_tipo_prueba_catalogo("Validar ícono de Home", capa="visuales"), "Visuales")
        self.assertEqual(_normalizar_tipo_prueba_catalogo("KPI/Calculos"), "KPI/Calculos")

    def test_observacion_visual_no_vuelca_filtro_de_pagina(self):
        case = {
            "caso_de_prueba": "Validar selector de All / In Stock / Listed",
            "tablero": "Home",
        }
        auto = {
            "capa": "visuales",
            "detalle": (
                "slicer usa Mock_CategoryGroup_Category; faltan en SQL: Pañales / Baby Wipes, "
                "Pañales / Diapers, Tissue / Cleaning Cloths"
            ),
            "lectura_qa": "Home · filtro operativo (Filtro)",
        }
        obs = _observaciones_para_desarrollo(case, auto, {})
        self.assertIn("Validar selector", obs)
        self.assertNotIn("Mock_CategoryGroup", obs)
        self.assertNotIn("Baby Wipes", obs)

    def test_observacion_filtro_resumida(self):
        case = {"caso_de_prueba": "Validar filtro de Category Group / Category", "tablero": "Home"}
        auto = {
            "capa": "filtros",
            "nombre_filtro": "Category group / Category",
            "detalle": (
                "slicer usa Mock_CategoryGroup_Category; "
                "Faltan opciones respecto al universo acordado: A / B, C / D, E / F"
            ),
        }
        obs = _observaciones_para_desarrollo(case, auto, {})
        self.assertIn("Faltan 3 opción", obs)
        self.assertNotIn("A / B", obs)


if __name__ == "__main__":
    unittest.main()
