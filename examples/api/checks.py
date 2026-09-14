"""Independent expected examples; XML uses standard JUnit testcase identities."""
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from app import quote

CASES = [
    ("valid", {"quantity": 3, "unit_price_cents": 125}, (200, {"total_cents": 375})),
    ("minimum", {"quantity": 1, "unit_price_cents": 0}, (200, {"total_cents": 0})),
    ("maximum", {"quantity": 10000, "unit_price_cents": 1}, (200, {"total_cents": 10000})),
    ("negative_quantity", {"quantity": -1, "unit_price_cents": 100}, (400, {"error": "invalid_quantity"})),
    ("zero_quantity", {"quantity": 0, "unit_price_cents": 100}, (400, {"error": "invalid_quantity"})),
    ("boolean_quantity", {"quantity": True, "unit_price_cents": 100}, (400, {"error": "invalid_type"})),
    ("negative_price", {"quantity": 2, "unit_price_cents": -1}, (400, {"error": "out_of_range"})),
    ("too_many", {"quantity": 10001, "unit_price_cents": 1}, (400, {"error": "out_of_range"})),
]

def main():
    suite = ET.Element("testsuite", name="quote", tests=str(len(CASES)))
    failed = 0
    for name, payload, expected in CASES:
        case = ET.SubElement(suite, "testcase", classname="quote", name=name)
        actual = quote(payload)
        if actual != expected:
            failed += 1
            ET.SubElement(case, "failure", message="Respuesta distinta al ejemplo aprobado").text = json.dumps(
                {"expected": expected, "actual": actual})
    suite.set("failures", str(failed))
    ET.ElementTree(suite).write(os.environ["QA_REPORT_PATH"], encoding="utf-8", xml_declaration=True)
    print(f"{len(CASES)} casos; {failed} fallidos")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
