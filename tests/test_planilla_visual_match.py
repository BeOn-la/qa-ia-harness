import unittest

from qa_harness.planilla_visual_match import PageVisualState, try_match_planilla_visual


class TestPlanillaVisualMatch(unittest.TestCase):
    def test_selector_all_stock_listed(self):
        visuales = {
            "hojas": [
                {
                    "nombre_hoja": "Home",
                    "casos_de_prueba": [
                        {
                            "tipo_caso": "visual del informe",
                            "orden_en_hoja": 3,
                            "rol_interpretado": "filtro operativo (Parameter full)",
                            "lectura_qa": "Home · filtro operativo (Parameter full)",
                            "tipo_visual": "slicer",
                        }
                    ],
                }
            ]
        }
        case = {
            "caso_de_prueba": "Validar selector de All / In Stock / Listed",
            "tablero": "Home",
        }
        b, meta = try_match_planilla_visual(
            case, visuales, tablero_aliases=None, page_state=PageVisualState()
        )
        self.assertIsNotNone(b)
        self.assertEqual(b["capa"], "visuales")
        self.assertEqual(meta["patron"], "selector_all_stock_listed")


if __name__ == "__main__":
    unittest.main()
