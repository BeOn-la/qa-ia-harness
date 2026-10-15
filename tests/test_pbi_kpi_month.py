from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from qa_harness.common import ContractError
from qa_harness.pbi_kpi_month import evaluate_rows, run_month_oracles
from qa_harness.sql_profiles import applied_env_file, parse_env_lines


class PbiKpiMonthTests(unittest.TestCase):
    def test_evaluate_rows_pass_and_fail(self):
        ok = evaluate_rows([{"kpi_id": "a", "compare_status": "pass"}])
        self.assertEqual(ok["exit_code"], 0)
        bad = evaluate_rows([{"kpi_id": "a", "compare_status": "fail"}])
        self.assertEqual(bad["exit_code"], 1)
        self.assertEqual(bad["failed_kpi_ids"], ["a"])

    def test_parse_env_lines(self):
        values = parse_env_lines("# comment\nMSSQL_USER=qa\nMSSQL_PASSWORD=\"x\"\n")
        self.assertEqual(values["MSSQL_USER"], "qa")
        self.assertEqual(values["MSSQL_PASSWORD"], "x")

    def test_run_month_oracles_invokes_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname='qa'\n")
            (root / "src" / "qa_harness").mkdir(parents=True)
            board = root / "beon" / "Softys" / "qa"
            (board / "sql").mkdir(parents=True)
            runner = board / "sql" / "run_month_oracles.py"
            runner.write_text("# stub\n")
            fw = root / "fw"
            fw.mkdir()
            (fw / ".venv" / "Scripts").mkdir(parents=True)
            (fw / ".venv" / "Scripts" / "python.exe").write_text("")

            config = {
                "profiles": {
                    "staging": {"execution": "allowed", "env_file": "config/sql/.env.test"},
                },
                "pbi_qa": {
                    "board_qa_root": "beon/Softys/qa",
                    "framework_root": "fw",
                },
            }
            (root / ".qa-profiles.local.json").write_text(json.dumps(config))
            env_dir = root / "config" / "sql"
            env_dir.mkdir(parents=True)
            (env_dir / ".env.test").write_text("MSSQL_USER=u\nMSSQL_PASSWORD=p\n")

            payload = [{"kpi_id": "title-compliance", "compare_status": "pass"}]
            with patch("qa_harness.pbi_kpi_month.subprocess.run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = json.dumps(payload)
                run.return_value.stderr = ""
                result = run_month_oracles(harness_root_path=root, profile="staging")
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["kpi_count"], 1)
            run.assert_called_once()

    def test_applied_env_file_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "env"
            path.write_text("QA_TMP=1\n")
            with patch.dict(__import__("os").environ, {}, clear=False):
                import os

                os.environ.pop("QA_TMP", None)
                with applied_env_file(root, "env"):
                    self.assertEqual(os.environ.get("QA_TMP"), "1")
                self.assertIsNone(os.environ.get("QA_TMP"))

    def test_missing_config_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("")
            (root / "src" / "qa_harness").mkdir(parents=True)
            with self.assertRaises(ContractError):
                run_month_oracles(harness_root_path=root, profile="staging")


if __name__ == "__main__":
    unittest.main()
