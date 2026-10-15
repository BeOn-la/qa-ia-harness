from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .common import ContractError
from .board_profiles import board_qa_root, resolve_board_from_ref, sql_framework_root
from .sql_profiles import (
    applied_env_file,
    harness_root,
    load_local_profiles_config,
    profile_entry,
)


def resolve_pbi_paths(
    root: Path,
    config: dict[str, Any],
    board_id: str | None,
    board_ref: str | None = None,
) -> tuple[Path, Path, str, dict[str, Any]]:
    ref = board_ref if board_ref is not None else board_id
    bid, board, ctx = resolve_board_from_ref(root, config, ref)
    board_path = board_qa_root(root, board)
    script = board_path / "sql" / "run_month_oracles.py"
    if not script.is_file():
        raise ContractError(f"No existe el runner de oráculos: {script}")
    framework_path = sql_framework_root(root, config, board)
    return script, framework_path, bid, ctx


def evaluate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "error", "exit_code": 2, "message": "Sin filas de resultado", "rows": []}
    failed = [r for r in rows if r.get("compare_status") != "pass"]
    return {
        "status": "passed" if not failed else "failed",
        "exit_code": 0 if not failed else 1,
        "kpi_count": len(rows),
        "failed_kpi_ids": [r.get("kpi_id") for r in failed],
        "rows": rows,
    }


def run_month_oracles(
    *,
    harness_root_path: Path | None = None,
    profile: str,
    board_id: str | None = None,
    board_ref: str | None = None,
    kpi_id: str | None = None,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    root = harness_root_path or harness_root()
    config = load_local_profiles_config(root)
    entry = profile_entry(config, profile)
    if board_ref and board_id:
        raise ContractError("Usar solo --board o --ref, no ambos.")
    script, framework_path, bid, board_ctx = resolve_pbi_paths(
        root, config, board_id, board_ref=board_ref
    )

    venv_python = framework_path / ".venv" / "Scripts" / "python.exe"
    python = str(venv_python if venv_python.is_file() else Path(sys.executable))

    argv = [python, str(script)]
    if kpi_id:
        argv.extend(["--kpi", kpi_id])

    env = os.environ.copy()
    env.setdefault("MSSQL_QUERY_TIMEOUT", str(timeout_seconds))

    with applied_env_file(root, entry["env_file"]):
        proc = subprocess.run(
            argv,
            cwd=str(script.parent),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env=env,
        )

    if proc.returncode != 0 and not proc.stdout.strip():
        raise ContractError(
            f"run_month_oracles falló (code {proc.returncode}): {proc.stderr.strip() or 'sin stderr'}"
        )

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ContractError(
            f"Salida no JSON del runner SQL. stderr: {proc.stderr[:500]}"
        ) from exc

    if kpi_id:
        rows: list[dict[str, Any]] = []
        for block in payload.values():
            if isinstance(block, list):
                rows.extend(block)
        summary = evaluate_rows(rows)
    else:
        if not isinstance(payload, list):
            raise ContractError("Se esperaba una lista JSON de KPI desde compare/month/all-kpis.sql")
        summary = evaluate_rows(payload)

    summary["profile"] = profile
    summary["board_id"] = bid
    summary["board_resolution"] = board_ctx
    summary["runner_script"] = str(script)
    summary["sql_framework"] = str(framework_path)
    if proc.stderr.strip():
        summary["runner_stderr"] = proc.stderr.strip()
    return summary
