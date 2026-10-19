from __future__ import annotations

import re
import unicodedata
from typing import Any

_ROLES_UX_AL_FINAL = frozenset(
    {
        "elemento de diseño",
        "elemento sin medida",
        "validación estética general",
        "estética general",
    }
)

_ROLES_FILTRO_VISUAL = frozenset(
    {
        "filtro contractual",
        "filtro operativo (filtro)",
    }
)


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "")
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", t.strip().lower())


def caso_incluido_en_planilla(caso: dict[str, Any]) -> bool:
    if caso.get("incluir_en_planilla") is False:
        return False
    if (caso.get("veredicto") or "").strip().lower() == "no aplica" and caso.get(
        "omitir_planilla_por_redundancia"
    ):
        return False
    return True


def dedupe_key_visual_planilla(caso: dict[str, Any], hoja: str) -> str | None:
    rol = _norm(str(caso.get("rol_interpretado") or ""))
    nombre = _norm(str(caso.get("nombre_caso") or caso.get("lectura_qa") or ""))
    kid = caso.get("identificador_indicador") or ""
    fid = caso.get("identificador_filtro") or ""
    if "zona clicable detalle kpi" in rol and kid:
        return f"{hoja}|click_kpi|{kid}"
    if "ir a" in nombre or "acción ir a otra hoja" in rol:
        dest = nombre.split("ir a", 1)[-1].strip() if "ir a" in nombre else nombre
        return f"{hoja}|nav|{dest}"
    if "filtro contractual" in rol and fid:
        return f"{hoja}|filtro_visual|{fid}"
    if nombre:
        return f"{hoja}|nombre|{nombre}"
    return None


def dedupe_visual_cases_for_planilla(
    casos: list[dict[str, Any]],
    hoja: str,
) -> list[dict[str, Any]]:
    """Una fila de planilla por clave semántica; conserva el de menor orden_en_hoja."""
    by_key: dict[str, dict[str, Any]] = {}
    for caso in casos:
        if not caso_incluido_en_planilla(caso):
            continue
        key = dedupe_key_visual_planilla(caso, hoja)
        if not key:
            continue
        prev = by_key.get(key)
        if prev is None:
            by_key[key] = caso
            continue
        o_new = int(caso.get("orden_en_hoja") or 9999)
        o_old = int(prev.get("orden_en_hoja") or 9999)
        if o_new < o_old:
            by_key[key] = caso
    return list(by_key.values())


def sort_visual_cases_for_planilla(casos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Canvas order con bloque UX/decoración al final de la hoja."""

    def bucket(c: dict[str, Any]) -> int:
        rol = _norm(str(c.get("rol_interpretado") or ""))
        if any(ux in rol for ux in _ROLES_UX_AL_FINAL):
            return 2
        if "filtro" in rol and "contractual" not in rol:
            return 0
        return 1

    return sorted(
        casos,
        key=lambda c: (
            bucket(c),
            int(c.get("orden_en_hoja") or 0),
            str(c.get("identificador_visual") or ""),
        ),
    )


def filter_kpi_cases_for_planilla(
    casos: list[dict[str, Any]],
    *,
    expected_on_page: set[str],
    contracted: set[str],
) -> list[dict[str, Any]]:
    """Omite filas de oráculo para KPI que no aplican en la hoja (módulos ejecutivos)."""
    out: list[dict[str, Any]] = []
    for caso in casos:
        tipo = (caso.get("tipo_caso") or "").lower()
        if "alcance" in tipo:
            out.append(caso)
            continue
        if "oráculo" not in tipo and "oraculo" not in tipo:
            out.append(caso)
            continue
        kid = str(caso.get("identificador_indicador") or "")
        if kid in contracted and expected_on_page and kid not in expected_on_page:
            continue
        out.append(caso)
    return out


def orden_capas_por_hoja(
    hoja: str,
    *,
    kpi_casos: list[dict[str, Any]],
    filtro_casos: list[dict[str, Any]],
    visual_casos: list[dict[str, Any]],
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Filtros → alcance/KPI → visuales (canvas + UX al final)."""
    vis = [c for c in visual_casos if caso_incluido_en_planilla(c)]
    vis = dedupe_visual_cases_for_planilla(vis, hoja)
    vis = sort_visual_cases_for_planilla(vis)
    return [
        ("filtros", filtro_casos),
        ("kpi", kpi_casos),
        ("visuales", vis),
    ]
