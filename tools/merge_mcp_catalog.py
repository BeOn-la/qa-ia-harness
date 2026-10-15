"""Fusiona fragmentos CSV (MCP read_range) en planilla-catalog.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_harness.planilla_qa import parse_catalog_csv  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print("Uso: merge_mcp_catalog.py <salida.json> <chunk.csv> [...]", file=sys.stderr)
        return 2
    out = Path(sys.argv[1])
    texts = [Path(p).read_text(encoding="utf-8-sig") for p in sys.argv[2:]]
    merged = "\n".join(t.strip() for t in texts if t.strip())
    source = {
        "spreadsheet_id": "1IiB3WAUIJQJNzJSmC6oLI2aZiGJYGW_qOqj1P8Bbo-Y",
        "sheet_title": "Revision 14/10/26",
        "template_sheet_title": "Revision 14/10/26",
        "template_sheet_id": 0,
        "url": "https://docs.google.com/spreadsheets/d/1IiB3WAUIJQJNzJSmC6oLI2aZiGJYGW_qOqj1P8Bbo-Y/edit",
    }
    catalog = parse_catalog_csv(merged, source=source)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(len(catalog["cases"]), "cases ->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
