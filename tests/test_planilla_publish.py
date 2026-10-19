import unittest

from qa_harness.planilla_publish import build_corrida_repo_publish_plan, build_publish_plan
from qa_harness.planilla_qa import export_planilla, parse_catalog_csv


class TestPlanillaPublish(unittest.TestCase):
    def test_regresion_includes_copy_step(self):
        catalog = parse_catalog_csv(
            ",Validar KPI Assortment,,,Home,KPI/Calculos\n",
        )
        catalog["source"] = {
            "spreadsheet_id": "abc",
            "sheet_title": "Revision plantilla",
            "template_sheet_id": 0,
        }
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
        export = export_planilla(
            catalog=catalog,
            kpi=kpi,
            modo="regresion",
            nombre_hoja_nueva="Revision 20/10/26",
        )
        plan = export["publish_plan"]
        self.assertEqual(plan["pasos"][0]["herramienta_mcp"], "copy_sheet_to_another_spreadsheet")
        self.assertTrue(any(p["herramienta_mcp"] == "write_range" for p in plan["pasos"]))

    def test_corrida_repo_publish_plan(self):
        plan = build_corrida_repo_publish_plan(
            spreadsheet_id="sid",
            template_sheet_id=0,
            template_sheet_title="Revision 14-10-26",
            target_sheet_title="Corrida repo 16-10-26",
            data_row_count=576,
            adc_batch_ranges=["A1:AC344", "A345:AC576"],
        )
        tools = [p["herramienta_mcp"] for p in plan["pasos"]]
        self.assertIn("copy_sheet_to_another_spreadsheet", tools)
        self.assertIn("insert_rows_or_columns", tools)
        self.assertNotIn("write_range", tools)
        self.assertEqual(plan["subida_datos"]["preferida"], "adc")
        local = [p for p in plan["pasos"] if p.get("herramienta_mcp") == "(script local)"]
        self.assertGreaterEqual(len(local), 2)


if __name__ == "__main__":
    unittest.main()
