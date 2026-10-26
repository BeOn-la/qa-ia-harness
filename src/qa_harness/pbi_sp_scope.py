from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .common import ContractError
from .pbi_filter_scope import compare_filter, run_filter_scope_sql_values
from .report_filters import discover_report_filter_ids, load_scope_filters
from .sql_profiles import applied_env_file, harness_root, load_local_profiles_config, profile_entry
from .pbi_kpi_month import resolve_pbi_paths


def run_pbi_sp_scope_sql(
    harness_root_path: Path,
    config: dict[str, Any],
    profile: str,
    board_id: str | None,
    board_ref: str | None,
    timeout_seconds: int,
) -> dict[str, Any]:
    root = harness_root_path
    entry = profile_entry(config, profile)
    script, framework_path, _bid, _ctx = resolve_pbi_paths(
        root, config, board_id, board_ref=board_ref
    )
    runner = script.parent / "run_pbi_sp_scope.py"
    if not runner.is_file():
        raise ContractError(f"No existe {runner}")

    venv_python = framework_path / ".venv" / "Scripts" / "python.exe"
    python = str(venv_python if venv_python.is_file() else Path(sys.executable))

    import subprocess

    env = os.environ.copy()
    env.setdefault("MSSQL_QUERY_TIMEOUT", str(timeout_seconds))

    with applied_env_file(root, entry["env_file"]):
        proc = subprocess.run(
            [python, str(runner)],
            cwd=str(runner.parent),
            capture_output=True,
            timeout=timeout_seconds,
            env=env,
        )

    if proc.returncode not in (0, 1):
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        stdout = proc.stdout.decode("utf-8", errors="replace")[:500]
        raise ContractError(
            f"run_pbi_sp_scope falló (code {proc.returncode}): {stderr or stdout}"
        )

    try:
        return json.loads(proc.stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"Salida no JSON de run_pbi_sp_scope: {exc}") from exc


def run_pbi_sp_scope(
    *,
    harness_root_path: Path | None = None,
    profile: str,
    board_id: str | None = None,
    board_ref: str | None = None,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    root = harness_root_path or harness_root()
    config = load_local_profiles_config(root)
    if board_ref and board_id:
        raise ContractError("Usar solo --board o --ref, no ambos.")

    _script, _framework_path, bid, board_ctx = resolve_pbi_paths(
        root, config, board_id, board_ref=board_ref
    )

    board_path = Path(board_ctx["board_qa_root"])
    scope_doc = load_scope_filters(board_path)
    report_path = Path(board_ctx["report_path"])
    report_map = discover_report_filter_ids(report_path)

    sql_values = run_filter_scope_sql_values(
        root, config, profile, board_id, board_ref, timeout_seconds
    )

    filter_rows: list[dict[str, Any]] = []
    for filter_id, spec in scope_doc["filters"].items():
        if filter_id not in report_map:
            continue
        filter_rows.append(
            compare_filter(
                filter_id,
                spec,
                sql_values,
                report_map.get(filter_id),
            )
        )

    sp_payload = run_pbi_sp_scope_sql(
        root, config, profile, board_id, board_ref, timeout_seconds
    )

    filter_failed = [r for r in filter_rows if r.get("status") == "fail"]
    sp_failed = [
        r for r in sp_payload.get("stored_procedures", []) if r.get("status") == "fail"
    ]
    exit_code = 1 if filter_failed or sp_failed else 0

    return {
        "status": "failed" if exit_code else sp_payload.get("status", "ok"),
        "exit_code": exit_code,
        "profile": profile,
        "board_id": bid,
        "scope_label": scope_doc.get("scope_label"),
        "filters": filter_rows,
        "stored_procedures": sp_payload.get("stored_procedures", []),
        "summary": {
            "filters_failed": len(filter_failed),
            "sp_failed": len(sp_failed),
            "sp_warned": sp_payload.get("summary", {}).get("warned", 0),
        },
        "board_resolution": board_ctx,
    }
