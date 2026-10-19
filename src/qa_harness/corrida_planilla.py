from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .board_profiles import resolve_board_from_ref
from .common import ContractError
from .pbi_por_hoja import run_filtros_por_hoja, run_kpi_por_hoja, run_visuales_por_hoja
from .planilla_bindings import load_planilla_bindings
from .planilla_publish import build_corrida_repo_publish_plan
from .planilla_qa import (
    default_planilla_bindings_path,
    export_planilla,
    load_planilla_catalog,
    load_planilla_qa_config,
    load_tablero_aliases,
)
from .sql_profiles import harness_root, load_local_profiles_config


def run_corrida_planilla(
    *,
    harness_root_path: Path | None = None,
    profile: str,
    board_ref: str | None = None,
    board_id: str | None = None,
    modo: str,
    revision_index: int = 1,
    hoja_planilla: str | None = None,
    nombre_hoja_nueva: str | None = None,
    entrada_previa_path: Path | None = None,
    solo_fallidos_anterior: bool = False,
    evidence_dir: Path | None = None,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    root = harness_root_path or harness_root()
    config = load_local_profiles_config(root)
    bid, _board, ctx = resolve_board_from_ref(root, config, board_ref or board_id)
    board_qa = Path(ctx["board_qa_root"])
    catalog_path = board_qa / "manual-cases" / "planilla-catalog.json"
    catalog = load_planilla_catalog(catalog_path) if modo != "corrida_repo" else {}
    aliases_path = board_qa / "planilla-tablero-aliases.json"
    tablero_aliases = load_tablero_aliases(aliases_path)
    bindings_path = default_planilla_bindings_path(board_qa)
    planilla_bindings = load_planilla_bindings(bindings_path)

    common = {
        "harness_root_path": root,
        "profile": profile,
        "board_id": board_id,
        "board_ref": board_ref,
        "timeout_seconds": timeout_seconds,
    }
    kpi = run_kpi_por_hoja(**common)
    filtros = run_filtros_por_hoja(**{**common, "timeout_seconds": min(timeout_seconds, 180)})
    visuales = run_visuales_por_hoja(**common)

    prev = None
    if entrada_previa_path and entrada_previa_path.is_file():
        prev = json.loads(entrada_previa_path.read_text(encoding="utf-8-sig"))

    if modo == "regresion" and not nombre_hoja_nueva:
        nombre_hoja_nueva = f"Revision {date.today().strftime('%d/%m/%y')}"

    export: dict[str, Any]
    publish_plan: dict[str, Any] | None
    if modo == "corrida_repo":
        export, publish_plan = _build_corrida_repo_export(
            board_qa=board_qa,
            nombre_hoja_nueva=nombre_hoja_nueva,
            stamp=date.today().isoformat(),
            evidence_dir=evidence_dir,
        )
    else:
        export = export_planilla(
            catalog=catalog,
            kpi=kpi,
            filtros=filtros,
            visuales=visuales,
            tablero_aliases=tablero_aliases or None,
            planilla_bindings=planilla_bindings,
            board_qa_root=board_qa,
            modo=modo,
            revision_index=revision_index,
            nombre_hoja_nueva=nombre_hoja_nueva,
            hoja_planilla=hoja_planilla,
            entrada_previa=prev,
            solo_fallidos_anterior=solo_fallidos_anterior,
            run_meta={
                "board_id": bid,
                "version_id": ctx.get("version_id"),
                "profile": profile,
            },
        )
        publish_plan = export.get("publish_plan")

    out_dir = evidence_dir or (board_qa / "test-evidence")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    paths = {
        "kpi": out_dir / f"kpi-por-hoja-{stamp}.json",
        "filtros": out_dir / f"filtros-por-hoja-{stamp}.json",
        "visuales": out_dir / f"visuales-por-hoja-{stamp}.json",
        "export": out_dir / f"export-planilla-{modo}-{stamp}.json",
        "corrida_repo_meta": out_dir / "_corrida_repo_sheet" / "meta.json",
    }
    paths["kpi"].write_text(json.dumps(kpi, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["filtros"].write_text(
        json.dumps(filtros, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["visuales"].write_text(
        json.dumps(visuales, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["export"].write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    # No persistir filas nuevas del catálogo en disco salvo regresión explícita con augment.
    if export.get("grid_csv"):
        (out_dir / f"planilla-{modo}-{stamp}.csv").write_text(
            export["grid_csv"], encoding="utf-8-sig"
        )

    codigo = max(
        int(kpi.get("codigo_salida") or 0),
        int(filtros.get("codigo_salida") or 0),
        int(visuales.get("codigo_salida") or 0),
    )
    return {
        "estado_general": "con fallos" if codigo else "correcto",
        "codigo_salida": codigo,
        "archivos": {k: str(v) for k, v in paths.items()},
        "export_planilla": export,
        "publish_plan": publish_plan,
    }


def _build_corrida_repo_export(
    *,
    board_qa: Path,
    nombre_hoja_nueva: str | None,
    stamp: str,
    evidence_dir: Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    tools = board_qa / "tools"
    build_script = tools / "build_corrida_repo_sheet.py"
    batches_script = tools / "make_corrida_repo_batches.py"
    if not build_script.is_file() or not batches_script.is_file():
        raise ContractError(
            "modo corrida_repo requiere tools/build_corrida_repo_sheet.py y "
            "tools/make_corrida_repo_batches.py en board_qa_root."
        )
    out_dir = evidence_dir or (board_qa / "test-evidence")
    target_title = nombre_hoja_nueva or f"Corrida repo {date.today().strftime('%d-%m-%y')}"
    for script, extra in (
        (build_script, ["--tag", stamp, "--evidence", str(out_dir), "--sheet-title", target_title]),
        (batches_script, ["--profile", "adc"]),
    ):
        subprocess.run(
            [sys.executable, str(script), *extra],
            cwd=str(tools),
            check=True,
        )
    repo_dir = out_dir / "_corrida_repo_sheet"
    meta = json.loads((repo_dir / "meta.json").read_text(encoding="utf-8-sig"))
    batches_doc = json.loads((repo_dir / "batches.json").read_text(encoding="utf-8-sig"))
    adc_ranges = [b["cells"] for b in batches_doc]
    planilla_cfg = load_planilla_qa_config(board_qa)
    spreadsheet_id = meta.get("spreadsheet_id") or planilla_cfg.get("spreadsheet_id")
    if not spreadsheet_id:
        raise ContractError("Falta spreadsheet_id en meta o board.yml planilla_qa.")
    template_id = planilla_cfg.get("template_sheet_id")
    template_title = (
        planilla_cfg.get("template_sheet_title") or "Revision 14/10/26"
    ).replace("/", "-")
    grid = json.loads((repo_dir / "grid.json").read_text(encoding="utf-8-sig"))
    publish = build_corrida_repo_publish_plan(
        spreadsheet_id=str(spreadsheet_id),
        template_sheet_id=template_id if isinstance(template_id, int) else None,
        template_sheet_title=template_title,
        target_sheet_title=meta.get("sheet_title") or target_title,
        data_row_count=len(grid),
        adc_batch_ranges=adc_ranges,
        board_qa_tools_relative="tools",
    )
    export = {
        "modo": "corrida_repo",
        "spreadsheet_id": spreadsheet_id,
        "sheet_title": publish["target_sheet_title"],
        "grid_rows": len(grid),
        "grid_cols": len(grid[0]) if grid else 0,
        "publish_plan": publish,
        "resumen": {
            "nota": "Planilla armada desde evidencia por hoja (sin planilla-catalog.json).",
            "filas": len(grid),
        },
    }
    return export, publish
