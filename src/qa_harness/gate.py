from __future__ import annotations

from pathlib import Path
from .common import CODES, ContractError, aggregate, file_hash, read_json, verify_artifacts
from .contract import load_manifest, validate_named
from .provenance import harness_identity
from .reporting import load_report
from .runner import capture, blockers


def evaluate(root, path, decisions_path=None):
    root, path = Path(root).resolve(), Path(path).resolve()
    report = load_report(path)
    manifest = load_manifest(root, report["manifest_path"])
    issues, states = [], []
    current = capture(root, manifest, report["manifest_path"])
    if file_hash(root / report["manifest_path"]) != report["manifest_sha256"] or manifest != report["manifest"]:
        raise ContractError("Manifiesto distinto al evaluado")
    before = report["identity_before"]
    if current["commit"] != before["commit"] or current["tree_sha256"] != before["tree_sha256"]:
        raise ContractError("Commit, especificaciones o archivos difieren de la evidencia")
    if report["harness"]["source_sha256"] != harness_identity()["source_sha256"]:
        raise ContractError("El reporte fue producido por otra revision del harness")
    if current["dirty"] or report["exploratory"] or report["scope_changed"] or not before["commit"]:
        issues.append("Evidencia exploratoria, checkout modificado o sin commit")
        states.append("incomplete")
    if manifest["policy"]["require_specification"] and (
        not manifest["specifications"] or any(s["status"] != "approved" for s in manifest["specifications"])
    ):
        issues.append("Conformidad con especificaciones no evaluable")
        states.append("incomplete")
    records = {c["id"]: c for c in report["controls"]}
    required_count = 0
    for control in manifest["controls"]:
        if not control["required"]:
            continue
        required_count += 1
        record = records[control["id"]]
        if blockers(manifest, control):
            states.append("incomplete")
            issues.append(f"{control['id']}: definiciones pendientes")
        state = record["status"]
        # Recalculate from evidence, never trust a hand-edited aggregate.
        if not record["attempts"]:
            state = "incomplete"
        else:
            phase_states = []
            for attempt in record["attempts"]:
                for phase in attempt["phases"]:
                    phase_states.append(phase["status"])
                execution = [p for p in attempt["phases"] if p["phase"] == "execute"]
                if not execution:
                    phase_states.append("incomplete")
                else:
                    actual = {t["id"]: t["status"] for t in execution[0]["tests"]}
                    phase_states.extend(actual.get(b["test_id"], "not_run") for b in control["bindings"])
                needed = [name for name in ("preflight", "setup", "execute", "cleanup") if name in control]
                if set(needed) - {p["phase"] for p in attempt["phases"]}:
                    phase_states.append("incomplete")
            state = aggregate(phase_states)
            if record["flaky"]:
                state = "incomplete"
        if control["id"] not in report["selected_controls"]:
            state = "incomplete"
        states.append(state)
        if state != "passed":
            issues.append(f"{control['id']}: {state}")
    manual = {}
    if decisions_path:
        decisions_path = Path(decisions_path).resolve()
        decisions = read_json(decisions_path)
        validate_named(decisions, "decisions")
        if decisions["run_id"] != report["run_id"] or decisions["report_sha256"] != file_hash(path):
            raise ContractError("Validacion humana pertenece a otra evidencia")
        ids = [m["id"] for m in decisions["manual_results"]]
        if len(ids) != len(set(ids)) or set(ids) - {m["id"] for m in manifest["manual_checks"]}:
            raise ContractError("Validaciones humanas duplicadas o desconocidas")
        for result in decisions["manual_results"]:
            verify_artifacts(result["evidence"], decisions_path.parent)
            manual[result["id"]] = result
    scenarios = {s["id"]: s for s in manifest["scenarios"]}
    for check in manifest["manual_checks"]:
        if not check["required"]:
            continue
        required_count += 1
        result = manual.get(check["id"])
        state = result["status"] if result else "incomplete"
        if any(scenarios[sid]["definition_status"] != "approved" for sid in check["scenario_ids"]):
            state = "incomplete"
        if any(q["status"] == "open" and set(q["scenario_ids"]) & set(check["scenario_ids"]) for q in manifest["questions"]):
            state = "incomplete"
        if result and state == "passed" and result["resolution"] != "verified":
            state = "incomplete"
        states.append(state)
        if state != "passed":
            issues.append(f"{check['id']}: {state}")
    if not required_count:
        states.append("incomplete")
        issues.append("No hay controles requeridos")
    state = aggregate(states)
    return {"status": state, "exit_code": CODES[state], "issues": issues,
            "run_id": report["run_id"], "scope": report["scope"],
            "meaning": "Politica del alcance declarado; no certifica la necesidad de negocio ni autoriza un despliegue"}
