from __future__ import annotations

import unittest

from qa_harness.pbi_filter_scope import compare_filter, _norm


class PbiFilterScopeTests(unittest.TestCase):
    def test_norm_strips_accents(self):
        self.assertEqual(_norm("La Anónima"), _norm("La Anonima"))

    def test_store_ok(self):
        spec = {
            "label": "Etailer / Tienda",
            "pairs": [{"platform": "Dia", "store": "Generica"}],
        }
        sql = {"etailer_tienda": [{"platform": "Día", "store": "Generica"}]}
        row = compare_filter("etailer_tienda", spec, sql, ["EcoDimStore.PlatformName"])
        self.assertEqual(row["status"], "ok")

    def test_store_fail_extra(self):
        spec = {"label": "x", "pairs": [{"platform": "A", "store": "B"}]}
        sql = {
            "etailer_tienda": [
                {"platform": "A", "store": "B"},
                {"platform": "C", "store": "D"},
            ]
        }
        row = compare_filter("etailer_tienda", spec, sql, ["EcoDimStore.Store"])
        self.assertEqual(row["status"], "fail")
        self.assertIn("sobran", row["detail"] or "")


if __name__ == "__main__":
    unittest.main()
