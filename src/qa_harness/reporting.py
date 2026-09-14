from __future__ import annotations

from pathlib import Path
from .common import ContractError, aggregate, fingerprint, read_json, verify_artifacts
from .contract import validate_named
from .parsers import parse_results


def load_report(path):
    path = Path(path).resolve()
    report = read_json(path)
    validate_named(report, "report")
    expected = fingerprint({k: v for k, v in report.items() if k != "integrity_sha256"})
    if report["integrity_sha256"] != expected:
        raise ContractError("Reporte alterado")
    control_ids = [c["id"] for c in report["controls"]]
    if len(set(control_ids)) != len(control_ids) or set(control_ids) != {c["id"] for c in report["manifest"]["controls"]}:
        raise ContractError("Inventario de controles inconsistente")
    if set(report["selected_controls"]) - set(control_ids):
        raise ContractError("Seleccion inconsistente")
    for control in report["controls"]:
        for attempt in control["attempts"]:
            phase_names = [p["phase"] for p in attempt["phases"]]
            if len(set(phase_names)) != len(phase_names):
                raise ContractError("Fases duplicadas")
            for phase in attempt["phases"]:
                verify_artifacts(phase["artifacts"], path.parent)
                raw = [a for a in phase["artifacts"] if Path(a["path"]).name in ("results.json", "results.xml")]
                if phase["tests"] or phase["status"] == "passed":
                    if len(raw) != 1:
                        raise ContractError("Resultado sin evidencia original")
                    raw_path = path.parent / raw[0]["path"]
                    tests, metadata = parse_results(raw_path, "json" if raw_path.suffix == ".json" else "junit",
                                                    attempt["run_id"], control["id"], phase["phase"])
                    if tests != phase["tests"] or metadata != phase["metadata"]:
                        raise ContractError("Resultados normalizados no coinciden con evidencia")
                    if phase["status"] == "passed" and aggregate(t["status"] for t in tests) != "passed":
                        raise ContractError("Aprobacion incompatible con casos originales")
    return report


def cell(value):
    import html
    return html.escape(str(value)).replace("|", "\\|").replace("\n", "<br>").replace("\r", "")


def markdown(report):
    manifest = report["manifest"]
    lines = [
        f"# QA: {cell(report['product'])}",
        "",
        f"Alcance: {cell(report['scope'])}. Perfil: {cell(report['profile'])}.",
        f"Resultado automatico: **{report['status']}** (salida {report['exit_code']}).",
        "**Esto no constituye aprobacion de negocio ni autorizacion de merge.**",
        "",
        f"- Ejecucion: {report['run_id']}",
        f"- Commit evaluado: {report['identity_before']['commit'] or 'sin commit'}",
        f"- Exploratoria: {report['exploratory']}",
        f"- Cambio durante ejecucion: {report['scope_changed']}",
        f"- Arbol: {report['identity_before']['tree_sha256']}",
        f"- Harness: {report['harness']['version']} / {report['harness']['source_sha256']}",
        f"- Periodo UTC: {report['started_at']} a {report['finished_at']}",
        "",
        "## Controles",
        "",
        "| Control | Requerido | Estado | Inestable | Motivo |",
        "|---|---|---|---|---|",
    ]
    for control in report["controls"]:
        lines.append(f"| {cell(control['id'])} | {control['required']} | {control['status']} | {control['flaky']} | {cell(control['reason'])} |")
    lines += ["", "## Ejecucion y evidencia", "",
              "| Control / intento / fase | Estado | Salida | Casos | Detalle / evidencia |",
              "|---|---|---|---|---|"]
    for control in report["controls"]:
        for index, attempt in enumerate(control["attempts"], 1):
            for phase in attempt["phases"]:
                artifacts = ", ".join(a["path"] for a in phase["artifacts"])
                lines.append(f"| {cell(control['id'])} / {index} / {phase['phase']} | {phase['status']} | {phase['exit_code']} | {len(phase['tests'])} | {cell(phase['message'])} {cell(artifacts)} |")
    lines += ["", "## Trazabilidad", "", "| Escenario | Definicion | Fuente | Tests declarados |", "|---|---|---|---|"]
    for scenario in manifest["scenarios"]:
        refs = ", ".join(r["specification"] + "#" + r["locator"] for r in scenario["references"])
        bindings = [b["test_id"] for c in manifest["controls"] for b in c["bindings"] if b["scenario_id"] == scenario["id"]]
        lines.append(f"| {cell(scenario['id'])} | {scenario['definition_status']} | {cell(refs or 'sin especificacion')} | {cell(', '.join(bindings) or 'manual / pendiente')} |")
    lines += ["", "## Validaciones humanas pendientes", ""]
    lines += [f"- {cell(m['id'])}: {cell(m['action'])} (resultado no incluido en esta ejecucion automatica)." for m in manifest["manual_checks"]]
    if not manifest["manual_checks"]:
        lines.append("No hay controles manuales declarados; no equivale a validacion de negocio.")
    lines += ["", "## Preguntas y exclusiones", ""]
    lines += [f"- {cell(q['id'])}: {cell(q['question'])} — {q['status']}." for q in manifest["questions"]]
    lines += [f"- Fuera: {cell(e['description'])}. Motivo: {cell(e['reason'])}." for e in manifest["exclusions"]]
    lines += ["", "Las inferencias y hallazgos de revision se mantienen separados en el QRD/registro de hallazgos.",
              "Reportes y logs conservados pueden estar redactados; sus hashes corresponden a la evidencia conservada.", ""]
    return "\n".join(lines)
