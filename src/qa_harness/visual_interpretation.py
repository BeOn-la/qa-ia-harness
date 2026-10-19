from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .report_pages import kpi_shown_on_page

_LITERAL_VALUE_RE = re.compile(r'"Value":\s*"\'([^\']+)\'"')
_QUERY_REF_RE = re.compile(r'"queryRef"\s*:\s*"([^"]+)"')
_NATIVE_REF_RE = re.compile(r'"nativeQueryRef"\s*:\s*"([^"]+)"')

ROW_TOLERANCE_PX = 48.0
# Franja más chica para validar shapes de navegación (evita mezclar filas KPI vecinas en Home).
NAV_ROW_TOLERANCE_PX = 32.0

# Marcador bookmark displayName (plantilla eco) → kpi_id
_BOOKMARK_KPI_HINTS: tuple[tuple[str, str], ...] = (
    ("assortment", "assortment"),
    ("listed", "assortment"),
    ("title", "title-compliance"),
    ("stock", "stock-compliance"),
    ("primary image", "primary-image-compliance"),
    ("q secondary", "qimages-compliance"),
    ("qimages", "qimages-compliance"),
    ("secondary image", "secondary-image-compliance"),
    ("promotion", "in-promotion"),
    ("average discount", "average-discount"),
    ("sos numeric", "share-of-search"),
    ("sos weighted", "share-of-search"),
    ("share of search", "share-of-search"),
    ("price", "price-check-compliance"),
    ("navigation numeric", "navigation-visibility"),
)


@dataclass(frozen=True)
class PageVisualEnriched:
    visual_id: str
    visual_type: str
    query_refs: tuple[str, ...]
    native_refs: tuple[str, ...]
    x: float
    y: float
    height: float
    width: float
    bookmark_ids: tuple[str, ...]
    navigation_page_ids: tuple[str, ...]
    action_button_kind: str | None
    has_visual_link: bool
    visual_link_kind: str | None = None
    tab_order: int = 0
    z_index: float = 0.0

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2.0


def sort_visuals_canvas_order(visuals: list[PageVisualEnriched]) -> list[PageVisualEnriched]:
    """Orden de lectura en pantalla: arriba→abajo, izquierda→derecha (como el canvas del informe)."""
    return sorted(
        visuals,
        key=lambda v: (v.y, v.x, v.tab_order, v.z_index, v.visual_id),
    )


def load_page_id_to_name(report_path: Path) -> dict[str, str]:
    pages_dir = report_path / "definition" / "pages"
    out: dict[str, str] = {}
    if not pages_dir.is_dir():
        return out
    for entry in pages_dir.iterdir():
        page_json = entry / "page.json"
        if not entry.is_dir() or not page_json.is_file():
            continue
        data = json.loads(page_json.read_text(encoding="utf-8"))
        out[entry.name] = str(data.get("displayName") or entry.name)
    return out


