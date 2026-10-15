"""Enlace planilla (catálogo Excel) ↔ resultados de corrida del harness (sin cambiar oráculos)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .planilla_qa import (
    FILTER_PHRASE_TO_ID,
    KPI_TITLE_TO_ID,
    _norm_tablero,
    _norm_text,
    _tablero_lookup_key,
    infer_automation_binding,
)


def load_planilla_bindings(path: Path | None) -> dict[str, Any] | None:
    if not path or not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return None
    return data


def _match_rule(
    case: dict[str, Any],
    rule: dict[str, Any],
    *,
    tablero_aliases: dict[str, str] | None,
) -> bool:
    m = rule.get("match") or {}
    caso = case.get("caso_de_prueba") or ""
    norm_caso = _norm_text(caso)
    tablero = case.get("tablero") or ""
    tab_key = _tablero_lookup_key(tablero, tablero_aliases)
    tipo = _norm_text(case.get("tipo_prueba") or "")

    if m.get("sheet_row") is not None and int(case.get("sheet_row") or 0) != int(m["sheet_row"]):
        return False
    if m.get("tablero"):
        want = _tablero_lookup_key(str(m["tablero"]), tablero_aliases)
        if tab_key != want:
            return False
    if m.get("tipo_prueba"):
        if tipo != _norm_text(str(m["tipo_prueba"])):
            return False
    if m.get("caso_regex"):
        if not re.search(str(m["caso_regex"]), caso, flags=re.IGNORECASE):
            return False
    if m.get("caso_contains"):
        parts = m["caso_contains"]
        if isinstance(parts, str):
            parts = [parts]
        if not any(_norm_text(p) in norm_caso for p in parts):
            return False
    if m.get("caso_equals"):
        if norm_caso != _norm_text(str(m["caso_equals"])):
            return False
    return bool(m)


def binding_from_rule(rule: dict[str, Any], case: dict[str, Any]) -> dict[str, Any] | None:
    raw = rule.get("binding")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    out = dict(raw)
    tab = _norm_tablero(case.get("tablero") or "")
    out.setdefault("tablero", tab)
    return out


def resolve_planilla_binding(
    case: dict[str, Any],
    bindings_doc: dict[str, Any] | None,
    *,
    tablero_aliases: dict[str, str] | None = None,
    visuales: dict[str, Any] | None = None,
    page_visual_state: Any | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """
    Devuelve (binding, meta).
    meta puede incluir cobertura_harness, nota, regla_id.
    """
    explicit = case.get("harness_binding")
    if isinstance(explicit, dict) and explicit.get("capa"):
        b = dict(explicit)
        b.setdefault("tablero", _norm_tablero(case.get("tablero") or ""))
        return b, {"origen": "catalogo.harness_binding"}

    if visuales is not None and page_visual_state is not None:
        from .planilla_visual_match import PageVisualState, try_match_planilla_visual

        state = page_visual_state
        if not isinstance(state, PageVisualState):
            state = page_visual_state  # duck-typed .take()
        vb, vmeta = try_match_planilla_visual(
            case,
            visuales,
            tablero_aliases=tablero_aliases,
            page_state=state,
        )
        if vb:
            return vb, vmeta

    if bindings_doc:
        for rule in bindings_doc.get("reglas") or []:
            if not _match_rule(case, rule, tablero_aliases=tablero_aliases):
                continue
            meta = {
                "origen": "planilla-harness-bindings",
                "regla_id": rule.get("id"),
                "cobertura_harness": rule.get("cobertura_harness"),
                "nota": rule.get("nota"),
            }
            b = binding_from_rule(rule, case)
            return b, meta

    b = infer_automation_binding(
        case.get("caso_de_prueba") or "",
        case.get("tipo_prueba") or "",
        case.get("tablero") or "",
    )
    return b, {"origen": "inferido_codigo"} if b else None


def default_kpi_phrases() -> dict[str, str]:
    return dict(KPI_TITLE_TO_ID)


def default_filter_phrases() -> list[tuple[str, str]]:
    return list(FILTER_PHRASE_TO_ID)


def build_linkage_report(
    catalog: dict[str, Any],
    *,
    kpi: dict[str, Any] | None,
    filtros: dict[str, Any] | None,
    visuales: dict[str, Any] | None,
    bindings_doc: dict[str, Any] | None,
    tablero_aliases: dict[str, str] | None,
    automation_index: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    from .planilla_qa import _case_result_key, _lookup_automation

    filas: list[dict[str, Any]] = []
    keys_con_catalogo: set[str] = set()

    from .planilla_visual_match import PageVisualState

    page_visual_states: dict[str, PageVisualState] = {}
    for case in catalog.get("cases") or []:
        tab_key = _tablero_lookup_key(case.get("tablero") or "", tablero_aliases)
        pv_state = page_visual_states.setdefault(tab_key, PageVisualState())
        binding, meta = resolve_planilla_binding(
            case,
            bindings_doc,
            tablero_aliases=tablero_aliases,
            visuales=visuales,
            page_visual_state=pv_state,
        )
        auto = _lookup_automation(binding, automation_index, tablero_aliases=tablero_aliases)
        ck = _case_result_key(case)
        keys_con_catalogo.add(ck)
        cobertura = (meta or {}).get("cobertura_harness")
        if cobertura is None:
            if binding is None:
                cobertura = "manual_o_sin_regla"
            elif auto is None:
                cobertura = "regla_sin_resultado_corrida"
            elif auto.get("veredicto") == "no aplica":
                cobertura = "harness_no_aplica_en_hoja"
            else:
                cobertura = "harness"
        filas.append(
            {
                "sheet_row": case.get("sheet_row"),
                "caso_de_prueba": case.get("caso_de_prueba"),
                "tablero": case.get("tablero"),
                "tipo_prueba": case.get("tipo_prueba"),
                "case_key": ck,
                "binding": binding,
                "enlace": meta,
                "cobertura_harness": cobertura,
                "veredicto": (auto or {}).get("veredicto"),
                "capa": (binding or {}).get("capa"),
            }
        )

    harness_sin_fila: list[dict[str, Any]] = []
    for key, auto in automation_index.items():
        if auto.get("veredicto") not in ("fallido", "correcto"):
            continue
        pk, capa, internal = key
        if capa == "visuales_resumen":
            continue
        harness_sin_fila.append(
            {
                "page_key": pk,
                "capa": capa,
                "id_interno": internal,
                "veredicto": auto.get("veredicto"),
                "detalle": (auto.get("detalle") or "")[:200],
                "lectura_qa": auto.get("lectura_qa"),
                "nombre_filtro": auto.get("nombre_filtro"),
                "kpi_id": auto.get("kpi_id"),
            }
        )

    resumen = {
        "filas_catalogo": len(filas),
        "con_binding": sum(1 for f in filas if f.get("binding")),
        "con_veredicto_corrida": sum(
            1
            for f in filas
            if f.get("veredicto") in ("correcto", "fallido")
        ),
        "manual_o_sin_regla": sum(
            1 for f in filas if f.get("cobertura_harness") == "manual_o_sin_regla"
        ),
        "no_aplica_en_hoja": sum(
            1 for f in filas if f.get("cobertura_harness") == "harness_no_aplica_en_hoja"
        ),
        "harness_ok_o_error": sum(
            1 for f in filas if f.get("cobertura_harness") == "harness"
        ),
        "resultados_corrida_sin_fila_catalogo": len(harness_sin_fila),
    }

    return {
        "schema_version": 1,
        "resumen": resumen,
        "filas": filas,
        "corrida_sin_fila_catalogo": harness_sin_fila,
    }
