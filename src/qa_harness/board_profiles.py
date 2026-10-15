from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import ContractError
from .sql_profiles import resolve_under

_PBIP_ARTIFACT_RE = re.compile(
    r"\.pbip\b|\.report\b|\.semanticmodel\b",
    re.IGNORECASE,
)


def list_board_ids(config: dict[str, Any]) -> list[str]:
    boards = config.get("boards")
    if isinstance(boards, dict) and boards:
        return sorted(boards.keys())
    if config.get("pbi_qa"):
        return ["legacy"]
    return []


def resolve_board(config: dict[str, Any], board_id: str | None) -> tuple[str, dict[str, Any]]:
    boards = config.get("boards")
    if isinstance(boards, dict) and boards:
        chosen = board_id or config.get("default_board")
        if not isinstance(chosen, str) or chosen not in boards:
            known = ", ".join(sorted(boards.keys())) or "(vacío)"
            raise ContractError(
                f"Tablero desconocido o sin default_board. Recibido: {board_id!r}. Disponibles: {known}"
            )
        entry = boards[chosen]
        if not isinstance(entry, dict):
            raise ContractError(f"boards.{chosen} debe ser un objeto.")
        return chosen, entry

    legacy = config.get("pbi_qa")
    if isinstance(legacy, dict):
        return "legacy", legacy

    raise ContractError(
        "Falta configuración de tableros: usar 'boards' + 'default_board' en .qa-profiles.local.json"
    )


def board_qa_root(harness_root: Path, board: dict[str, Any]) -> Path:
    raw = board.get("board_qa_root")
    if not isinstance(raw, str) or not raw.strip():
        raise ContractError("board_qa_root requerido en la entrada del tablero.")
    return resolve_under(harness_root, raw)


def consumer_repo_root(harness_root: Path, board: dict[str, Any]) -> Path:
    raw = board.get("consumer_repo_root") or board.get("beon_pbi_root")
    if not isinstance(raw, str) or not raw.strip():
        raise ContractError("consumer_repo_root requerido en la entrada del tablero.")
    return resolve_under(harness_root, raw)


def pbip_path(harness_root: Path, board: dict[str, Any]) -> Path:
    repo = consumer_repo_root(harness_root, board)
    rel = board.get("pbip_relative") or board.get("pbip_manifest")
    if not isinstance(rel, str) or not rel.strip():
        raise ContractError("pbip_relative requerido (ruta al .pbip desde consumer_repo_root).")
    path = (repo / rel).resolve()
    if not path.is_file():
        raise ContractError(f"No existe el PBIP configurado: {path}")
    return path


def kpi_catalog_root(harness_root: Path, board: dict[str, Any]) -> Path:
    raw = board.get("kpi_catalog_root")
    if isinstance(raw, str) and raw.strip():
        return resolve_under(harness_root, raw)
    qa = board_qa_root(harness_root, board)
    candidate = qa.parent.parent / "qa"
    if (candidate / "kpi-catalog.yml").is_file():
        return candidate
    repo = consumer_repo_root(harness_root, board)
    fallback = repo / "qa"
    if (fallback / "kpi-catalog.yml").is_file():
        return fallback
    raise ContractError("No se encontró kpi-catalog.yml (definir kpi_catalog_root en boards.<id>).")


