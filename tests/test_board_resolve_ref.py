from __future__ import annotations

import unittest
from pathlib import Path

from qa_harness.board_profiles import resolve_board_from_ref
from qa_harness.common import ContractError


class BoardResolveRefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.consumer = self.root / "_tmp_consumer"
        self.consumer.mkdir(exist_ok=True)
        qa = self.consumer / "Softys" / "qa"
        qa.mkdir(parents=True)
        (qa / "board.yml").write_text(
            "version_id: test-v1\nlabel: Tablero prueba\npbip_manifest: Softys (1).pbip\n",
            encoding="utf-8",
        )
        bundle = self.consumer / "Softys"
        bundle.mkdir(parents=True, exist_ok=True)
        (bundle / "Softys (1).pbip").write_text("{}", encoding="utf-8")
        (bundle / "Softys (1).Report").mkdir()
        (bundle / "Softys (1).SemanticModel").mkdir()

        self.config = {
            "default_board": "softys",
            "boards": {
                "softys": {
                    "label": "Softys cfg",
                    "consumer_repo_root": str(self.consumer.relative_to(self.root)),
                    "board_qa_root": str((qa).relative_to(self.root)),
                    "pbip_relative": "Softys/Softys (1).pbip",
                    "framework_root": ".",
                }
            },
        }

    def tearDown(self) -> None:
        import shutil

        if self.consumer.is_dir():
            shutil.rmtree(self.consumer, ignore_errors=True)

    def test_resolve_from_report_drag(self) -> None:
        ref = f"@{self.consumer.name}/Softys/Softys (1).Report"
        bid, _entry, ctx = resolve_board_from_ref(self.root, self.config, ref)
        self.assertEqual(bid, "softys")
        self.assertEqual(ctx["version_id"], "test-v1")
        self.assertEqual(ctx["resolved_via"], "path_ref")
        self.assertIn("Softys (1).Report", ctx["report_path"])

    def test_resolve_board_id_token(self) -> None:
        bid, entry, ctx = resolve_board_from_ref(self.root, self.config, "softys")
        self.assertEqual(bid, "softys")
        self.assertEqual(ctx["resolved_via"], "board_id")

    def test_unknown_path_raises(self) -> None:
        with self.assertRaises(ContractError):
            resolve_board_from_ref(self.root, self.config, "Otro/Otro.Report")


if __name__ == "__main__":
    unittest.main()
