import unittest

from qa_harness.planilla_publish import _revision_write_batches


class TestPublishValuesCopy(unittest.TestCase):
    def test_batch_values_not_cleared_after_flush(self):
        filas = [
            {
                "sheet_row": 3,
                "automation": {"x": 1},
                "revisiones": [
                    {
                        "estado": "Aprobado",
                        "tipo_error": "",
                        "prioridad": "",
                        "controlado_por": "",
                        "resuelto_por": "",
                        "fecha_auditoria": "01/01/2026",
                        "fecha_revision": "",
                        "captura_1": "",
                        "captura_2": "",
                        "observaciones_qa": "ok",
                        "observaciones_desarrollo": "",
                    }
                ],
            }
        ]
        batches = _revision_write_batches(
            filas,
            sheet_title="T",
            revision_index=1,
            only_automated=True,
        )
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["values"][0][0], "Aprobado")


if __name__ == "__main__":
    unittest.main()
