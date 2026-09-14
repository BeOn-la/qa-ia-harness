from __future__ import annotations

import importlib.resources
import re
from pathlib import Path
from . import __version__
from .common import ContractError, contained, read_json


def validate(value, schema, location="$"):
    """Small validator for the explicitly supported JSON Schema vocabulary."""
    if "$ref" in schema:
        raise ContractError("Referencias de schema no soportadas")
    if "type" in schema:
        kinds = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        def matches(kind):
            return {"object": isinstance(value, dict), "array": isinstance(value, list),
                    "string": isinstance(value, str), "integer": type(value) is int,
                    "number": type(value) in (int, float), "boolean": type(value) is bool,
                    "null": value is None}.get(kind, False)
        if not any(matches(kind) for kind in kinds):
            raise ContractError(f"{location}: tipo invalido")
    if "const" in schema and value != schema["const"]:
        raise ContractError(f"{location}: version/valor incompatible")
    if "enum" in schema and value not in schema["enum"]:
        raise ContractError(f"{location}: valor no permitido")
    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - set(value)
        if missing:
            raise ContractError(f"{location}: faltan {', '.join(sorted(missing))}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise ContractError(f"{location}: campos desconocidos {sorted(set(value) - set(properties))}")
        for key, item in value.items():
            if key in properties:
                validate(item, properties[key], location + "." + key)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ContractError(f"{location}: lista vacia/no suficiente")
        if len(value) > schema.get("maxItems", 1000000):
            raise ContractError(f"{location}: lista demasiado larga")
        if schema.get("uniqueItems") and len({repr(item) for item in value}) != len(value):
            raise ContractError(f"{location}: elementos duplicados")
        for index, item in enumerate(value):
            validate(item, schema.get("items", {}), f"{location}[{index}]")
    if isinstance(value, str):
        if len(value.strip()) < schema.get("minLength", 0):
            raise ContractError(f"{location}: texto vacio")
        if schema.get("pattern") and not re.search(schema["pattern"], value):
            raise ContractError(f"{location}: formato invalido")
    if type(value) in (int, float):
        if value < schema.get("minimum", float("-inf")) or value > schema.get("maximum", float("inf")):
            raise ContractError(f"{location}: fuera de rango")


def schema_for(name):
    with importlib.resources.files("qa_harness.schemas").joinpath(name + ".json").open("r", encoding="utf-8") as stream:
        import json
        return json.load(stream)


def validate_named(value, name):
    validate(value, schema_for(name))


def unique(items, label):
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        raise ContractError(f"IDs duplicados: {label}")
    return {item["id"]: item for item in items}


def load_manifest(root, path):
    root = Path(root).resolve()
    source = contained(root, path, exists=True)
    manifest = read_json(source)
    validate_named(manifest, "manifest")
    if manifest["harness_version"] != __version__:
        raise ContractError(f"Se requiere harness {manifest['harness_version']}; instalado {__version__}")
    contained(root, manifest["qrd"], exists=True)
    specs = unique(manifest["specifications"], "specifications")
    scenarios = unique(manifest["scenarios"], "scenarios")
    controls = unique(manifest["controls"], "controls")
    unique(manifest["manual_checks"], "manual_checks")
    questions = unique(manifest["questions"], "questions")
    texts = {}
    for spec_id, spec in specs.items():
        texts[spec_id] = contained(root, spec["path"], exists=True).read_text(encoding="utf-8-sig")
    for scenario in scenarios.values():
        if scenario["definition_status"] == "approved":
            if not scenario.get("expected") or not scenario.get("approved_by") or not scenario.get("approved_at"):
                raise ContractError(f"{scenario['id']}: aprobacion sin esperado/autor/fecha")
        if scenario["kind"] == "business" and scenario["definition_status"] == "approved" and not scenario["references"]:
            raise ContractError(f"{scenario['id']}: criterio de negocio aprobado sin fuente")
        for ref in scenario["references"]:
            if ref["specification"] not in specs:
                raise ContractError(f"{scenario['id']}: especificacion inexistente")
            if ref["locator"] not in texts[ref["specification"]]:
                raise ContractError(f"{scenario['id']}: localizador no encontrado: {ref['locator']}")
            if scenario["definition_status"] == "approved" and specs[ref["specification"]]["status"] != "approved":
                raise ContractError(f"{scenario['id']}: fuente pendiente")
    for question in questions.values():
        if set(question["scenario_ids"]) - set(scenarios):
            raise ContractError("Pregunta referencia escenarios inexistentes")
        if question["status"] == "resolved" and not question.get("decision"):
            raise ContractError("Pregunta resuelta sin decision")
    for profile in manifest["profiles"]:
        if profile["name"].lower() in {"prod", "production", "produccion", "productivo"}:
            raise ContractError("Produccion no es un perfil permitido")
        for name in profile["required_env"] + profile["secret_env"]:
            if name not in profile["pass_env"]:
                raise ContractError(f"Variable no declarada en pass_env: {name}")
        if profile.get("sql_target"):
            target = profile["sql_target"]
            if profile.get("sql_access") not in {"read_only", "isolated_write"}:
                raise ContractError("SQL requiere sql_access=read_only o isolated_write")
            for name in (target["server_env"], target["database_env"]):
                if name not in profile["required_env"]:
                    raise ContractError("SQL requiere servidor/base explicitos")
            if not target["expected_principals"]:
                raise ContractError("SQL requiere principal esperado")
            if profile["sql_access"] == "isolated_write":
                if profile["kind"] not in {"local", "staging"}:
                    raise ContractError("Escritura aislada solo se permite en local o staging")
                if not profile.get("write_scope"):
                    raise ContractError("Escritura aislada requiere write_scope")
            contained(root, target["baseline"], exists=True)
            for migration in target["migrations"]:
                contained(root, migration, exists=True)
    if len({p["name"] for p in manifest["profiles"]}) != len(manifest["profiles"]):
        raise ContractError("Perfiles duplicados")
    mapped = set()
    for control in controls.values():
        if set(control["profiles"]) - {p["name"] for p in manifest["profiles"]}:
            raise ContractError("Control referencia perfil inexistente")
        if set(control["scenario_ids"]) - set(scenarios):
            raise ContractError("Control referencia escenario inexistente")
        bindings = control["bindings"]
        if {b["scenario_id"] for b in bindings} != set(control["scenario_ids"]):
            raise ContractError(f"{control['id']}: mapeo de escenarios incompleto")
        if len({(b["scenario_id"], b["test_id"]) for b in bindings}) != len(bindings):
            raise ContractError("Bindings duplicados")
        mapped.update(control["scenario_ids"])
        for phase in ("preflight", "setup", "execute", "cleanup"):
            if phase not in control:
                continue
            command = control[phase]
            contained(root, command["cwd"], exists=True)
            for arg in command["argv"]:
                unknown = re.findall(r"\{([^{}]+)\}", arg)
                if set(unknown) - {"python", "report", "run_id", "root"}:
                    raise ContractError("Placeholder de comando desconocido")
        if "setup" in control and "cleanup" not in control:
            raise ContractError("Setup requiere limpieza explicita")
        if any(p.get("sql_target") for p in manifest["profiles"] if p["name"] in control["profiles"]):
            if "preflight" not in control or control["preflight"]["format"] != "json":
                raise ContractError("SQL requiere preflight JSON con identidad efectiva")
            for profile in manifest["profiles"]:
                if profile["name"] in control["profiles"] and profile.get("sql_target") and profile["sql_access"] == "read_only":
                    if "setup" in control or "cleanup" in control:
                        raise ContractError("Un perfil SQL read_only no puede declarar setup ni cleanup")
    for manual in manifest["manual_checks"]:
        if set(manual["scenario_ids"]) - set(scenarios):
            raise ContractError("Control manual referencia escenario inexistente")
        mapped.update(manual["scenario_ids"])
    if set(scenarios) - mapped:
        raise ContractError("Escenarios sin control automatico o manual; declarar el pendiente en manual_checks")
    return manifest