def load_bookmark_labels(report_path: Path) -> dict[str, str]:
    folder = report_path / "definition" / "bookmarks"
    out: dict[str, str] = {}
    if not folder.is_dir():
        return out
    for path in folder.glob("*.bookmark.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = data.get("name")
        if isinstance(name, str):
            out[name] = str(data.get("displayName") or name).strip()
    return out


def load_bookmark_active_section(report_path: Path) -> dict[str, str]:
    folder = report_path / "definition" / "bookmarks"
    out: dict[str, str] = {}
    if not folder.is_dir():
        return out
    for path in folder.glob("*.bookmark.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        name = data.get("name")
        state = data.get("explorationState") or {}
        section = state.get("activeSection")
        if isinstance(name, str) and isinstance(section, str):
            out[name] = section
    return out


def _extract_literal_values(text: str, key: str) -> list[str]:
    values: list[str] = []
    needle = f'"{key}"'
    idx = 0
    while True:
        i = text.find(needle, idx)
        if i < 0:
            break
        chunk = text[i : i + 500]
        m = _LITERAL_VALUE_RE.search(chunk)
        if m:
            values.append(m.group(1))
        idx = i + len(needle)
    return values


def _detect_action_button_kind(text: str) -> str | None:
    if "'clearAllSlicers'" in text:
        return "limpiar_filtros"
    if "navigationSection" in text:
        return "ir_a_hoja"
    return None


def _norm_page_name(name: str) -> str:
    return (name or "").strip().casefold()


def _detect_visual_link_kind(text: str) -> str | None:
    if "'Back'" in text or '"Back"' in text:
        return "back"
    if "PageNavigation" in text:
        return "page_navigation"
    return None


def list_visuals_enriched(report_path: Path, page_id: str) -> list[PageVisualEnriched]:
    folder = report_path / "definition" / "pages" / page_id / "visuals"
    if not folder.is_dir():
        return []
    out: list[PageVisualEnriched] = []
    for entry in sorted(folder.iterdir()):
        if not entry.is_dir():
            continue
        path = entry / "visual.json"
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
        except (OSError, json.JSONDecodeError):
            continue
        visual = data.get("visual") or {}
        pos = data.get("position") or {}
        vtype = str(visual.get("visualType") or "desconocido")
        refs = tuple(sorted(set(_QUERY_REF_RE.findall(text))))
        natives = tuple(sorted(set(_NATIVE_REF_RE.findall(text))))
        bookmarks = tuple(_extract_literal_values(text, "bookmark"))
        nav_pages = tuple(_extract_literal_values(text, "navigationSection"))
        has_link = "visualLink" in text and '"show"' in text
        out.append(
            PageVisualEnriched(
                visual_id=entry.name,
                visual_type=vtype,
                query_refs=refs,
                native_refs=natives,
                x=float(pos.get("x") or 0),
                y=float(pos.get("y") or 0),
                height=float(pos.get("height") or 0),
                width=float(pos.get("width") or 0),
                bookmark_ids=bookmarks,
                navigation_page_ids=nav_pages,
                action_button_kind=_detect_action_button_kind(text),
                has_visual_link=has_link,
                visual_link_kind=_detect_visual_link_kind(text),
                tab_order=int(pos.get("tabOrder") or 0),
                z_index=float(pos.get("z") or 0),
            )
        )
    return sort_visuals_canvas_order(out)


def cluster_visuals_by_row(visuals: list[PageVisualEnriched]) -> dict[str, list[PageVisualEnriched]]:
    """visual_id → otros visuales en la misma franja horizontal (fila de KPI en Home)."""
    if not visuals:
        return {}
    sorted_v = sorted(visuals, key=lambda v: (v.center_y, v.x))
    bands: list[list[PageVisualEnriched]] = []
    for v in sorted_v:
        if not bands or abs(v.center_y - bands[-1][0].center_y) > ROW_TOLERANCE_PX:
            bands.append([v])
        else:
            bands[-1].append(v)
    by_id: dict[str, list[PageVisualEnriched]] = {}
    for band in bands:
        for v in band:
            by_id[v.visual_id] = band
    return by_id


def effective_dax_measures(visual: PageVisualEnriched) -> list[str]:
    """Medidas para catálogo: nativeQueryRef cuando el queryRef es alias (ej. Kpi Title → Title Compliance)."""
    from_query = [
        r.split(".", 1)[1] for r in visual.query_refs if r.startswith("DAX Measures.")
    ]
    natives = [n for n in visual.native_refs if n]
    if natives and from_query:
        merged: list[str] = []
        for i, q in enumerate(from_query):
            if q.startswith("Kpi ") and i < len(natives):
                merged.append(natives[i])
            else:
                merged.append(q)
        for n in natives:
            if n not in merged:
                merged.append(n)
        return merged
    return natives or from_query


def kpi_id_from_bookmark_label(label: str) -> str | None:
    norm = label.casefold().strip()
    for hint, kid in _BOOKMARK_KPI_HINTS:
        if hint in norm:
            return kid
    return None


def contract_label_for_kpi(kpi_id: str, contract_names: dict[str, str]) -> str:
    return contract_names.get(kpi_id, kpi_id)


def catalog_labels_for_kpi(kpi_id: str, catalog: list[dict[str, Any]]) -> str:
    for entry in catalog:
        if str(entry.get("kpi_id")) == kpi_id:
            return str(entry.get("home_label") or kpi_id)
    return kpi_id


def kpi_ids_for_effective_measures(
    measures: list[str],
    catalog: list[dict[str, Any]],
) -> list[str]:
    found: list[str] = []
    measure_set = set(measures)
    for entry in catalog:
        if kpi_shown_on_page(entry, measure_set):
            found.append(str(entry["kpi_id"]))
    for m in measures:
        if m.startswith("SS_Share_Own"):
            found.append("share-of-search")
        if m.startswith("NV_Share") or m.startswith("SV_Share"):
            found.append("search-visibility" if "SV" in m else "navigation-visibility")
    return sorted(set(found))


def _kpi_cards_in_band(
    band: list[PageVisualEnriched],
    catalog: list[dict[str, Any]],
) -> list[tuple[PageVisualEnriched, str]]:
    candidates: list[tuple[PageVisualEnriched, str]] = []
    for v in band:
        if v.visual_type.casefold() not in ("card",):
            continue
        measures = effective_dax_measures(v)
        if not measures:
            continue
        if any(" vs " in m for m in measures):
            continue
        kids = kpi_ids_for_effective_measures(measures, catalog)
        if kids:
            candidates.append((v, kids[0]))
    candidates.sort(key=lambda t: t[0].x)
    return candidates


def peers_near_visual(
    anchor: PageVisualEnriched,
    visuals: list[PageVisualEnriched],
    tolerance: float = NAV_ROW_TOLERANCE_PX,
) -> list[PageVisualEnriched]:
    cy = anchor.center_y
    return [v for v in visuals if abs(v.center_y - cy) <= tolerance]


def _primary_kpi_card_in_band(
    band: list[PageVisualEnriched],
    catalog: list[dict[str, Any]],
    anchor: PageVisualEnriched | None = None,
) -> tuple[PageVisualEnriched | None, str | None]:
    candidates = _kpi_cards_in_band(band, catalog)
    if not candidates:
        return None, None
    if anchor is None:
        return candidates[0][0], candidates[0][1]
    ax = anchor.x + anchor.width / 2.0
    best = min(candidates, key=lambda t: abs((t[0].x + t[0].width / 2.0) - ax))
    return best[0], best[1]


def format_lectura_qa(
    *,
    page_name: str,
    rol: str,
    kpi_id: str | None,
    contract_names: dict[str, str],
    catalog: list[dict[str, Any]],
    extra: str = "",
) -> str:
    parts = [page_name, rol]
    if kpi_id:
        contrato = contract_label_for_kpi(kpi_id, contract_names)
        plantilla = catalog_labels_for_kpi(kpi_id, catalog)
        parts.append(f"{contrato} ({plantilla})")
    if extra:
        parts.append(extra)
    return " · ".join(parts)


def is_target_or_pp_measure(measure: str) -> bool:
    m = measure.casefold()
    return " vs target" in m or " vs pp" in m or " vs anterior" in m


def is_operational_slicer(refs: tuple[str, ...]) -> bool:
    operational_prefixes = (
        "Date.",
        "Dim_Brand.",
        "EcoDimKpi.",
        "Trade.",
        "DAX Measures.Selector",
    )
    for ref in refs:
        if any(ref.startswith(p) for p in operational_prefixes):
            return True
        if ref.startswith("DAX Measures.") and "Filtro" in ref:
            return True
    return False


def evaluate_visual_contextual(
    *,
    visual: PageVisualEnriched,
    page_display_name: str,
    row_peers: list[PageVisualEnriched],
    page_spec: dict[str, Any] | None,
    contracted: set[str],
    expected_on_page: set[str],
    strict_contract: bool,
    catalog: list[dict[str, Any]],
    filter_verdicts: dict[str, dict[str, Any]],
    oracle_by_kpi: dict[str, dict[str, Any]],
    contract_names: dict[str, str],
    bookmark_labels: dict[str, str],
    bookmark_sections: dict[str, str],
    page_id_to_name: dict[str, str],
    page_visuals: list[PageVisualEnriched] | None = None,
) -> dict[str, Any]:
    from .report_filters import _FIELD_TO_FILTER
    from .report_visuals import filter_id_for_visual

    vtype_cf = visual.visual_type.casefold()
    measures = effective_dax_measures(visual)
    titulo_tecnico = f"{visual.visual_type} ({visual.visual_id[:8]}…)"

    base: dict[str, Any] = {
        "identificador_visual": visual.visual_id,
        "tipo_visual": visual.visual_type,
        "campos_en_consulta": list(visual.query_refs),
        "medidas_dax": measures,
    }

    def finish(
        rol: str,
        veredicto: str,
        detalle: str,
        kpi_id: str | None = None,
        nombre_caso: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        lectura = format_lectura_qa(
            page_name=page_display_name,
            rol=rol,
            kpi_id=kpi_id,
            contract_names=contract_names,
            catalog=catalog,
        )
        base.update(
            {
                "rol_interpretado": rol,
                "lectura_qa": lectura,
                "nombre_caso": nombre_caso or lectura,
                "veredicto": veredicto,
                "detalle": detalle,
                **extra,
            }
        )
        if kpi_id:
            base["identificador_indicador"] = kpi_id
        return base

    if visual.visual_link_kind == "back":
        return finish(
            "navegación atrás",
            "correcto",
            "Botón de retroceso del informe (historial de navegación de Power BI).",
        )

    if vtype_cf == "image" and visual.navigation_page_ids:
        nav_name = page_id_to_name.get(
            visual.navigation_page_ids[0], visual.navigation_page_ids[0]
        )
        if _norm_page_name(nav_name) == "home":
            return finish(
                "navegación a Home",
                "correcto",
                "Ícono o imagen con enlace a la hoja Home.",
                nombre_caso=f"{page_display_name} · ícono Home",
            )
        return finish(
            "enlace a otra hoja",
            "correcto",
            f"Imagen con enlace a la hoja «{nav_name}».",
        )

    # —— Navegación: shape / botón con bookmark o cambio de hoja ——
    if vtype_cf in ("shape", "actionbutton") and (
        visual.bookmark_ids or visual.navigation_page_ids or visual.has_visual_link
    ):
        _, row_kpi = _primary_kpi_card_in_band(row_peers, catalog, anchor=visual)
        bm_label = ""
        bm_kpi: str | None = None
        if visual.bookmark_ids:
            bm_label = bookmark_labels.get(visual.bookmark_ids[0], visual.bookmark_ids[0])
            bm_kpi = kpi_id_from_bookmark_label(bm_label)
        nav_name = None
        if visual.navigation_page_ids:
            nav_name = page_id_to_name.get(
                visual.navigation_page_ids[0], visual.navigation_page_ids[0]
            )
        target_section = None
        if visual.bookmark_ids:
            target_section = bookmark_sections.get(visual.bookmark_ids[0])

        if visual.action_button_kind == "limpiar_filtros":
            return finish(
                "acción limpiar filtros",
                "correcto",
                "Botón estándar de plantilla eco para borrar segmentaciones.",
            )

        if visual.action_button_kind == "ir_a_hoja" and nav_name:
            return finish(
                "acción ir a otra hoja",
                "correcto",
                f"Navega a la hoja '{nav_name}' (comportamiento esperado de plantilla).",
                nombre_caso=f"{page_display_name} · ir a {nav_name}",
            )

        nav_peers = (
            peers_near_visual(visual, page_visuals)
            if page_visuals
            else row_peers
        )
        near_cards = _kpi_cards_in_band(nav_peers, catalog)
        near_kpis = {kid for _, kid in near_cards}
        if bm_kpi and bm_kpi in near_kpis:
            return finish(
                "zona clicable detalle KPI",
                "correcto",
                f"Bookmark '{bm_label}' coincide con la tarjeta KPI en la misma franja del canvas.",
                kpi_id=bm_kpi,
            )

        if bm_kpi and row_kpi:
            ok = bm_kpi == row_kpi
            det = (
                f"Zona clicable alineada al KPI de la fila; bookmark '{bm_label}' abre detalle coherente."
                if ok
                else f"Bookmark '{bm_label}' apunta a {bm_kpi} pero la tarjeta mas cercana en la fila amplia es {row_kpi}."
            )
            return finish(
                "zona clicable detalle KPI",
                "correcto" if ok else "fallido",
                det,
                kpi_id=bm_kpi if ok else row_kpi,
            )

        if bm_kpi and bm_kpi in contracted:
            section_name = page_id_to_name.get(target_section or "", target_section or "")
            det = f"Bookmark '{bm_label}' abre hoja '{section_name or 'KPI Analysis'}'."
            if nav_name and nav_name not in ("KPI Analysis", "Share of Search", "Retail Media - Navigation"):
                return finish(
                    "zona clicable detalle KPI",
                    "fallido",
                    f"Navegacion a '{nav_name}' no coincide con detalle KPI tipico.",
                    kpi_id=bm_kpi,
                )
            return finish(
                "zona clicable detalle KPI",
                "correcto",
                det,
                kpi_id=bm_kpi,
            )

        if bm_label:
            return finish(
                "zona clicable (bookmark)",
                "correcto",
                f"Area de clic con bookmark '{bm_label}'; no se pudo cruzar con fila, revisar layout.",
                kpi_id=bm_kpi,
            )

    # —— Decoración sin enlace ni datos ——
    if vtype_cf in ("image", "textbox", "basicshape") or (
        vtype_cf in ("shape", "actionbutton") and not visual.query_refs and not visual.has_visual_link
    ):
        return finish(
            "elemento de diseño",
            "correcto",
            "Solo maquetación o texto; no lleva KPI ni filtro contractual.",
        )

    # —— Slicers ——
    if vtype_cf == "slicer" or filter_id_for_visual(visual.query_refs):
        fid = filter_id_for_visual(visual.query_refs)
        if not fid:
            label = visual.query_refs[0].split(".")[-1] if visual.query_refs else "filtro"
            return finish(
                f"filtro operativo ({label})",
                "correcto",
                "Filtro de plantilla eco no listado en scope-filters; se acepta si el tablero lo usa.",
            )
        fv = filter_verdicts.get(fid)
        if fv is None:
            return finish(
                f"filtro contractual ({fid})",
                "correcto",
                "Filtro contractual presente; no se re-evaluó SQL en esta pasada.",
                nombre_caso=f"{page_display_name} · filtro {fid}",
            )
        ok = fv.get("status") == "ok"
        return finish(
            f"filtro contractual",
            "correcto" if ok else "fallido",
            fv.get("detail")
            or ("Valores alineados al contrato." if ok else "Valores del filtro fuera del contrato."),
            nombre_caso=f"{page_display_name} · filtro {fv.get('filtro', fid)}",
            identificador_filtro=fid,
        )

    # —— Tarjeta de filtros aplicados / refresh ——
    if measures and all(
        m in ("Filtros aplicados general", "FIltros aplicados navigation", "Último Refresh")
        or "Filtros aplicados" in m
        for m in measures
    ):
        return finish(
            "información de contexto",
            "correcto",
            "Muestra filtros activos o fecha de actualización; no es un KPI.",
        )

    # —— Comparación target / período anterior (fuera de scope contractual) ——
    if measures and all(is_target_or_pp_measure(m) for m in measures):
        _, row_kpi = _primary_kpi_card_in_band(row_peers, catalog, anchor=visual)
        kid = row_kpi or kpi_ids_for_effective_measures(measures, catalog)
        kid_one = kid[0] if isinstance(kid, list) and kid else row_kpi
        return finish(
            "comparación target o período anterior",
            "correcto",
            "Target y variación vs período anterior no están en el scope; la visual cumple su rol de apoyo.",
            kpi_id=kid_one,
            nombre_caso=f"{page_display_name} · variación · {measures[0]}",
        )

    if not measures and not visual.query_refs:
        return finish(
            "elemento sin medida",
            "correcto",
            "Sin campos de datos; asumido decoración o contenedor vacío.",
        )

    if not measures:
        return finish(
            "visual con columnas",
            "correcto",
            "Usa columnas de dimensión en lugar de medidas; válido para tablas o gráficos de corte.",
        )

    kpi_ids = kpi_ids_for_effective_measures(measures, catalog)
    base["indicadores_vinculados"] = kpi_ids

    fuera_contrato = [k for k in kpi_ids if k not in contracted]
    if strict_contract and fuera_contrato:
        return finish(
            "tarjeta KPI",
            "fallido",
            "En Home solo deben verse los 10 KPIs del contrato: "
            + ", ".join(fuera_contrato),
            kpi_id=fuera_contrato[0],
        )

    if kpi_ids and expected_on_page:
        fuera_de_hoja = [k for k in kpi_ids if k in contracted and k not in expected_on_page]
        if fuera_de_hoja and page_spec and page_spec.get("validacion_alcance") == "subconjunto_contrato":
            return finish(
                "tarjeta KPI",
                "fallido",
                "Indicador del contrato no esperado en esta hoja: " + ", ".join(fuera_de_hoja),
                kpi_id=fuera_de_hoja[0],
            )

    primary_kpi = next((k for k in kpi_ids if k in contracted), kpi_ids[0] if kpi_ids else None)
    if primary_kpi and primary_kpi in oracle_by_kpi:
        row = oracle_by_kpi[primary_kpi]
        ok = row.get("compare_status") == "pass"
        return finish(
            "tarjeta o gráfico KPI",
            "correcto" if ok else "fallido",
            (
                "Oráculo mensual (DAX vs definición) coincide."
                if ok
                else "La medida del visual debería coincidir con el oráculo SQL y no coincide."
            ),
            kpi_id=primary_kpi,
        )

    if kpi_ids and all(k in contracted for k in kpi_ids):
        return finish(
            "tarjeta o gráfico KPI",
            "correcto",
            "Indicador del contrato presente; sin oráculo SQL en esta corrida.",
            kpi_id=primary_kpi,
        )

    if kpi_ids and not contracted.intersection(kpi_ids):
        return finish(
            "indicador fuera de contrato",
            "correcto" if not strict_contract else "fallido",
            (
                "Capacidad eco fuera de los 10 KPIs; permitido fuera de Home."
                if not strict_contract
                else "No debe mostrarse en el resumen contractual de Home."
            ),
            kpi_id=kpi_ids[0],
        )

    return finish(
        "visual sin clasificar",
        "fallido",
        f"No se pudo vincular medidas {measures!r} al catálogo; revisar nomenclatura DAX.",
        nombre_caso=titulo_tecnico,
    )
