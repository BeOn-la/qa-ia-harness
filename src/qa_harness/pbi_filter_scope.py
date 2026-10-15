from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from .common import ContractError
from .report_filters import discover_report_filter_ids, load_scope_filters
from .sql_profiles import applied_env_file, harness_root, load_local_profiles_config, profile_entry
from .pbi_kpi_month import resolve_pbi_paths


def _norm(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text).casefold()


def _norm_platform(platform: str) -> str:
    p = _norm(platform)
    for suffix in (" app ar", " ar"):
        if p.endswith(suffix):
            p = p[: -len(suffix)].strip()
    p = p.replace("mas online", "masonline")
    return p


def _norm_store(store: str) -> str:
    s = _norm(store)
    if s in ("generic", "generica"):
        return "generica"
    if s.startswith("tienda "):
        s = s[7:].strip()
    return s


def _pair_key(platform: str, store: str) -> str:
    return f"{_norm_platform(platform)}|{_norm_store(store)}"


def _norm_group(group: str) -> str:
    g = _norm(group)
    return g.replace("cuidado del adulto", "cuidado adulto")


def _cat_key(group: str, category: str) -> str:
    return f"{_norm_group(group)}|{_norm(category)}"


def _display_store(platform: str, store: str) -> str:
    return f"{platform} / {store}"


def _display_cat(group: str, category: str) -> str:
    return f"{group} / {category}"


def compare_filter(
    filter_id: str,
    spec: dict[str, Any],
    sql_values: dict[str, list],
    report_refs: list[str] | None,
) -> dict[str, Any]:
    label = spec.get("label") or filter_id
    in_report = bool(report_refs)
    detail_parts: list[str] = []

    mock_binding = bool(report_refs and any(r.startswith("Mock_") for r in report_refs))
    if mock_binding:
        detail_parts.append("slicer usa Mock_CategoryGroup_Category (no CategoryGroup_Category)")

    if filter_id == "etailer_tienda":
        expected = {
            _pair_key(p["platform"], p["store"]): _display_store(p["platform"], p["store"])
            for p in spec.get("pairs", [])
        }
        actual_raw = sql_values.get("etailer_tienda") or []
        actual = {
            _pair_key(r["platform"], r["store"]): _display_store(r["platform"], r["store"])
            for r in actual_raw
        }
    elif filter_id == "categoria":
        expected = {
            _cat_key(p["group"], p["category"]): _display_cat(p["group"], p["category"])
            for p in spec.get("pairs", [])
        }
        actual_raw = sql_values.get("categoria") or []
        actual = {
            _cat_key(r["group"], r["category"]): _display_cat(r["group"], r["category"])
            for r in actual_raw
        }
    elif filter_id == "keyword_sos":
        expected = {_norm(k): k for k in spec.get("values", [])}
        actual_raw = sql_values.get("keyword_sos") or []
        actual = {_norm(r["keyword"]): r["keyword"] for r in actual_raw}
    else:
        raise ContractError(f"filter_id desconocido en scope: {filter_id}")

    missing = sorted(expected[k] for k in expected if k not in actual)
    extra = sorted(actual[k] for k in actual if k not in expected)
    values_display = sorted(actual.values())

    status = "ok"
    if missing:
        status = "fail"
        detail_parts.append(f"faltan en SQL: {', '.join(missing)}")
    if extra:
        status = "fail"
        detail_parts.append(f"sobran en SQL: {', '.join(extra)}")
    if mock_binding and filter_id == "categoria":
        status = "fail"

    return {
        "filter_id": filter_id,
        "filtro": label,
        "en_tablero": in_report,
        "valores": values_display,
        "status": status,
        "detail": "; ".join(detail_parts) if detail_parts else None,
    }


def run_filter_scope_sql_values(
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
    filter_runner = script.parent / "run_filter_scope.py"
    if not filter_runner.is_file():
        raise ContractError(f"No existe {filter_runner}")

    venv_python = framework_path / ".venv" / "Scripts" / "python.exe"
    python = str(venv_python if venv_python.is_file() else Path(sys.executable))

    import subprocess

    env = os.environ.copy()
    env.setdefault("MSSQL_QUERY_TIMEOUT", str(timeout_seconds))

    with applied_env_file(root, entry["env_file"]):
        proc = subprocess.run(
            [python, str(filter_runner)],
            cwd=str(filter_runner.parent),
            capture_output=True,
            timeout=timeout_seconds,
            env=env,
        )

    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        stdout = proc.stdout.decode("utf-8", errors="replace")[:300]
        raise ContractError(
            f"run_filter_scope falló (code {proc.returncode}): {stderr or stdout}"
        )

    try:
        return json.loads(proc.stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"Salida no JSON de run_filter_scope: {exc}") from exc


def run_filter_scope(
    *,
    harness_root_path: Path | None = None,
    profile: str,
    board_id: str | None = None,
    board_ref: str | None = None,
    timeout_seconds: int = 180,
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

    rows: list[dict[str, Any]] = []
    for filter_id, spec in scope_doc["filters"].items():
        if filter_id not in report_map:
            continue
        rows.append(
            compare_filter(
                filter_id,
                spec,
                sql_values,
                report_map.get(filter_id),
            )
        )

    failed = [r for r in rows if r["status"] != "ok"]
    return {
        "status": "passed" if not failed else "failed",
        "exit_code": 0 if not failed else 1,
        "profile": profile,
        "board_id": bid,
        "scope_label": scope_doc.get("scope_label"),
        "filter_count": len(rows),
        "rows": rows,
        "board_resolution": board_ctx,
    }
