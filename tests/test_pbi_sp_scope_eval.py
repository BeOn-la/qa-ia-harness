import importlib.util
import unittest
from pathlib import Path


def _load_runner_module():
    root = Path(__file__).resolve().parents[1]
    path = (root.parent / "beon-pbi" / "Softys" / "qa" / "sql" / "run_pbi_sp_scope.py").resolve()
    if not path.is_file():
        raise unittest.SkipTest(f"No existe {path}")
    spec = importlib.util.spec_from_file_location("run_pbi_sp_scope", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestPbiSpScopeEval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_runner_module()
        cls.contract = cls.mod._load_contract()

    def test_fact_null_threshold_fail(self):
        row = self.mod._evaluate_row(
            "FactProductCompliance",
            100,
            {
                "total_rows": 100,
                "null_title_bool": 96,
                "null_assortment": 0,
                "null_stock": 0,
                "null_qimage": 0,
                "min_products_per_store": 120,
            },
            self.contract,
        )
        self.assertEqual(row["status"], "fail")

    def test_dim_store_min_rows(self):
        row = self.mod._evaluate_row("DimStore", 9, {}, self.contract)
        self.assertEqual(row["status"], "ok")
        row_bad = self.mod._evaluate_row("DimStore", 8, {}, self.contract)
        self.assertEqual(row_bad["status"], "fail")


if __name__ == "__main__":
    unittest.main()
