"""
Sincroniza planilla-catalog.json desde Google Sheets (columnas A:F).

Flujo (agente con MCP plugin-google-sheets autenticado):

1. read_range pestaña plantilla ``Revision 14/10/26`` celdas ``A3:F280``
   (si hace falta, tres rangos ``A3:F100``, ``A101:F200``, ``A201:F280``).
2. Guardar la respuesta JSON completa en ``tools/_mcp_range_pull.json``.
3. Ejecutar::

     python tools/ingest_mcp_read_range_json.py tools/_mcp_range_pull.json \\
       -o ..\\beon-pbi\\Softys\\qa\\manual-cases\\planilla-catalog.json

Alternativa CSV: ``python tools/merge_mcp_catalog.py <out.json> part1.csv part2.csv``
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT.parent / "beon-pbi" / "Softys" / "qa" / "manual-cases" / "planilla-catalog.json",
    )
    parser.add_argument(
        "--mcp-json",
        type=Path,
        default=ROOT / "tools" / "_mcp_range_pull.json",
    )
    args = parser.parse_args()
    if not args.mcp_json.is_file():
        print(f"Falta {args.mcp_json}; seguir pasos MCP en el docstring.", file=sys.stderr)
        return 2
    import subprocess

    cmd = [
        sys.executable,
        str(ROOT / "tools" / "ingest_mcp_read_range_json.py"),
        str(args.mcp_json),
        "-o",
        str(args.output),
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
