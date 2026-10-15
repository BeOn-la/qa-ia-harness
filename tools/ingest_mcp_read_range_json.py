"""Convierte salida JSON de MCP read_range (campo ranges[].content) en planilla-catalog.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_harness.planilla_qa import parse_catalog_csv  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mcp_json", type=Path, help="JSON de read_range (archivo o -)")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--spreadsheet-id", default="1IiB3WAUIJQJNzJSmC6oLI2aZiGJYGW_qOqj1P8Bbo-Y")
    parser.add_argument("--sheet-title", default="Revision 14/10/26")
    parser.add_argument("--template-sheet-id", type=int, default=0)
    args = parser.parse_args()
    raw = (
        args.mcp_json.read_text(encoding="utf-8-sig")
        if args.mcp_json != Path("-")
        else sys.stdin.read()
    )
    data = json.loads(raw)
    parts: list[str] = []
    for block in data.get("ranges") or []:
        text = (block.get("content") or "").strip()
        if text:
            parts.append(text)
    merged = "\n".join(parts)
    source = {
        "spreadsheet_id": args.spreadsheet_id,
        "sheet_title": args.sheet_title,
        "template_sheet_title": args.sheet_title,
        "template_sheet_id": args.template_sheet_id,
        "url": f"https://docs.google.com/spreadsheets/d/{args.spreadsheet_id}/edit",
    }
    catalog = parse_catalog_csv(merged, source=source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(len(catalog["cases"]), "cases ->", args.output)
    auto = sum(1 for c in catalog["cases"] if c.get("automation"))
    print("con automation:", auto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
