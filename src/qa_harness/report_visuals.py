from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .report_filters import _FIELD_TO_FILTER
from .report_pages import kpi_shown_on_page

_QUERY_REF_RE = re.compile(r'"queryRef"\s*:\s*"([^"]+)"')

DECORATIVE_VISUAL_TYPES = frozenset(
    {
        "shape",
        "image",
        "actionbutton",
        "pagenavigator",
        "textbox",
        "basicShape",
    }
)

SUPPORTING_MEASURE_MARKERS = (
    " vs ",
    "Filtros aplicados",
    "FIltros aplicados",
    "Último Refresh",
    "Selector",
    "_Selector",
    "Dynamic Perfect",
    "Kpi ",
    " vs PP",
    " vs Target",
    " vs anterior",
)


@dataclass(frozen=True)
class PageVisual:
    visual_id: str
    visual_type: str
    query_refs: tuple[str, ...]


def list_visuals_on_page(report_path: Path, page_id: str) -> list[PageVisual]:
    folder = report_path / "definition" / "pages" / page_id / "visuals"
    if not folder.is_dir():
        return []
    out: list[PageVisual] = []
    for entry in sorted(folder.iterdir()):
        if not entry.is_dir():
            continue
        path = entry / "visual.json"
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        visual = data.get("visual") or {}
        vtype = str(visual.get("visualType") or "desconocido")
        text = path.read_text(encoding="utf-8")
        refs = tuple(sorted(set(_QUERY_REF_RE.findall(text))))
        out.append(PageVisual(visual_id=entry.name, visual_type=vtype, query_refs=refs))
    return out


def measure_names_from_refs(refs: tuple[str, ...]) -> list[str]:
    names: list[str] = []
    for ref in refs:
        if ref.startswith("DAX Measures."):
            names.append(ref.split(".", 1)[1])
    return names


def kpi_ids_for_measures(
    measures: list[str],
    catalog: list[dict[str, Any]],
) -> list[str]:
    found: list[str] = []
    for entry in catalog:
        if kpi_shown_on_page(entry, set(measures)):
            found.append(str(entry["kpi_id"]))
    return sorted(set(found))


def is_supporting_measure(measure: str) -> bool:
    return any(marker in measure for marker in SUPPORTING_MEASURE_MARKERS)


def filter_id_for_visual(refs: tuple[str, ...]) -> str | None:
    for ref in refs:
        fid = _FIELD_TO_FILTER.get(ref)
        if fid:
            return fid
    return None