def scope_confluence_url(board: dict[str, Any]) -> str | None:
    url = board.get("scope_confluence_url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    return None


def sql_framework_root(harness_root: Path, config: dict[str, Any], board: dict[str, Any]) -> Path:
    raw = board.get("framework_root") or config.get("sql_framework_root")
    if not isinstance(raw, str) or not raw.strip():
        raise ContractError("framework_root o sql_framework_root requerido.")
    return resolve_under(harness_root, raw)


def _parse_simple_yaml(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    return out


def read_board_yml_metadata(board_qa: Path) -> dict[str, str | None]:
    yml = board_qa / "board.yml"
    if not yml.is_file():
        return {"version_id": None, "label": None, "pbip_manifest": None}
    parsed = _parse_simple_yaml(yml)
    return {
        "version_id": parsed.get("version_id"),
        "label": parsed.get("label"),
        "pbip_manifest": parsed.get("pbip_manifest"),
    }


def pbip_bundle_paths(harness_root: Path, board: dict[str, Any]) -> dict[str, Path]:
    repo = consumer_repo_root(harness_root, board)
    pbip_rel = board.get("pbip_relative") or board.get("pbip_manifest")
    if not isinstance(pbip_rel, str) or not pbip_rel.strip():
        raise ContractError("pbip_relative requerido en la entrada del tablero.")
    pbip = (repo / pbip_rel).resolve()
    parent = pbip.parent
    stem = pbip.stem
    report_rel = board.get("report_relative")
    if isinstance(report_rel, str) and report_rel.strip():
        report = (repo / report_rel).resolve()
    else:
        report = (parent / f"{stem}.Report").resolve()
    semantic = (parent / f"{stem}.SemanticModel").resolve()
    return {
        "pbip": pbip,
        "report": report,
        "semantic_model": semantic,
        "bundle_dir": parent.resolve(),
    }


def _normalize_ref_text(ref: str) -> str:
    text = ref.strip().strip('"').strip("'")
    if text.startswith("@"):
        text = text[1:].lstrip()
    return text.replace("\\", "/").lower()


def _looks_like_board_path(ref: str) -> bool:
    norm = _normalize_ref_text(ref)
    return "/" in norm or _PBIP_ARTIFACT_RE.search(norm) is not None


def _suffix_match(ref_norm: str, path: Path) -> bool:
    parts = path.as_posix().lower().split("/")
    for width in range(1, min(5, len(parts)) + 1):
        suffix = "/".join(parts[-width:])
        if suffix and suffix in ref_norm:
            return True
    return path.name.lower() in ref_norm


def ref_matches_board_bundle(ref: str, bundle: dict[str, Path]) -> bool:
    ref_norm = _normalize_ref_text(ref)
    for key in ("pbip", "report", "semantic_model", "bundle_dir"):
        if _suffix_match(ref_norm, bundle[key]):
            return True
    return False


def find_board_yml_from_ref(ref_path: Path) -> Path | None:
    probe = ref_path
    if not probe.is_absolute():
        probe = ref_path.resolve(strict=False)
    for parent in [probe, *probe.parents]:
        direct = parent / "board.yml"
        if parent.name == "qa" and direct.is_file():
            return direct
        nested = parent / "qa" / "board.yml"
        if nested.is_file():
            return nested
    return None


def _resolve_ref_path(harness_root: Path, config: dict[str, Any], ref: str) -> Path:
    text = ref.strip().strip('"').strip("'")
    if text.startswith("@"):
        text = text[1:].lstrip()
    raw = Path(text)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    candidates.append(harness_root / raw)
    candidates.append(harness_root.parent / raw)
    boards = config.get("boards")
    if isinstance(boards, dict):
        for entry in boards.values():
            if not isinstance(entry, dict):
                continue
            try:
                repo = consumer_repo_root(harness_root, entry)
            except ContractError:
                continue
            stripped = text.replace("\\", "/")
            for prefix in ("beon-pbi/", "../beon-pbi/"):
                if stripped.lower().startswith(prefix.lower()):
                    stripped = stripped[len(prefix) :]
            candidates.append(repo / stripped)
            candidates.append(repo / Path(stripped).name)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        if resolved.exists():
            return resolved
    return raw


def _board_id_for_qa_root(harness_root: Path, config: dict[str, Any], qa_root: Path) -> str | None:
    boards = config.get("boards")
    if not isinstance(boards, dict):
        return None
    target = qa_root.resolve()
    for bid, entry in boards.items():
        if not isinstance(entry, dict):
            continue
        try:
            if board_qa_root(harness_root, entry).resolve() == target:
                return bid
        except ContractError:
            continue
    return None


def _optional_bundle(harness_root: Path, entry: dict[str, Any]) -> dict[str, Path] | None:
    try:
        return pbip_bundle_paths(harness_root, entry)
    except ContractError:
        return None


def resolve_board_from_ref(
    harness_root: Path,
    config: dict[str, Any],
    args: str | None,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Resuelve tablero por ID, ruta arrastrada (.Report/.pbip/.SemanticModel) o default_board."""
    if not args or not str(args).strip():
        board_id, entry = resolve_board(config, None)
        qa = board_qa_root(harness_root, entry)
        meta = read_board_yml_metadata(qa)
        bundle = _optional_bundle(harness_root, entry)
        return board_id, entry, _resolution_context(args, meta, bundle, qa, "default_board")

    text = str(args).strip()
    boards = config.get("boards")
    if isinstance(boards, dict) and not _looks_like_board_path(text):
        first = text.split()[0]
        if first in boards:
            board_id, entry = resolve_board(config, first)
            qa = board_qa_root(harness_root, entry)
            meta = read_board_yml_metadata(qa)
            bundle = _optional_bundle(harness_root, entry)
            return board_id, entry, _resolution_context(text, meta, bundle, qa, "board_id")

    if not isinstance(boards, dict) or not boards:
        raise ContractError("Para resolver por ruta se requiere boards en .qa-profiles.local.json")

    ref_path = _resolve_ref_path(harness_root, config, text)
    matches: list[tuple[str, dict[str, Any]]] = []
    for bid, entry in boards.items():
        if not isinstance(entry, dict):
            continue
        try:
            bundle = pbip_bundle_paths(harness_root, entry)
        except ContractError:
            continue
        if ref_matches_board_bundle(text, bundle):
            matches.append((bid, entry))

    if not matches:
        yml = find_board_yml_from_ref(ref_path)
        if yml is not None:
            qa = yml.parent
            bid = _board_id_for_qa_root(harness_root, config, qa)
            if bid is not None:
                entry = boards[bid]
                bundle = pbip_bundle_paths(harness_root, entry)
                meta = read_board_yml_metadata(qa)
                return bid, entry, _resolution_context(text, meta, bundle, qa, "board_yml")

        known = ", ".join(sorted(boards.keys()))
        raise ContractError(
            "No se pudo asociar la ruta al tablero. "
            f"Arrastrá .Report / .pbip / .SemanticModel registrado en boards.* o usá board_id ({known}). "
            f"Ref: {text[:200]}"
        )

    if len(matches) > 1:
        ids = ", ".join(m[0] for m in matches)
        raise ContractError(f"La ruta coincide con más de un tablero: {ids}. Acotá la ruta o usá board_id.")

    board_id, entry = matches[0]
    qa = board_qa_root(harness_root, entry)
    meta = read_board_yml_metadata(qa)
    bundle = pbip_bundle_paths(harness_root, entry)
    return board_id, entry, _resolution_context(text, meta, bundle, qa, "path_ref")


def _resolution_context(
    ref: str | None,
    meta: dict[str, str | None],
    bundle: dict[str, Path] | None,
    board_qa: Path,
    resolved_via: str,
) -> dict[str, Any]:
    version_id = meta.get("version_id")
    label = meta.get("label")
    ctx: dict[str, Any] = {
        "resolved_via": resolved_via,
        "board_ref": ref,
        "version_id": version_id,
        "board_yml_label": label,
        "board_qa_root": str(board_qa.resolve()),
        "pbip_path": None,
        "report_path": None,
        "semantic_model_path": None,
    }
    if bundle is not None:
        ctx["pbip_path"] = str(bundle["pbip"])
        ctx["report_path"] = str(bundle["report"])
        ctx["semantic_model_path"] = str(bundle["semantic_model"])
    return ctx
