"""Adversarial test producer; invoked only inside disposable test repositories."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

mode = os.getenv("FIXTURE_MODE", "pass")
phase = os.environ["QA_PHASE"]
state = Path(".qa-runs")
state.mkdir(exist_ok=True)
if phase == "cleanup":
    (state / "cleanup.marker").write_text("attempted")
if mode == "timeout" and phase == "execute":
    time.sleep(60)
if mode == "interactive":
    input("must never wait for a session")
if mode == "mutate" and phase == "execute":
    Path("spec.md").write_text("RF-001 changed")
if mode == "no-report":
    raise SystemExit(0)
if mode == "malformed":
    Path(os.environ["QA_REPORT_PATH"]).write_text("not json")
    raise SystemExit(0)
status = {"fail": "failed", "error": "error", "skip": "skipped"}.get(mode, "passed")
if mode == "setup-fail" and phase == "setup":
    status = "failed"
if mode == "cleanup-fail" and phase == "cleanup":
    status = "failed"
if mode == "retry" and phase == "execute" and os.environ["QA_RUN_ID"].endswith("a1"):
    status = "failed"
tests = [{"id": "case-1", "status": status}]
if mode in ("empty", "no-assertions"):
    tests = []
if mode == "mixed":
    tests.append({"id": "case-2", "status": "failed"})
if mode == "duplicate":
    tests.append({"id": "case-1", "status": "passed"})
if mode == "unknown-test":
    tests[0]["id"] = "unexpected"
if mode == "secret":
    print(os.environ["FIXTURE_PASSWORD"])
payload = {"schema_version": 1, "run_id": os.environ["QA_RUN_ID"],
           "control_id": os.environ["QA_CONTROL_ID"], "phase": phase, "tests": tests}
if mode == "wrong-run":
    payload["run_id"] = "old-run"
if os.getenv("QA_EXPECTED_SQL_SERVER"):
    payload["metadata"] = {"target": {
        "server": "wrong" if mode == "wrong-target" else os.environ["QA_EXPECTED_SQL_SERVER"],
        "database": os.environ["QA_EXPECTED_SQL_DATABASE"], "engine_version": "fixture",
        "principal": "fixture-principal",
        "baseline_sha256": hashlib.sha256(Path("spec.md").read_bytes()).hexdigest()}}
Path(os.environ["QA_REPORT_PATH"]).write_text(json.dumps(payload), encoding="utf-8")
raise SystemExit(7 if mode == "exit-mismatch" else 0)
