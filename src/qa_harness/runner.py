from __future__ import annotations

import os
import platform
import sys
import uuid
from pathlib import Path

from .common import (CODES, ContractError, aggregate, contained, file_hash, fingerprint,
                     now, write_json)
from .contract import load_manifest, validate_named
from .process import execute
from .provenance import snapshot, harness_identity


def select_profile(manifest, name):
    for profile in manifest["profiles"]:
        if profile["name"] == name:
            return profile
    raise ContractError("Perfil desconocido; no hay seleccion implicita de entorno")


def blockers(manifest, control):
    scenarios = {s["id"]: s for s in manifest["scenarios"]}
    pending = [sid for sid in control["scenario_ids"] if scenarios[sid]["definition_status"] != "approved"]
    pending += [q["id"] for q in manifest["questions"]
                if q["status"] == "open" and set(q["scenario_ids"]) & set(control["scenario_ids"])]
    return pending


def profile_problems(profile, allow_isolated_write=False):
    problems = [f"Falta variable requerida: {name}" for name in profile["required_env"] if not os.getenv(name)]
    if profile.get("sql_target") and not problems:
        target = profile["sql_target"]
        if os.environ[target["server_env"]] not in target["allowed_connections"]:
            problems.append("Conexion SQL fuera de destinos permitidos")
        if os.environ[target["database_env"]] != target["expected_database"]:
            problems.append("Base SQL fuera de destinos permitidos")
        if profile["sql_access"] == "isolated_write" and not allow_isolated_write:
            problems.append("Escritura SQL aislada requiere --allow-isolated-write")
    return problems


def check(root, manifest_path, profile_name):
    manifest = load_manifest(root, manifest_path)
    profile = select_profile(manifest, profile_name)
    issues = profile_problems(profile)
    for control in manifest["controls"]:
        if profile_name in control["profiles"] and blockers(manifest, control):
            issues.append(f"{control['id']}: definiciones pendientes")
    if not manifest["controls"]:
        issues.append("No hay controles automaticos")
    if not manifest["specifications"]:
        issues.append("Sin especificaciones: conformidad de negocio no evaluada")
    return {"status": "incomplete" if issues else "passed", "issues": issues,
            "product": manifest["product"], "scope": manifest["scope"]}


def capture(root, manifest, manifest_path):
    identity = snapshot(root)
    paths = [manifest_path, manifest["qrd"]] + [spec["path"] for spec in manifest["specifications"]]
    for profile in manifest["profiles"]:
        if profile.get("sql_target"):
            paths += [profile["sql_target"]["baseline"], *profile["sql_target"]["migrations"]]
    git_root = Path(identity["git_root"])
    for raw in paths:
        path = contained(root, raw, exists=True)
        identity["files"][path.relative_to(git_root).as_posix()] = file_hash(path)
    identity["tree_sha256"] = fingerprint(identity["files"])
    return identity


def verify_target(phase, target, root):
    effective = phase["metadata"].get("target", {})
    expected = {"server": target["expected_server"], "database": target["expected_database"],
                "baseline_sha256": file_hash(contained(root, target["baseline"], exists=True))}
    if any(effective.get(k) != v for k, v in expected.items()) or not effective.get("engine_version"):
        phase["status"] = "error"
        phase["message"] = "Preflight SQL sin identidad efectiva, version o baseline coincidentes"
    elif effective.get("principal") not in target["expected_principals"]:
        phase["status"] = "error"
        phase["message"] = "Preflight SQL con principal efectivo no permitido"


def acquire_lock(root, target, run_id):
    directory = contained(root, ".qa-runs/locks")
    directory.mkdir(parents=True, exist_ok=True)
    key = fingerprint([target["expected_server"], target["expected_database"]])
    path = directory / (key + ".json")
    try:
        with path.open("x", encoding="utf-8") as stream:
            import json
            json.dump({"run_id": run_id, "state": "running", "created_at": now(),
                       "server": target["expected_server"], "database": target["expected_database"]}, stream)
    except FileExistsError as exc:
        raise ContractError("Destino ocupado o contaminado; inspeccionar lock y verificar limpieza antes de recuperarlo") from exc
    return path


