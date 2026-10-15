import json
import unittest
from pathlib import Path

from qa_harness.planilla_bindings import (
    load_planilla_bindings,
    resolve_planilla_binding,
)
from qa_harness.planilla_qa import build_automation_index, resolve_case_binding

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SOFTYS_BINDINGS = (
    Path(__file__).resolve().parents[2].parent
    / "beon-pbi"
    / "Softys"
    / "qa"
    / "planilla-harness-bindings.json"
)


class TestPlanillaBindings(unittest.TestCase):
    def test_filter_rule_etailer(self):
        doc = {
            "reglas": [
                {
                    "id": "t1",
                    "match": {"caso_contains": "validar filtro de etailer / store"},
                    "binding": {"capa": "filtros", "filter_id": "etailer_tienda"},
                    "cobertura_harness": "harness",
                }
            ]
        }
        case = {
            "caso_de_prueba": "Validar filtro de eTailer / Store",
            "tablero": "Home",
            "tipo_prueba": "Filtros",
        }
        binding, meta = resolve_planilla_binding(case, doc)
        self.assertEqual(binding["filter_id"], "etailer_tienda")
        self.assertEqual(meta["origen"], "planilla-harness-bindings")

    def test_manual_rule_no_binding(self):
        doc = {
            "reglas": [
                {
                    "id": "m1",
                    "match": {"caso_contains": "date"},
                    "binding": None,
                    "cobertura_harness": "manual",
                }
            ]
        }
        case = {
            "caso_de_prueba": "Validar filtro de Date",
            "tablero": "Home",
            "tipo_prueba": "Filtros",
        }
        binding, meta = resolve_planilla_binding(case, doc)
        self.assertIsNone(binding)
        self.assertEqual(meta["cobertura_harness"], "manual")

    def test_resolve_case_binding_uses_bindings_file(self):
        if not SOFTYS_BINDINGS.is_file():
            self.skipTest("planilla-harness-bindings.json no presente")
        doc = load_planilla_bindings(SOFTYS_BINDINGS)
        case = {
            "caso_de_prueba": "Validar KPI Assortment",
            "tablero": "Home",
            "tipo_prueba": "KPI/Calculos",
        }
        binding = resolve_case_binding(case, {}, planilla_bindings=doc)
        self.assertEqual(binding["kpi_id"], "assortment")


if __name__ == "__main__":
    unittest.main()
