from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_alcance_document(board_qa_root: Path) -> dict[str, Any]:
    path = board_qa_root / "alcance-ajustes-planilla.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def global_ajustes(doc: dict[str, Any]) -> dict[str, Any]:
    raw = doc.get("global")
    return raw if isinstance(raw, dict) else {}


def por_hoja_ajustes(doc: dict[str, Any]) -> dict[str, Any]:
    raw = doc.get("por_hoja")
    return raw if isinstance(raw, dict) else {}


def indicadores_no_habilitados_ui(doc: dict[str, Any]) -> set[str]:
    g = global_ajustes(doc)
    ids = g.get("indicadores_no_habilitados_ui") or g.get("indicadores_no_habilitados") or []
    return {str(x) for x in ids}


def filtros_aprobados_producto(doc: dict[str, Any]) -> set[str]:
    g = global_ajustes(doc)
    return {str(x) for x in (g.get("filtros_aprobados_producto") or [])}


def navegacion_no_valida_en_home(doc: dict[str, Any]) -> set[str]:
    g = global_ajustes(doc)
    return {str(x).strip() for x in (g.get("navegacion_no_valida_en_home") or [])}


def no_exigir_visibles_en_hoja(doc: dict[str, Any], hoja: str) -> set[str]:
    reglas = por_hoja_ajustes(doc).get(hoja) or {}
    base = set(indicadores_no_habilitados_ui(doc))
    base.update(str(x) for x in (reglas.get("no_exigir_visibles") or []))
    return base


def kpi_tratado_como_no_visible(kpi_id: str, hoja: str, doc: dict[str, Any]) -> bool:
    return kpi_id in no_exigir_visibles_en_hoja(doc, hoja)
