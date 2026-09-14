"""Verify demonstrations using the public core. No real product is selected."""
import json
import os
from pathlib import Path
import sys
import uuid

from qa_harness.common import write_json
from qa_harness.reporting import load_report
from qa_harness.runner import run

ROOT = Path(__file__).resolve().parent


def verify(kind):
    root = ROOT / kind
    profile = "local" if kind == "api" else "disposable"
    outcomes = []
    previous = os.environ.get("QA_DEMO_BUG")
    try:
        for mode, expected in (("0", 0), ("1", 1)):
            os.environ["QA_DEMO_BUG"] = mode
            report, directory = run(root, "qa.json", profile,
                                    output=f".qa-runs/demo-{mode}-{uuid.uuid4().hex}",
                                    allow_isolated_write=(kind == "sql"))
            load_report(directory / "report.json")
            if report["exit_code"] != expected:
                raise RuntimeError(f"{kind}: esperado {expected}, obtenido {report['exit_code']}: {directory}")
            if kind == "sql":
                phases = report["controls"][0]["attempts"][0]["phases"]
                if phases[-1]["phase"] != "cleanup" or phases[-1]["status"] != "passed":
                    raise RuntimeError("SQL sin limpieza comprobada")
            outcomes.append({"fault_enabled": mode == "1", "expected_exit": expected,
                             "actual_exit": report["exit_code"], "report": str(directory / "report.json"),
                             "exploratory": report["exploratory"]})
    finally:
        if previous is None:
            os.environ.pop("QA_DEMO_BUG", None)
        else:
            os.environ["QA_DEMO_BUG"] = previous
    summary = {"kind": kind, "validation": "passed", "runs": outcomes,
               "limitation": "Synthetic consumer, not a BeOn pilot"}
    write_json(root / ".qa-runs/verification.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    verify(sys.argv[1] if len(sys.argv) > 1 else "api")
