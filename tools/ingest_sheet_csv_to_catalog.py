"""Lee CSV (stdin o archivo) exportado de columnas A:F y escribe planilla-catalog.json."""
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
    parser.add_argument("input", nargs="?", type=Path, help="CSV; si se omite, lee stdin")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--spreadsheet-id", default="")
    parser.add_argument("--sheet-title", default="")
    parser.add_argument("--template-sheet-id", type=int, default=None)
    parser.add_argument("--url", default="")
    args = parser.parse_args()
    text = (
        args.input.read_text(encoding="utf-8-sig")
        if args.input
        else sys.stdin.read()
    )
    source = {
        "spreadsheet_id": args.spreadsheet_id or None,
        "sheet_title": args.sheet_title or None,
        "template_sheet_title": args.sheet_title or None,
        "template_sheet_id": args.template_sheet_id,
        "url": args.url or None,
    }
    catalog = parse_catalog_csv(text, source=source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(len(catalog["cases"]), "cases ->", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
