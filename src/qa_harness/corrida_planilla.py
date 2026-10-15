from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .board_profiles import resolve_board_from_ref
from .pbi_por_hoja import run_filtros_por_hoja, run_kpi_por_hoja, run_visuales_por_hoja
from .planilla_bindings import load_planilla_bindings
from .planilla_qa import (
    default_planilla_bindings_path,
    export_planilla,
    load_planilla_catalog,
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
    catalog = load_planilla_catalog(catalog_path)
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

    export = export_planilla(
        catalog=catalog,
        kpi=kpi,
        filtros=filtros,
        visuales=visuales,
        tablero_aliases=tablero_aliases or None,
        planilla_bindings=planilla_bindings,
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

    out_dir = evidence_dir or (board_qa / "test-evidence")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    paths = {
        "kpi": out_dir / f"kpi-por-hoja-{stamp}.json",
        "filtros": out_dir / f"filtros-por-hoja-{stamp}.json",
        "visuales": out_dir / f"visuales-por-hoja-{stamp}.json",
        "export": out_dir / f"export-planilla-{modo}-{stamp}.json",
    }
    paths["kpi"].write_text(json.dumps(kpi, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["filtros"].write_text(
        json.dumps(filtros, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["visuales"].write_text(
        json.dumps(visuales, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    paths["export"].write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    augmented = export.get("catalog_augmented") or {}
    if augmented.get("filas_agregadas"):
        from .planilla_qa import augment_catalog_with_harness

        merged = augment_catalog_with_harness(
            catalog,
            kpi,
            filtros,
            visuales,
            tablero_aliases=tablero_aliases,
        )
        merged.pop("catalog_augmented", None)
        catalog_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
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
        "publish_plan": export.get("publish_plan"),
    }