def evaluate_visual(
    *,
    visual: PageVisual,
    page_spec: dict[str, Any] | None,
    contracted: set[str],
    expected_on_page: set[str],
    strict_contract: bool,
    catalog: list[dict[str, Any]],
    catalog_ids: set[str],
    filter_verdicts: dict[str, dict[str, Any]],
    oracle_by_kpi: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    vtype_cf = visual.visual_type.casefold()
    measures = measure_names_from_refs(visual.query_refs)
    titulo = f"{visual.visual_type} ({visual.visual_id[:8]}…)"

    base: dict[str, Any] = {
        "identificador_visual": visual.visual_id,
        "tipo_visual": visual.visual_type,
        "campos_en_consulta": list(visual.query_refs),
        "medidas_dax": measures,
    }

    if vtype_cf in DECORATIVE_VISUAL_TYPES or not visual.query_refs:
        base.update(
            {
                "nombre_caso": titulo,
                "veredicto": "no aplica",
                "detalle": "Elemento de diseño o navegación sin datos de negocio contratados.",
            }
        )
        return base

    if vtype_cf == "slicer" or filter_id_for_visual(visual.query_refs):
        fid = filter_id_for_visual(visual.query_refs)
        if not fid:
            base.update(
                {
                    "nombre_caso": f"Slicer ({visual.visual_id[:8]}…)",
                    "veredicto": "no aplica",
                    "detalle": "Filtro del tablero no mapeado al contrato de filtros.",
                }
            )
            return base
        fv = filter_verdicts.get(fid)
        if fv is None:
            base.update(
                {
                    "nombre_caso": f"Slicer — {fid}",
                    "veredicto": "no aplica",
                    "detalle": "Este filtro no se evaluó contra SQL en esta corrida.",
                }
            )
            return base
        ok = fv.get("status") == "ok"
        base.update(
            {
                "nombre_caso": f"Slicer — {fv.get('filtro', fid)}",
                "identificador_filtro": fid,
                "veredicto": "correcto" if ok else "fallido",
                "detalle": fv.get("detail")
                or ("Valores del modelo alineados al contrato." if ok else "Filtro fuera de contrato."),
            }
        )
        return base

    if not measures:
        base.update(
            {
                "nombre_caso": titulo,
                "veredicto": "no aplica",
                "detalle": "Visual con datos pero sin medidas DAX (tabla o columna); revisar manual si es crítico.",
            }
        )
        return base

    if all(is_supporting_measure(m) for m in measures):
        base.update(
            {
                "nombre_caso": f"Apoyo — {measures[0]}",
                "veredicto": "no aplica",
                "detalle": "Medida de apoyo (comparación, selector o texto); no es un indicador contractual.",
            }
        )
        return base

    kpi_ids = kpi_ids_for_measures(measures, catalog)
    base["indicadores_vinculados"] = kpi_ids

    fuera_contrato = [k for k in kpi_ids if k not in contracted]
    if strict_contract and fuera_contrato:
        base.update(
            {
                "nombre_caso": f"Indicador — {measures[0]}",
                "veredicto": "fallido",
                "detalle": (
                    "En esta hoja no deben mostrarse indicadores fuera del contrato: "
                    + ", ".join(fuera_contrato)
                ),
            }
        )
        return base

    if kpi_ids and expected_on_page:
        fuera_de_hoja = [k for k in kpi_ids if k in contracted and k not in expected_on_page]
        if fuera_de_hoja and page_spec and page_spec.get("validacion_alcance") == "subconjunto_contrato":
            base.update(
                {
                    "nombre_caso": f"Indicador — {measures[0]}",
                    "veredicto": "fallido",
                    "detalle": (
                        "Indicador del contrato no esperado en esta hoja: "
                        + ", ".join(fuera_de_hoja)
                    ),
                }
            )
            return base

    primary_kpi = next((k for k in kpi_ids if k in contracted), kpi_ids[0] if kpi_ids else None)
    if primary_kpi and primary_kpi in oracle_by_kpi:
        row = oracle_by_kpi[primary_kpi]
        ok = row.get("compare_status") == "pass"
        base.update(
            {
                "nombre_caso": f"Indicador — {measures[0]}",
                "veredicto": "correcto" if ok else "fallido",
                "detalle": (
                    "Oráculo mensual (lógica DAX vs definición) coincide."
                    if ok
                    else "El valor del visual debería alinearse al oráculo SQL y no coincide."
                ),
                "identificador_indicador": primary_kpi,
            }
        )
        return base

    if kpi_ids and all(k in contracted for k in kpi_ids):
        base.update(
            {
                "nombre_caso": f"Indicador — {measures[0]}",
                "veredicto": "correcto",
                "detalle": "Indicador del contrato; sin oráculo SQL en esta corrida (solo alcance).",
            }
        )
        return base

    if kpi_ids and not contracted.intersection(kpi_ids):
        base.update(
            {
                "nombre_caso": f"Indicador — {measures[0]}",
                "veredicto": "correcto" if not strict_contract else "fallido",
                "detalle": (
                    "Indicador del tablero eco fuera de los 10 del contrato; permitido fuera de Home."
                    if not strict_contract
                    else "Indicador fuera del contrato en hoja de resumen estricto."
                ),
            }
        )
        return base

    base.update(
        {
            "nombre_caso": titulo,
            "veredicto": "no aplica",
            "detalle": "No se pudo vincular a indicador del catálogo.",
        }
    )
    return base
