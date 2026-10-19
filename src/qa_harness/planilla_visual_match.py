"""Empareja filas de planilla con casos interpretados de visuales-por-hoja."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .planilla_qa import _norm_tablero, _norm_text, _page_key_from_hoja_result, _tablero_lookup_key


def visual_index_key(caso_visual: dict[str, Any]) -> str:
    lectura = caso_visual.get("lectura_qa") or caso_visual.get("nombre_caso") or ""
    base = _norm_text(lectura)[:72]
    vid = (caso_visual.get("identificador_visual") or "").strip()
    if vid:
        return f"{base}|{vid[:12]}"
    orden = caso_visual.get("orden_en_hoja")
    if orden is not None:
        return f"{base}|o{orden}"
    return base


def _visuals_interpretados(visuales: dict[str, Any] | None, page_key: str) -> list[dict[str, Any]]:
    if not visuales:
        return []
    for hoja in visuales.get("hojas") or []:
        if _page_key_from_hoja_result(hoja) != page_key:
            continue
        out = [
            c
            for c in hoja.get("casos_de_prueba") or []
            if c.get("tipo_caso") == "visual del informe"
        ]
        return sorted(out, key=lambda c: int(c.get("orden_en_hoja") or 0))
    return []


@dataclass
class PageVisualState:
    """Contadores por tipo de match en una hoja (misma pestaña del informe)."""
    slots: dict[str, int] = field(default_factory=dict)

    def take(self, slot: str) -> int:
        n = self.slots.get(slot, 0)
        self.slots[slot] = n + 1
        return n


def _nth_in_caso(caso: str) -> int | None:
    m = re.search(r"\b(\d+)\b", caso)
    if m:
        return int(m.group(1)) - 1
    return None


def _binding_visual(page_key: str, caso_visual: dict[str, Any]) -> dict[str, Any]:
    vkey = visual_index_key(caso_visual)
    return {
        "capa": "visuales",
        "tablero": page_key,
        "visual_key": vkey,
        "lectura_qa": caso_visual.get("lectura_qa"),
        "orden_en_hoja": caso_visual.get("orden_en_hoja"),
    }


def _pick_by_slot(
    pool: list[dict[str, Any]],
    slot: str,
    state: PageVisualState,
    *,
    index: int | None = None,
) -> dict[str, Any] | None:
    if not pool:
        return None
    i = index if index is not None else state.take(slot)
    if i < 0 or i >= len(pool):
        return None
    return pool[i]


def try_match_planilla_visual(
    case: dict[str, Any],
    visuales: dict[str, Any] | None,
    *,
    tablero_aliases: dict[str, str] | None,
    page_state: PageVisualState,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """
    Devuelve (binding, meta) si el caso de planilla corresponde a un visual interpretado.
    """
    caso = case.get("caso_de_prueba") or ""
    norm = _norm_text(caso)
    tab_display = (case.get("tablero") or "").strip()
    page_key = _tablero_lookup_key(tab_display, tablero_aliases)
    visuals = _visuals_interpretados(visuales, page_key)
    if not visuals:
        return None, None

    meta_base = {"origen": "planilla_visual_match", "tablero": tab_display}

    def pool_rol(substr: str) -> list[dict[str, Any]]:
        return [v for v in visuals if substr in _norm_text(v.get("rol_interpretado") or "")]

    def pool_lectura(substr: str) -> list[dict[str, Any]]:
        return [v for v in visuals if substr in _norm_text(v.get("lectura_qa") or "")]

    def pool_tipo(*tipos: str) -> list[dict[str, Any]]:
        tset = {t.casefold() for t in tipos}
        return [v for v in visuals if (v.get("tipo_visual") or "").casefold() in tset]

    # --- Selectores / filtros operativos (no scope-filters.json) ---
    if "selector de all / in stock / listed" in norm:
        def _campos_text(v: dict[str, Any]) -> str:
            return _norm_text(" ".join(v.get("campos_en_consulta") or []))

        p = pool_lectura("parameter full")
        if not p:
            p = [
                v
                for v in visuals
                if v.get("tipo_visual") == "slicer"
                and (
                    "selector kpi" in _campos_text(v)
                    or "parameter full" in _campos_text(v)
                    or (
                        "filtro operativo (filtro)" in _norm_text(v.get("rol_interpretado") or "")
                        and float((v.get("posicion_en_canvas") or {}).get("y") or 999) < 220
                    )
                )
            ]
        v = _pick_by_slot(p, "param_full", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "selector_all_stock_listed"}

    if "selector assortment" in norm or "selector de kpi" in norm:
        p = [v for v in visuals if "bookmark" in _norm_text(v.get("rol_interpretado") or "")]
        if not p:
            p = pool_lectura("parameter full")
        v = _pick_by_slot(p, "selector_kpi", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "selector_kpi"}

    if "selector de cumplimiento" in norm or "cumplimiento / no cumplimiento" in norm:
        p = pool_lectura("cumplimiento") or pool_lectura("parameter")
        v = _pick_by_slot(p, "selector_cumplimiento", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "selector_cumplimiento"}

    if "selector title" in norm or "descripcion /primary" in norm:
        p = pool_lectura("parameter") or pool_lectura("bookmark")
        v = _pick_by_slot(p, "selector_content", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "selector_content_health"}

    if "selector price status" in norm:
        p = pool_lectura("price") + pool_lectura("parameter")
        v = _pick_by_slot(p, "selector_price", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "selector_pricing"}

    if "selector de granularidad" in norm or "granularidad (numeric)" in norm:
        p = pool_lectura("granular") or pool_lectura("numeric")
        v = _pick_by_slot(p, "granularidad", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "granularidad"}

    if "validar filtro de date" in norm:
        p = pool_lectura("año/mes") or pool_lectura("parameter date")
        v = _pick_by_slot(p, "filtro_date", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "filtro_date"}

    if "validar filtro de brand" in norm:
        p = pool_lectura("brand")
        v = _pick_by_slot(p, "filtro_brand", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "filtro_brand"}

    if "aliascategory" in norm:
        p = pool_lectura("dims") or pool_lectura("categor")
        v = _pick_by_slot(p, "filtro_alias", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "filtro_alias"}

    if "power sku" in norm:
        p = pool_lectura("sku")
        v = _pick_by_slot(p, "filtro_sku", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "filtro_sku"}

    if "ean - product name" in norm or "ean - product" in norm:
        p = pool_lectura("sku / name") or pool_lectura("name")
        v = _pick_by_slot(p, "filtro_ean", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "filtro_ean"}

    if "keyword" in norm and "validar filtro" in norm:
        p = pool_lectura("keyword")
        v = _pick_by_slot(p, "filtro_keyword", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "filtro_keyword_vis"}

    # --- Gráficos ---
    if "grafico de barras" in norm or "gráfico de barras" in norm:
        p = [
            v
            for v in visuals
            if (v.get("tipo_visual") or "").casefold() in ("barchart", "clusteredbarchart", "hundredstackedbarchart")
            or "bar" in _norm_text(v.get("tipo_visual") or "")
        ]
        if not p:
            p = [v for v in pool_rol("tarjeta o gráfico kpi") if "bar" in _norm_text(v.get("tipo_visual") or "")]
        v = _pick_by_slot(p, "grafico_barras", page_state, index=_nth_in_caso(caso))
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "grafico_barras"}

    if "grafico evolutivo" in norm or "gráfico evolutivo" in norm:
        p = pool_tipo("lineChart", "areaChart") or [
            v for v in pool_rol("tarjeta o gráfico kpi") if (v.get("tipo_visual") or "").casefold() == "linechart"
        ]
        v = _pick_by_slot(p, "grafico_evolutivo", page_state, index=_nth_in_caso(caso))
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "grafico_evolutivo"}

    # --- Tablas ---
    if "tabla operativa" in norm:
        p = [
            v
            for v in visuals
            if (v.get("tipo_visual") or "").casefold() in ("tableex", "pivottable", "matrix")
            or "tabla" in _norm_text(v.get("rol_interpretado") or "")
            or (
                "tarjeta o gráfico kpi" in _norm_text(v.get("rol_interpretado") or "")
                and (v.get("tipo_visual") or "").casefold() == "tableex"
            )
        ]
        idx = _nth_in_caso(caso)
        slot = "tabla_operativa"
        v = _pick_by_slot(p, slot, page_state, index=idx)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "tabla_operativa"}

    # --- Botones / navegación ---
    if "boton de" in norm or "botón de" in norm:
        target = ""
        if "pricing" in norm:
            target = "pricing"
        elif "multi kpi" in norm:
            target = "multi"
        elif "price status" in norm:
            target = "price"
        elif "price index" in norm:
            target = "index"
        p = pool_rol("acción ir a otra hoja") or pool_rol("accion ir a otra hoja")
        if target:
            filtered = [v for v in p if target in _norm_text(v.get("detalle") or v.get("lectura_qa") or "")]
            if filtered:
                p = filtered
        v = _pick_by_slot(p, f"boton_{target or 'nav'}", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "boton_nav"}

    if "icono de home" in norm:
        p = [
            v
            for v in visuals
            if "navegacion a home" in _norm_text(v.get("rol_interpretado") or "")
        ]
        if not p:
            p = sorted(
                [v for v in visuals if float((v.get("posicion_en_canvas") or {}).get("y") or 999) < 80],
                key=lambda c: float((c.get("posicion_en_canvas") or {}).get("x") or 0),
            )
        v = _pick_by_slot(p, "icono_home", page_state, index=0)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "icono_home"}

    if "flecha de navegacion" in norm:
        p = [
            v
            for v in visuals
            if "navegacion atras" in _norm_text(v.get("rol_interpretado") or "")
        ]
        v = _pick_by_slot(p, "flecha_atras", page_state, index=0)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "flecha_atras"}

    if "iconos de navegacion" in norm:
        p = pool_rol("acción ir a otra hoja") or pool_rol("accion ir a otra hoja")
        p = [v for v in p if "home" not in _norm_text(v.get("detalle") or "")]
        v = _pick_by_slot(p, "iconos_nav_plus", page_state, index=_nth_in_caso(caso))
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "iconos_nav_plus"}

    if "boton de navegacion" in norm or "navegacion +detail" in norm:
        p = pool_rol("acción ir a otra hoja")
        v = _pick_by_slot(p, "nav_detail", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "nav_detail"}

    if "result of the day" in norm:
        p = pool_lectura("result") or pool_rol("tarjeta o gráfico kpi")
        v = _pick_by_slot(p, "result_day", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "result_day"}

    if "position" in norm and "share" in _norm_text(tab_display):
        p = pool_lectura("position") or pool_tipo("card", "cardVisual")
        v = _pick_by_slot(p, "sos_position", page_state)
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "sos_position"}

    if "zona clicable" in norm or "drill" in norm:
        p = pool_rol("zona clicable detalle kpi")
        v = _pick_by_slot(p, "zona_clicable", page_state, index=_nth_in_caso(caso))
        if v:
            return _binding_visual(page_key, v), {**meta_base, "patron": "zona_clicable"}

    return None, None
