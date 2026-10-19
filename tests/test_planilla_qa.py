import json
import unittest
from pathlib import Path

from qa_harness.planilla_qa import (
    export_planilla,
    load_planilla_catalog,
    parse_catalog_csv,
    veredicto_to_estado,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestPlanillaQa(unittest.TestCase):
    def test_veredicto_to_estado(self):
        self.assertEqual(veredicto_to_estado("correcto"), "Aprobado")
        self.assertEqual(veredicto_to_estado("fallido"), "Error")

    def test_parse_catalog_csv(self):
        text = (FIXTURES / "planilla_catalog_sample.csv").read_text(encoding="utf-8")
        catalog = parse_catalog_csv(text)
        self.assertEqual(len(catalog["cases"]), 3)
        self.assertEqual(catalog["cases"][0]["automation"]["filter_id"], "etailer_tienda")

    def test_export_recorrida_maps_kpi_and_filtro(self):
        catalog = parse_catalog_csv(
            (FIXTURES / "planilla_catalog_sample.csv").read_text(encoding="utf-8")
        )
        kpi = {
            "hojas": [
                {
                    "nombre_hoja": "Home",
                    "casos_de_prueba": [
                        {
                            "tipo_caso": "oráculo sql mensual del indicador",
                            "identificador_indicador": "assortment",
                            "se_muestra_en_esta_hoja": True,
                            "veredicto_comparacion_sql": "correcto",
                            "detalle": "ok",
                        }
                    ],
                }
            ]
        }
        filtros = {
            "hojas": [
                {
                    "nombre_hoja": "Home",
                    "casos_de_prueba": [
                        {
                            "identificador_filtro": "etailer_tienda",
                            "se_muestra_en_esta_hoja": True,
                            "veredicto_contrato": "fallido",
                            "detalle": "diff",
                        }
                    ],
                }
            ]
        }
        out = export_planilla(
            catalog=catalog,
            kpi=kpi,
            filtros=filtros,
            modo="recorrida",
            revision_index=1,
            hoja_planilla="Revision test",
        )
        by_caso = {f["catalog"]["caso_de_prueba"]: f for f in out["filas"]}
        self.assertEqual(
            by_caso["Validar KPI Assortment"]["revision"]["estado"], "Aprobado"
        )
        filtro = by_caso["Validar filtro de eTailer / Store"]["revision"]
        self.assertEqual(filtro["estado"], "Error")
        self.assertEqual(filtro["tipo_error"], "Datos")
        self.assertEqual(filtro["prioridad"], "Alta")
        self.assertEqual(filtro["controlado_por"], "Motrel Gabriel")
        self.assertIn("validar filtro de etailer", filtro["observaciones_qa"].lower())
        self.assertIn("diff", filtro["observaciones_qa"].lower())
        self.assertNotIn("test-evidence", filtro["observaciones_qa"].lower())
        kpi_rev = by_caso["Validar KPI Assortment"]["revision"]
        self.assertEqual(kpi_rev["observaciones_qa"], "")
        self.assertEqual(len(out["sheets_patch"]), 2)

    def test_export_regresion_nueva_hoja(self):
        catalog = parse_catalog_csv(
            (FIXTURES / "planilla_catalog_sample.csv").read_text(encoding="utf-8")
        )
        out = export_planilla(
            catalog=catalog,
            modo="regresion",
            nombre_hoja_nueva="Revision 15/10/26",
        )
        self.assertEqual(out["sheet_title"], "Revision 15/10/26")
        self.assertIn("Revision 1", out["grid_csv"])


if __name__ == "__main__":
    unittest.main()
