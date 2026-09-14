from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

MAX_REPORT_BYTES = 10 * 1024 * 1024
STATUSES = {"passed", "failed", "error", "skipped", "blocked", "not_run", "cancelled", "incomplete"}
CODES = {"passed": 0, "failed": 1, "error": 2, "skipped": 3, "blocked": 3,
         "not_run": 3, "cancelled": 3, "incomplete": 3}


class ContractError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()


def fingerprint(value):
    return digest(canonical(value))


def file_hash(path):
    return digest(Path(path).read_bytes())


def read_json(path):
    path = Path(path)
    if path.stat().st_size > MAX_REPORT_BYTES:
        raise ContractError(f"Archivo demasiado grande: {path.name}")
    try:
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ContractError(f"Clave JSON duplicada: {key}")
                result[key] = value
            return result
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ContractError("Numero JSON invalido")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"JSON invalido: {path.name}") from exc


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def contained(root, raw, *, exists=False):
    root = Path(root).resolve()
    raw_path = Path(raw)
    if raw_path.is_absolute() or ".." in raw_path.parts:
        raise ContractError(f"Se requiere ruta relativa contenida: {raw}")
    result = (root / raw_path).resolve()
    if not result.is_relative_to(root) or ".git" in raw_path.parts:
        raise ContractError(f"Ruta fuera del consumidor: {raw}")
    if exists and not result.exists():
        raise ContractError(f"Falta ruta: {raw}")
    return result


def aggregate(states):
    states = list(states)
    if "error" in states:
        return "error"
    if "failed" in states:
        return "failed"
    if not states or any(state != "passed" for state in states):
        return "incomplete"
    return "passed"


def artifact(path, base):
    path = Path(path)
    return {"path": path.relative_to(base).as_posix(), "sha256": file_hash(path)}


def verify_artifacts(artifacts, base):
    for item in artifacts:
        path = contained(base, item["path"], exists=True)
        if file_hash(path) != item["sha256"]:
            raise ContractError(f"Evidencia alterada: {item['path']}")