def run(root, manifest_path, profile_name, selected=None, output=None, retry=0, allow_isolated_write=False):
    root = Path(root).resolve()
    manifest = load_manifest(root, manifest_path)
    profile = select_profile(manifest, profile_name)
    controls = {c["id"]: c for c in manifest["controls"]}
    if selected is None:
        selected = [c["id"] for c in manifest["controls"] if profile_name in c["profiles"]]
    if len(set(selected)) != len(selected) or set(selected) - set(controls):
        raise ContractError("Seleccion duplicada o desconocida")
    if retry not in range(3):
        raise ContractError("retry debe ser 0, 1 o 2")
    run_id = uuid.uuid4().hex
    destination = contained(root, output or f".qa-runs/{run_id}")
    owned = contained(root, ".qa-runs")
    if destination == owned or not destination.is_relative_to(owned) or destination.name == "locks":
        raise ContractError("La salida debe ser un directorio nuevo dentro de .qa-runs/")
    if destination.exists():
        raise ContractError("La salida ya existe; no se sobrescribe evidencia")
    before = capture(root, manifest, manifest_path)
    destination.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": 1, "run_id": run_id, "started_at": now(), "finished_at": "",
              "product": manifest["product"], "scope": manifest["scope"], "profile": profile_name,
              "manifest_path": Path(manifest_path).as_posix(), "manifest_sha256": file_hash(root / manifest_path),
              "manifest": manifest, "selected_controls": selected, "identity_before": before,
              "identity_after": before, "harness": harness_identity(),
              "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                              "declared_env": {k: os.environ.get(k) for k in profile["pass_env"] if k not in profile["secret_env"]},
                              "secret_env": profile["secret_env"]},
              "controls": [], "status": "incomplete", "exit_code": 3, "scope_changed": False,
              "exploratory": before["dirty"], "integrity_sha256": ""}
    problems = profile_problems(profile, allow_isolated_write)
    cancelled = False
    for control in manifest["controls"]:
        record = {"id": control["id"], "required": control["required"],
                  "scenario_ids": control["scenario_ids"], "status": "not_run", "flaky": False,
                  "reason": "", "attempts": []}
        report["controls"].append(record)
        if control["id"] not in selected:
            record["reason"] = "Fuera de la seleccion"
            continue
        pending = blockers(manifest, control)
        if cancelled or pending or problems or profile_name not in control["profiles"]:
            record["status"] = "blocked"
            record["reason"] = "; ".join(problems + pending) or "Perfil incompatible o ejecucion cancelada"
            continue
        lock = None
        if profile.get("sql_target"):
            try:
                lock = acquire_lock(root, profile["sql_target"], run_id)
            except ContractError as exc:
                record["status"], record["reason"] = "blocked", str(exc)
                continue
        contaminated = False
        try:
            for attempt_index in range(retry + 1):
                attempt_id = f"{run_id}-a{attempt_index + 1}"
                attempt = {"run_id": attempt_id, "phases": [], "status": "incomplete"}
                record["attempts"].append(attempt)
                setup_attempted = False
                try:
                    ready = True
                    for phase_name in ("preflight", "setup", "execute"):
                        if phase_name not in control or not ready:
                            continue
                        if phase_name in ("setup", "execute"):
                            setup_attempted = True
                        phase = execute(root, control[phase_name],
                                        destination / control["id"] / f"attempt-{attempt_index + 1}" / phase_name,
                                        attempt_id, control["id"], phase_name, profile)
                        attempt["phases"].append(phase)
                        if phase_name == "preflight" and profile.get("sql_target"):
                            verify_target(phase, profile["sql_target"], root)
                        if phase_name == "execute":
                            ids = {t["id"] for t in phase["tests"]}
                            if any(b["test_id"] not in ids for b in control["bindings"]):
                                if phase["status"] == "passed":
                                    phase["status"] = "incomplete"
                                phase["message"] += " Faltan tests declarados en bindings"
                        ready = phase["status"] == "passed"
                        cancelled = cancelled or phase["status"] == "cancelled"
                except (ContractError, OSError) as exc:
                    attempt["phases"].append({"phase": "execute", "status": "error", "exit_code": None,
                                              "tests": [], "metadata": {}, "artifacts": [],
                                              "message": str(exc), "duration_seconds": 0.0})
                finally:
                    if setup_attempted and "cleanup" in control:
                        try:
                            cleanup = execute(root, control["cleanup"],
                                              destination / control["id"] / f"attempt-{attempt_index + 1}" / "cleanup",
                                              attempt_id, control["id"], "cleanup", profile)
                            attempt["phases"].append(cleanup)
                            contaminated = cleanup["status"] != "passed"
                        except (ContractError, OSError, KeyboardInterrupt):
                            contaminated = True
                            attempt["phases"].append({"phase": "cleanup", "status": "error", "exit_code": None,
                                                      "tests": [], "metadata": {}, "artifacts": [],
                                                      "message": "Limpieza interrumpida o no ejecutable", "duration_seconds": 0.0})
                attempt["status"] = aggregate(p["status"] for p in attempt["phases"])
                if not any(p["phase"] == "execute" for p in attempt["phases"]) and attempt["status"] == "passed":
                    attempt["status"] = "incomplete"
                if attempt["status"] == "passed" or cancelled or contaminated:
                    break
            last = record["attempts"][-1]["status"]
            record["flaky"] = last == "passed" and any(a["status"] != "passed" for a in record["attempts"][:-1])
            record["status"] = "incomplete" if record["flaky"] else aggregate(a["status"] for a in record["attempts"])
            if contaminated:
                record["status"], record["reason"] = "error", "Limpieza no verificada; destino contaminado"
        finally:
            if lock:
                if contaminated:
                    write_json(lock, {"run_id": run_id, "state": "contaminated", "evidence": str(destination)})
                else:
                    lock.unlink()
    after = capture(root, manifest, manifest_path)
    report["identity_after"] = after
    report["scope_changed"] = (before["tree_sha256"], before["commit"]) != (after["tree_sha256"], after["commit"])
    report["exploratory"] = before["dirty"] or after["dirty"] or report["scope_changed"]
    report["status"] = "error" if report["scope_changed"] else aggregate(
        c["status"] for c in report["controls"] if c["id"] in selected)
    report["exit_code"] = CODES[report["status"]]
    report["finished_at"] = now()
    report["integrity_sha256"] = fingerprint({k: v for k, v in report.items() if k != "integrity_sha256"})
    validate_named(report, "report")
    write_json(destination / "report.json", report)
    from .reporting import markdown
    (destination / "report.md").write_text(markdown(report), encoding="utf-8")
    return report, destination
