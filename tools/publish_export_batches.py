"""Genera lotes compactos write_range desde export-planilla.json (salida JSON)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_harness.planilla_qa import REVISION_FIELD_NAMES, _col_letter, revision_start_col


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: publish_export_batches.py <export.json>", file=sys.stderr)
        return 2
    export = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    sheet = export.get("sheet_title") or ""
    rev = int(export.get("revision_index") or 1)
    sid = export.get("spreadsheet_id")
    filas = sorted(
        [f for f in export.get("filas") or [] if f.get("sheet_row")],
        key=lambda f: int(f["sheet_row"]),
    )
    start = revision_start_col(rev)
    end = start + len(REVISION_FIELD_NAMES) - 1
    col_a, col_b = _col_letter(start), _col_letter(end)

    batches: list[dict] = []
    pending: list[list[str]] = []
    rows: list[int] = []

    def flush_rev() -> None:
        if not pending:
            return
        batches.append(
            {
                "sheet": sheet,
                "cells": f"{col_a}{rows[0]}:{col_b}{rows[-1]}",
                "values": [row[:] for row in pending],
            }
        )
        pending.clear()
        rows.clear()

    for fila in filas:
        row = int(fila["sheet_row"])
        blocks = fila.get("revisiones") or []
        block = blocks[rev - 1] if rev - 1 < len(blocks) else {}
        if rows and row != rows[-1] + 1:
            flush_rev()
        rows.append(row)
        pending.append([block.get(n, "") for n in REVISION_FIELD_NAMES])
        if len(pending) >= 80:
            flush_rev()
    flush_rev()

    nuevas = [f for f in filas if f.get("catalog_nuevo")]
    if nuevas:
        r0, r1 = int(nuevas[0]["sheet_row"]), int(nuevas[-1]["sheet_row"])
        vals = []
        by_row = {int(f["sheet_row"]): f["catalog"] for f in nuevas}
        for r in range(r0, r1 + 1):
            c = by_row.get(r) or {}
            vals.append(
                [
                    c.get("id") or "",
                    c.get("caso_de_prueba") or "",
                    c.get("pasos_a_seguir") or "",
                    c.get("resultado_esperado") or "",
                    c.get("tablero") or "",
                    c.get("tipo_prueba") or "",
                ]
            )
        batches.insert(
            0,
            {
                "sheet": sheet,
                "cells": f"A{r0}:F{r1}",
                "values": [row[:] for row in vals],
                "kind": "catalog_nuevo",
            },
        )

    out = {"spreadsheet_id": sid, "sheet_title": sheet, "batches": batches}
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
