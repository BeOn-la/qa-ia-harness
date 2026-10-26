from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .common import ContractError


def harness_root(start: Path | None = None) -> Path:
    """Raíz del repo qa-ia-harness (donde vive .qa-profiles.local.json)."""
    if start is None:
        start = Path.cwd()
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "src" / "qa_harness").is_dir():
            return candidate
    raise ContractError(
        "No se detectó la raíz de qa-ia-harness; ejecutar desde el repo o usar --harness-root."
    )


def load_local_profiles_config(root: Path) -> dict[str, Any]:
    path = root / ".qa-profiles.local.json"
    if not path.is_file():
        raise ContractError(
            "Falta .qa-profiles.local.json. Copiar .qa-profiles.local.json.example y ajustar rutas."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"JSON inválido en {path.name}") from exc
    if not isinstance(data, dict):
        raise ContractError(f"{path.name} debe ser un objeto JSON.")
    return data


def resolve_under(root: Path, raw: str) -> Path:
    path = (root / raw).resolve()
    if not path.exists():
        raise ContractError(f"Ruta inexistente: {raw} (resuelto: {path})")
    return path


def profile_entry(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    profiles = config.get("profiles")
    if not isinstance(profiles, dict):
        raise ContractError("profiles ausente en .qa-profiles.local.json")
    entry = profiles.get(profile_name)
    if not isinstance(entry, dict):
        raise ContractError(f"Perfil desconocido: {profile_name}")
    if entry.get("execution") != "allowed":
        raise ContractError(f"Perfil '{profile_name}' no habilitado para ejecución.")
    if profile_name == "production":
        raise ContractError("Producción no es un perfil ejecutable (usar prod-readonly).")
    env_file = entry.get("env_file")
    if not isinstance(env_file, str) or not env_file.strip():
        raise ContractError(f"Perfil '{profile_name}' sin env_file.")
    return entry


def parse_env_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ContractError("Línea inválida en archivo de perfil SQL.")
        name, value = stripped.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name] = value
    return values


@contextmanager
def applied_env_file(root: Path, rel_env_file: str) -> Iterator[None]:
    env_path = root / rel_env_file
    if not env_path.is_file():
        raise ContractError(f"No existe el archivo de perfil: {rel_env_file}")
    new_values = parse_env_lines(env_path.read_text(encoding="utf-8"))
    previous: dict[str, str | None] = {}
    for key, value in new_values.items():
        previous[key] = os.environ.get(key)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, old in previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
