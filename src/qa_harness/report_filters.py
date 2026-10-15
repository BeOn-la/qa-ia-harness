from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .common import ContractError

_QUERY_REF_RE = re.compile(r'"queryRef"\s*:\s*"([^"]+)"')

# Campos de slicer/filtro del reporte → id en scope-filters.json
_FIELD_TO_FILTER: dict[str, str] = {
    "EcoDimStore.PlatformName": "etailer_tienda",
    "EcoDimStore.Store": "etailer_tienda",
    "CategoryGroup_Category.CategoryGroup": "categoria",
    "CategoryGroup_Category.Category": "categoria",
    "Mock_CategoryGroup_Category.CategoryGroup": "categoria",
    "Mock_CategoryGroup_Category.Category": "categoria",
    "Dim_Keyword.Keyword": "keyword_sos",
}


def _map_refs_to_filters(refs: set[str]) -> dict[str, list[str]]:
    by_filter: dict[str, set[str]] = {}
    for ref in refs:
        fid = _FIELD_TO_FILTER.get(ref)
        if not fid:
            continue
        by_filter.setdefault(fid, set()).add(ref)
    return {k: sorted(v) for k, v in sorted(by_filter.items())}


def discover_report_filter_ids(report_path: Path) -> dict[str, list[str]]:
    """Devuelve filter_id → lista de queryRef del reporte que lo activan."""
    if not report_path.is_dir():
        raise ContractError(f"No existe la carpeta Report: {report_path}")
    definition = report_path / "definition"
    if not definition.is_dir():
        raise ContractError(f"Sin definition/ en {report_path}")

    refs: set[str] = set()
    for path in definition.rglob("*.json"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        refs.update(_QUERY_REF_RE.findall(text))

    return _map_refs_to_filters(refs)


def discover_page_filter_ids(report_path: Path, page_id: str) -> dict[str, list[str]]:
    from .report_pages import query_refs_on_page

    return _map_refs_to_filters(query_refs_on_page(report_path, page_id))


def load_scope_filters(board_qa_root: Path) -> dict[str, Any]:
    path = board_qa_root / "scope-filters.json"
    if not path.is_file():
        raise ContractError(
            f"Falta scope contractual de filtros: {path} (valores esperados vs Confluence)."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"JSON inválido en {path.name}") from exc
    if not isinstance(data.get("filters"), dict):
        raise ContractError("scope-filters.json debe tener objeto 'filters'.")
    return data
