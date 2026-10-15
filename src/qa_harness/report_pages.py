from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import ContractError

_QUERY_REF_RE = re.compile(r'"queryRef"\s*:\s*"([^"]+)"')
_METADATA_MEASURE_RE = re.compile(r'"metadata":\s*"DAX Measures\.([^"]+)"')


@dataclass(frozen=True)
class ReportPage:
    page_id: str
    display_name: str


def list_report_pages(report_path: Path) -> list[ReportPage]:
    if not report_path.is_dir():
        raise ContractError(f"No existe la carpeta del informe: {report_path}")
    pages_meta = report_path / "definition" / "pages" / "pages.json"
    if not pages_meta.is_file():
        raise ContractError(f"Sin pages.json en {report_path}")
    meta = json.loads(pages_meta.read_text(encoding="utf-8"))
    order = meta.get("pageOrder")
    if not isinstance(order, list):
        raise ContractError("pages.json sin pageOrder")
    pages: list[ReportPage] = []
    for page_id in order:
        if not isinstance(page_id, str):
            continue
        page_json = report_path / "definition" / "pages" / page_id / "page.json"
        if not page_json.is_file():
            continue
        data = json.loads(page_json.read_text(encoding="utf-8"))
        name = data.get("displayName") or page_id
        pages.append(ReportPage(page_id=page_id, display_name=str(name)))
    return pages


def select_pages(pages: list[ReportPage], page_filter: str | None) -> list[ReportPage]:
    if not page_filter or not page_filter.strip():
        return pages
    needle = page_filter.strip().casefold()
    matched = [
        p
        for p in pages
        if p.page_id.casefold() == needle or p.display_name.casefold() == needle
    ]
    if not matched:
        partial = [p for p in pages if needle in p.display_name.casefold()]
        matched = partial
    if not matched:
        known = ", ".join(f"{p.display_name!r}" for p in pages)
        raise ContractError(
            f"No se encontró la hoja {page_filter!r}. Hojas disponibles: {known}"
        )
    return matched


def query_refs_on_page(report_path: Path, page_id: str) -> set[str]:
    folder = report_path / "definition" / "pages" / page_id
    if not folder.is_dir():
        return set()
    refs: set[str] = set()
    for path in folder.rglob("*.json"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        refs.update(_QUERY_REF_RE.findall(text))
    return refs


def dax_measures_on_page(report_path: Path, page_id: str) -> set[str]:
    folder = report_path / "definition" / "pages" / page_id
    measures: set[str] = set()
    if not folder.is_dir():
        return measures
    for path in folder.rglob("*.json"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for ref in _QUERY_REF_RE.findall(text):
            if ref.startswith("DAX Measures."):
                measures.add(ref.split(".", 1)[1])
        measures.update(_METADATA_MEASURE_RE.findall(text))
    return measures


def kpi_shown_on_page(catalog_entry: dict[str, Any], measures: set[str]) -> bool:
    primary = str(catalog_entry["dax_measure"])
    label = str(catalog_entry.get("home_label") or "")
    label_cf = label.casefold()
    primary_cf = primary.casefold()
    head = primary.split()[0].casefold() if primary else ""

    for alt in catalog_entry.get("dax_selector_measures") or []:
        if str(alt) in measures:
            return True

    for m in measures:
        m_cf = m.casefold()
        if m == primary or m_cf == primary_cf:
            return True
        if primary_cf in m_cf or m_cf in primary_cf:
            return True
        if label_cf and label_cf in m_cf:
            return True
        if head and len(head) > 3 and m_cf.startswith(head):
            return True
    return False


def page_result_shell(page: ReportPage) -> dict[str, Any]:
    return {
        "identificador_hoja": page.page_id,
        "nombre_hoja": page.display_name,
        "casos_de_prueba": [],
    }
