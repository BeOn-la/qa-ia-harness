import unittest

from qa_harness.planilla_publish import build_publish_plan
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
        export = export_planilla(
            catalog=catalog,
            modo="regresion",
            nombre_hoja_nueva="Revision 20/10/26",
        )
        plan = export["publish_plan"]
        self.assertEqual(plan["pasos"][0]["herramienta_mcp"], "copy_sheet_to_another_spreadsheet")
        self.assertTrue(any(p["herramienta_mcp"] == "write_range" for p in plan["pasos"]))


if __name__ == "__main__":
    unittest.main()
