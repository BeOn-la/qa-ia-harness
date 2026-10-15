from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import ContractError

_KPI_BLOCK_RE = re.compile(
    r"^\s*-\s+kpi_id:\s*(?P<id>\S+)\s*\n"
    r"(?P<body>(?:^\s{4,}\S.*\n)*)",
    re.MULTILINE,
)
_FIELD_RE = re.compile(r"^\s+(?P<key>\w+):\s*(?P<val>.+?)\s*$", re.MULTILINE)


def load_kpi_catalog(catalog_path: Path) -> list[dict[str, Any]]:
    if not catalog_path.is_file():
        raise ContractError(f"No existe el catálogo de indicadores: {catalog_path}")
    text = catalog_path.read_text(encoding="utf-8-sig")
    entries: list[dict[str, Any]] = []
    for match in _KPI_BLOCK_RE.finditer(text):
        body = match.group("body")
        fields: dict[str, Any] = {"kpi_id": match.group("id")}
        for fm in _FIELD_RE.finditer(body):
            key, val = fm.group("key"), fm.group("val").strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                fields[key] = [p.strip() for p in inner.split(",") if p.strip()]
            else:
                fields[key] = val.strip('"').strip("'")
        if "dax_measure" not in fields:
            raise ContractError(f"Falta dax_measure para kpi_id={fields['kpi_id']}")
        entries.append(fields)
    if not entries:
        raise ContractError(f"Sin entradas en catálogo: {catalog_path}")
    return entries
