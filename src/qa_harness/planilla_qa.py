from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from datetime import date
from importlib.resources import files as pkg_files
from pathlib import Path
from typing import Any, Iterable

from .common import ContractError


def _load_revision_capsules(board_qa_root: Path | None = None) -> dict[str, Any]:
    bundled = pkg_files("qa_harness.schemas").joinpath("planilla_revision_capsules.json")
    path = Path(bundled)
    if not path.is_file():
        path = Path(__file__).resolve().parents[2] / "schemas" / "planilla_revision_capsules.json"
    if not path.is_file():
        raise ContractError("Falta schemas/planilla_revision_capsules.json en el paquete.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if board_qa_root:
        local = Path(board_qa_root) / "planilla-revision-capsules.json"
        if local.is_file():
            override = json.loads(local.read_text(encoding="utf-8-sig"))
            for key in (
                "prioridad",
                "controlado_por",
                "tipo_prueba",
                "prioridad_error_default",
                "controlado_por_error_default",
                "tipo_error_por_capa",
                "tipo_prueba_por_capa",
                "politica",
            ):
                if key in override:
                    if isinstance(data.get(key), dict) and isinstance(override[key], dict):
                        data[key] = {**data[key], **override[key]}
                    else:
                        data[key] = override[key]
    return data


REVISION_FIELD_NAMES = (
    "estado",
    "tipo_error",
    "prioridad",
    "controlado_por",
    "resuelto_por",
    "fecha_auditoria",
    "fecha_revision",
    "captura_1",
    "captura_2",
    "observaciones_qa",
    "observaciones_desarrollo",
)

FIXED_HEADERS = (
    "ID",
    "Caso de Prueba",
    "Pasos a Seguir",
    "Resultado Esperado",
    "Tablero",
    "Tipo de Prueba",
)

# Columna G = revisión 1 (1-based índice 7) en plantilla clásica A–F.
REVISION_1_START_COL = 7
# Corrida repo: columna E = Resultado Obtenido → revisión 1 empieza en H (8).
CORRIDA_REPO_REVISION_1_START_COL = 8
REVISION_WIDTH = len(REVISION_FIELD_NAMES)


def load_planilla_qa_config(board_qa_root: Path) -> dict[str, Any]:
    """Lee bloque planilla_qa de board.yml (sin dependencia PyYAML)."""
    path = board_qa_root / "board.yml"
    if not path.is_file():
        return {}
    out: dict[str, Any] = {}
    in_block = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "planilla_qa:":
            in_block = True
            continue
        if not in_block:
            continue
        if line and not line[0].isspace():
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    if out.get("template_sheet_id") is not None:
        try:
            out["template_sheet_id"] = int(str(out["template_sheet_id"]))
        except ValueError:
            pass
    return out

KPI_TITLE_TO_ID: dict[str, str] = {
    "assortment": "assortment",
    "in stock": "stock-compliance",
    "in promotion": "in-promotion",
    "average discount": "average-discount",
    "price check": "price-check-compliance",
    "price index": "price-index-compliance",
    "title": "title-compliance",
    "description": "description-compliance",
    "primary image": "primary-image-compliance",
    "secondary image": "secondary-image-compliance",
    "q images": "qimages-compliance",
    "navigation visibility numeric": "navigation-visibility",
    "search visibility numeric": "search-visibility",
    "share of search": "share-of-search",
}

FILTER_PHRASE_TO_ID: list[tuple[str, str]] = [
    ("etailer / store", "etailer_tienda"),
    ("e tailer / store", "etailer_tienda"),
    ("category group / category", "categoria"),
    ("keyword", "keyword_sos"),
]


def _norm_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text.strip().lower())
    return text


def _norm_tablero(value: str) -> str:
    return _norm_text(value)


def load_tablero_aliases(path: Path | None) -> dict[str, str]:
    if not path or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    raw = data.get("aliases") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return {}
    return {_norm_tablero(str(k)): _norm_tablero(str(v)) for k, v in raw.items()}


def _tablero_lookup_key(value: str, aliases: dict[str, str] | None) -> str:
    key = _norm_tablero(value)
    if aliases and key in aliases:
        return aliases[key]
    return key


def _col_letter(index_1based: int) -> str:
    n = index_1based
    letters = ""
    while n:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def revision_start_col(revision_index: int) -> int:
    if revision_index < 1:
        raise ContractError("revision_index debe ser >= 1.")
    return REVISION_1_START_COL + (revision_index - 1) * REVISION_WIDTH


def load_planilla_catalog(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if "cases" not in data or not isinstance(data["cases"], list):
        raise ContractError("Catálogo de planilla inválido: falta lista cases.")
    return data


def parse_catalog_csv(text: str, *, source: dict[str, Any] | None = None) -> dict[str, Any]:
    reader = csv.reader(io.StringIO(text))
    cases: list[dict[str, Any]] = []
    row_index = 3
    for row in reader:
        if not row or not any(cell.strip() for cell in row):
            continue
        while len(row) < 6:
            row.append("")
        caso = row[1].strip()
        if not caso:
            continue
        tablero = row[4].strip()
        tipo = row[5].strip()
        entry: dict[str, Any] = {
            "sheet_row": row_index,
            "id": row[0].strip(),
            "caso_de_prueba": caso,
            "pasos_a_seguir": row[2].strip(),
            "resultado_esperado": row[3].strip(),
            "tablero": tablero,
            "tipo_prueba": tipo,
            "automation": infer_automation_binding(caso, tipo, tablero),
        }
        cases.append(entry)
        row_index += 1
    return {
        "schema_version": 1,
        "source": source or {},
        "cases": cases,
    }


def infer_automation_binding(caso: str, tipo: str, tablero: str) -> dict[str, Any] | None:
    norm_caso = _norm_text(caso)
    norm_tipo = _norm_text(tipo)
    tab_norm = _norm_tablero(tablero)

    if "validar filtro" in norm_caso or norm_tipo == "filtros":
        for phrase, filter_id in FILTER_PHRASE_TO_ID:
            if phrase in norm_caso:
                return {
                    "capa": "filtros",
                    "filter_id": filter_id,
                    "tablero": tab_norm,
                }
        return None

    if "validar kpi" in norm_caso or norm_tipo.startswith("kpi"):
        for label, kpi_id in KPI_TITLE_TO_ID.items():
            if label in norm_caso:
                return {
                    "capa": "indicadores",
                    "kpi_id": kpi_id,
                    "tablero": tab_norm,
                }
        return None

    if "alcance" in norm_caso or "indicadores visibles vs contrato" in norm_caso:
        return {"capa": "alcance", "tablero": tab_norm}

    if "estetica general" in norm_caso or "colorcoding" in norm_caso:
        return {"capa": "visuales_resumen", "tablero": tab_norm}

    return None


def resolve_case_binding(
    case: dict[str, Any],
    index: dict[tuple[str, str, str], dict[str, Any]],
    *,
    tablero_aliases: dict[str, str] | None = None,
    planilla_bindings: dict[str, Any] | None = None,
    visuales: dict[str, Any] | None = None,
    page_visual_state: Any | None = None,
) -> dict[str, Any] | None:
    from .planilla_bindings import resolve_planilla_binding

    binding, _meta = resolve_planilla_binding(
        case,
        planilla_bindings,
        tablero_aliases=tablero_aliases,
        visuales=visuales,
        page_visual_state=page_visual_state,
    )
    return binding


def default_planilla_bindings_path(board_qa_root: Path) -> Path:
    return board_qa_root / "planilla-harness-bindings.json"


def _display_tablero_for_page_key(
    page_key: str,
    cases: list[dict[str, Any]],
    tablero_aliases: dict[str, str] | None,
) -> str:
    pk = _norm_tablero(page_key)
    for c in cases:
        if _tablero_lookup_key(c.get("tablero") or "", tablero_aliases) == pk:
            return (c.get("tablero") or "").strip()
    if tablero_aliases:
        for planilla_norm, report_norm in tablero_aliases.items():
            if report_norm == pk:
                return planilla_norm.title()
    return page_key


def _shift_sheet_rows_from(cases: list[dict[str, Any]], from_row_exclusive: int, delta: int) -> None:
    for c in cases:
        row = int(c.get("sheet_row") or 0)
        if row > from_row_exclusive:
            c["sheet_row"] = row + delta


def _insert_cases_after_tablero(
    cases: list[dict[str, Any]],
    tablero_display: str,
    new_entries: list[dict[str, Any]],
    *,
    tablero_aliases: dict[str, str] | None,
) -> list[dict[str, Any]]:
    tab_key = _tablero_lookup_key(tablero_display, tablero_aliases)
    last_i = -1
    last_row = 2
    for i, c in enumerate(cases):
        if _tablero_lookup_key(c.get("tablero") or "", tablero_aliases) == tab_key:
            last_i = i
            last_row = max(last_row, int(c.get("sheet_row") or 0))
    if last_i < 0 or not new_entries:
        return cases
    _shift_sheet_rows_from(cases, last_row, len(new_entries))
    for j, entry in enumerate(new_entries):
        entry["sheet_row"] = last_row + 1 + j
        entry.setdefault("tablero", tablero_display)
    return cases[: last_i + 1] + new_entries + cases[last_i + 1 :]


def _titulo_caso_visual_planilla(lectura: str, tablero: str) -> str:
    lectura = (lectura or "").strip()
    if "filtro contractual" in _norm_text(lectura):
        return "Validar slicer contractual (QA automático)"
    if "visual sin clasificar" in _norm_text(lectura):
        return "Validar elemento visual (QA automático)"
    parte = lectura.split("·", 1)[-1].strip() if "·" in lectura else lectura
    return f"Validar {parte} (QA automático)"


def augment_catalog_with_harness(
    catalog: dict[str, Any],
    kpi: dict[str, Any] | None,
    filtros: dict[str, Any] | None,
    visuales: dict[str, Any] | None,
    *,
    tablero_aliases: dict[str, str] | None = None,
    solo_hoja: str = "Home",
) -> dict[str, Any]:
    """Agrega filas nuevas sin quitar las de la planilla. Por defecto solo extras de Home, al final del bloque Home."""
    base_cases = [
        c for c in (catalog.get("cases") or []) if not c.get("catalog_nuevo")
    ]
    cases: list[dict[str, Any]] = sorted(
        base_cases, key=lambda c: int(c.get("sheet_row") or 0)
    )
    keys = {_case_result_key(c) for c in cases}
    index = build_automation_index(kpi, filtros, visuales)
    tab_display = solo_hoja
    tab_key = _tablero_lookup_key(solo_hoja, tablero_aliases)
    nuevos: list[dict[str, Any]] = []

    for key, auto in index.items():
        pk, capa, internal = key
        if pk != tab_key or capa != "visuales" or auto.get("veredicto") != "fallido":
            continue
        lectura = auto.get("lectura_qa") or internal
        titulo = _titulo_caso_visual_planilla(lectura, tab_display)
        draft = {"tablero": tab_display, "caso_de_prueba": titulo}
        if _case_result_key(draft) in keys:
            continue
        detalle = (auto.get("detalle") or "").strip()
        nuevos.append(
            {
                "id": "",
                "caso_de_prueba": titulo,
                "pasos_a_seguir": (
                    f"Abrir la hoja «{tab_display}» del informe y revisar el elemento señalado "
                    f"en la fila del caso (posición {auto.get('orden_en_hoja') or '—'} en el layout de la hoja)."
                ),
                "resultado_esperado": (
                    "El visual cumple el comportamiento esperado para esa hoja según el contrato del tablero."
                ),
                "tablero": tab_display,
                "tipo_prueba": "Visuales",
                "catalog_nuevo": True,
                "automation": {
                    "capa": "visuales",
                    "tablero": tab_key,
                    "visual_key": internal,
                    "lectura_qa": lectura,
                    "detalle": detalle,
                },
            }
        )
        keys.add(_case_result_key(draft))

    if nuevos:
        cases = _insert_cases_after_tablero(
            cases, tab_display, nuevos, tablero_aliases=tablero_aliases
        )

    out = dict(catalog)
    out["cases"] = cases
    out["catalog_augmented"] = {
        "filas_planilla_original": len(base_cases),
        "filas_total": len(cases),
        "filas_agregadas": len(nuevos),
        "bloque_insertado_despues_de": tab_display,
    }
    return out


def veredicto_to_estado(veredicto: str | None) -> str:
    caps = _load_revision_capsules()["estado"]
    if veredicto == "correcto":
        return caps["aprobado"]
    if veredicto == "fallido":
        return caps["error"]
    return caps["sin_revisar"]


def _estados_error_para_filtro_previo() -> tuple[str, ...]:
    pol = _load_revision_capsules().get("politica") or {}
    prev = pol.get("estados_error_previos") or ["Error", "Rechazado", "Fallido"]
    return tuple(str(x) for x in prev)


def _capsule_choice(
    field: str,
    value: str,
    *,
    fallback: str,
    caps: dict[str, Any] | None = None,
) -> str:
    caps = caps or _load_revision_capsules()
    allowed = caps.get(field) or []
    if isinstance(allowed, list) and value in allowed:
        return value
    if isinstance(allowed, list) and fallback in allowed:
        return fallback
    return value or fallback


def _tipo_prueba_para_capa(capa: str) -> str | None:
    caps = _load_revision_capsules()
    raw = (caps.get("tipo_prueba_por_capa") or {}).get(capa)
    if not raw:
        return None
    return _capsule_choice("tipo_prueba", str(raw), fallback=str(raw))


def _normalizar_tipo_prueba_catalogo(valor: str | None, *, capa: str | None = None) -> str:
    caps = _load_revision_capsules()
    allowed = set(caps.get("tipo_prueba") or [])
    actual = (valor or "").strip()
    if actual in allowed:
        return actual
    if capa:
        inferido = _tipo_prueba_para_capa(capa)
        if inferido:
            return inferido
    return ""


def _sanitizar_texto_planilla(texto: str) -> str:
    """Quita rutas, nombres de repo harness y referencias a artefactos internos de QA."""
    if not texto:
        return ""
    t = texto.strip().replace("\n", " ")
    patrones = (
        r"test-evidence[^\s]*",
        r"qa-ia-harness[^\s]*",
        r"scope-kpis\.json",
        r"scope-filters\.json",
        r"planilla-harness-bindings[^\s]*",
        r"identificador interno de QA:\s*[\w-]+",
        r"\(identificador interno[^)]+\)",
        r"según reglas del harness",
        r"interpretación QA del tablero",
        r"corrida automática de visuales",
    )
    for pat in patrones:
        t = re.sub(pat, "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bfaltan en sql\b:", "Faltan opciones respecto al universo acordado:", t, flags=re.IGNORECASE)
    t = re.sub(r"\bsobran en sql\b:", "Hay opciones de más respecto al universo acordado:", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,;.")
    return t


def _error_metadata_for_capa(
    capa: str,
    *,
    caps: dict[str, Any] | None = None,
) -> tuple[str, str, str]:
    caps = caps or _load_revision_capsules()
    tipo = (caps.get("tipo_error_por_capa") or {}).get(capa) or "Datos"
    prioridad = _capsule_choice(
        "prioridad",
        str(caps.get("prioridad_error_default") or "Alta"),
        fallback="Alta",
        caps=caps,
    )
    controlado = _capsule_choice(
        "controlado_por",
        str(caps.get("controlado_por_error_default") or "Motrel Gabriel"),
        fallback="Motrel Gabriel",
        caps=caps,
    )
    return tipo, prioridad, controlado


def _page_key_from_hoja_result(hoja: dict[str, Any]) -> str:
    name = hoja.get("nombre_hoja") or hoja.get("display_name") or ""
    return _norm_tablero(str(name))


def build_automation_index(
    kpi: dict[str, Any] | None,
    filtros: dict[str, Any] | None,
    visuales: dict[str, Any] | None,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Clave: (tablero_norm, capa, id_interno)."""
    index: dict[tuple[str, str, str], dict[str, Any]] = {}

    if kpi:
        for hoja in kpi.get("hojas") or []:
            pk = _page_key_from_hoja_result(hoja)
            for caso in hoja.get("casos_de_prueba") or []:
                if caso.get("tipo_caso") == "alcance contractual en la hoja":
                    v = caso.get("veredicto_alcance")
                    index[(pk, "alcance", "_")] = {
                        "veredicto": v,
                        "detalle": caso.get("detalle") or "",
                        "capa": "alcance",
                    }
                    continue
                kid = caso.get("identificador_indicador")
                if not kid:
                    continue
                if not caso.get("se_muestra_en_esta_hoja"):
                    index[(pk, "indicadores", str(kid))] = {
                        "veredicto": "no aplica",
                        "detalle": caso.get("detalle") or "",
                        "capa": "indicadores",
                        "kpi_id": str(kid),
                        "tipo_caso": caso.get("tipo_caso") or "",
                    }
                else:
                    v = caso.get("veredicto_comparacion_sql")
                    index[(pk, "indicadores", str(kid))] = {
                        "veredicto": v,
                        "detalle": caso.get("detalle") or "",
                        "capa": "indicadores",
                        "kpi_id": str(kid),
                        "tipo_caso": caso.get("tipo_caso") or "",
                    }

    if filtros:
        for hoja in filtros.get("hojas") or []:
            pk = _page_key_from_hoja_result(hoja)
            for caso in hoja.get("casos_de_prueba") or []:
                fid = caso.get("identificador_filtro")
                if not fid:
                    continue
                if not caso.get("se_muestra_en_esta_hoja"):
                    index[(pk, "filtros", str(fid))] = {
                        "veredicto": "no aplica",
                        "detalle": caso.get("detalle") or "",
                        "capa": "filtros",
                        "nombre_filtro": caso.get("nombre_filtro") or "",
                        "campos_en_visuales": caso.get("campos_en_visuales") or [],
                    }
                else:
                    v = caso.get("veredicto_contrato")
                    index[(pk, "filtros", str(fid))] = {
                        "veredicto": v,
                        "detalle": caso.get("detalle") or "",
                        "capa": "filtros",
                        "nombre_filtro": caso.get("nombre_filtro") or "",
                        "campos_en_visuales": caso.get("campos_en_visuales") or [],
                    }

    if visuales:
        from .planilla_visual_match import visual_index_key

        for hoja in visuales.get("hojas") or []:
            pk = _page_key_from_hoja_result(hoja)
            visuales_hoja: list[dict[str, Any]] = []
            for caso in hoja.get("casos_de_prueba") or []:
                v = caso.get("veredicto")
                lectura = caso.get("lectura_qa") or caso.get("nombre_caso") or ""
                key = visual_index_key(caso)
                index[(pk, "visuales", key)] = {
                    "veredicto": v,
                    "detalle": caso.get("detalle") or "",
                    "capa": "visuales",
                    "lectura_qa": lectura,
                    "orden_en_hoja": caso.get("orden_en_hoja"),
                    "rol_interpretado": caso.get("rol_interpretado") or "",
                }
                if caso.get("tipo_caso") == "visual del informe":
                    visuales_hoja.append(caso)
            if visuales_hoja:
                _index_visuales_resumen_hoja(index, pk, visuales_hoja)

    return index


_CONTEXT_ROLES = frozenset({"información de contexto", "contexto"})


def _index_visuales_resumen_hoja(
    index: dict[tuple[str, str, str], dict[str, Any]],
    pk: str,
    visuales_hoja: list[dict[str, Any]],
) -> None:
    fallidos = [
        c
        for c in visuales_hoja
        if c.get("veredicto") == "fallido"
        and (c.get("rol_interpretado") or "") not in _CONTEXT_ROLES
    ]
    if fallidos:
        partes = [
            f"Visual #{c.get('orden_en_hoja')}: {(c.get('detalle') or c.get('lectura_qa') or '')[:160]}"
            for c in fallidos[:8]
        ]
        index[(pk, "visuales_resumen", "_")] = {
            "veredicto": "fallido",
            "detalle": " | ".join(partes),
            "capa": "visuales_resumen",
            "fallidos": len(fallidos),
            "total_visuales": len(visuales_hoja),
        }
    else:
        index[(pk, "visuales_resumen", "_")] = {
            "veredicto": "correcto",
            "detalle": (
                f"Revisión automática de {len(visuales_hoja)} visuales en la hoja "
                "sin fallos bloqueantes (excl. elementos de contexto)."
            ),
            "capa": "visuales_resumen",
            "fallidos": 0,
            "total_visuales": len(visuales_hoja),
        }


def _lookup_automation(
    binding: dict[str, Any] | None,
    index: dict[tuple[str, str, str], dict[str, Any]],
    *,
    tablero_aliases: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    if not binding:
        return None
    capa = binding["capa"]
    tab = _tablero_lookup_key(binding.get("tablero") or "", tablero_aliases)
    if capa == "alcance":
        return index.get((tab, "alcance", "_"))
    if capa == "indicadores":
        return index.get((tab, "indicadores", binding["kpi_id"]))
    if capa == "filtros":
        return index.get((tab, "filtros", binding["filter_id"]))
    if capa == "visuales_resumen":
        return index.get((tab, "visuales_resumen", "_"))
    if capa == "visuales":
        vkey = binding.get("visual_key") or ""
        return index.get((tab, "visuales", vkey))
    return None


def _case_result_key(case: dict[str, Any]) -> str:
    return "|".join(
        [
            _norm_tablero(case.get("tablero") or ""),
            _norm_text(case.get("caso_de_prueba") or ""),
        ]
    )


def _empty_revision_block() -> dict[str, str]:
    return {name: "" for name in REVISION_FIELD_NAMES}


def _infer_pasos_y_resultado(
    case: dict[str, Any],
    binding: dict[str, Any] | None,
    automation: dict[str, Any] | None,
) -> dict[str, str]:
    """Texto sugerido para C/D cuando el catálogo viene vacío (no pisa celdas con contenido)."""
    tablero = (case.get("tablero") or "").strip()
    caso = (case.get("caso_de_prueba") or "").strip()
    out: dict[str, str] = {}
    if not binding:
        return out
    capa = binding.get("capa")
    if capa == "filtros":
        nombre = (automation or {}).get("nombre_filtro") or caso.replace("Validar filtro de ", "")
        if not (case.get("pasos_a_seguir") or "").strip():
            out["pasos_a_seguir"] = (
                f"Abrir el informe en Power BI y ubicar la hoja «{tablero}». "
                f"Abrir el slicer «{nombre}» y revisar la lista completa de opciones visibles."
            )
        if not (case.get("resultado_esperado") or "").strip():
            out["resultado_esperado"] = (
                "Las opciones del slicer coinciden con el universo definido en el scope contractual "
                "del cliente y con el mismo universo obtenido por la consulta SQL de QA (sin valores "
                "de más ni faltantes)."
            )
    elif capa == "indicadores":
        if not (case.get("pasos_a_seguir") or "").strip():
            out["pasos_a_seguir"] = (
                f"En la hoja «{tablero}», localizar el indicador de «{caso}» "
                f"y el periodo mensual configurado en el tablero."
            )
        if not (case.get("resultado_esperado") or "").strip():
            out["resultado_esperado"] = (
                "El valor mostrado en Power BI coincide con el cálculo de referencia del periodo "
                "(mismas reglas de negocio y mismo universo filtrado)."
            )
    elif capa == "visuales_resumen":
        if not (case.get("pasos_a_seguir") or "").strip():
            out["pasos_a_seguir"] = (
                f"Abrir la hoja «{tablero}» del informe y recorrer visualmente el layout: "
                f"«{caso}»."
            )
        if not (case.get("resultado_esperado") or "").strip():
            out["resultado_esperado"] = (
                "La hoja no presenta fallos en layout, navegación, gráficos ni tablas revisados."
            )
    elif capa == "alcance":
        if not (case.get("pasos_a_seguir") or "").strip():
            out["pasos_a_seguir"] = (
                f"En «{tablero}», listar los indicadores visibles y compararlos con el alcance contractual."
            )
        if not (case.get("resultado_esperado") or "").strip():
            out["resultado_esperado"] = (
                "Los indicadores visibles coinciden con el alcance acordado para ese tipo de hoja."
            )
    if not (case.get("tipo_prueba") or "").strip() and binding:
        inferido = _tipo_prueba_para_capa(str(binding.get("capa") or ""))
        if inferido:
            out.setdefault("tipo_prueba_inferido", inferido)
    return out


def _catalog_field_patches(
    case: dict[str, Any],
    inferred: dict[str, str],
) -> list[dict[str, Any]]:
    row = case.get("sheet_row")
    if not row or not inferred:
        return []
    patches: list[dict[str, Any]] = []
    if inferred.get("pasos_a_seguir") and not (case.get("pasos_a_seguir") or "").strip():
        patches.append({"col": "C", "field": "pasos_a_seguir", "value": inferred["pasos_a_seguir"]})
    if inferred.get("resultado_esperado") and not (case.get("resultado_esperado") or "").strip():
        patches.append({"col": "D", "field": "resultado_esperado", "value": inferred["resultado_esperado"]})
    tipo_inf = inferred.get("tipo_prueba_inferido")
    if tipo_inf and not (case.get("tipo_prueba") or "").strip():
        patches.append({"col": "F", "field": "tipo_prueba", "value": tipo_inf})
    for p in patches:
        p["sheet_row"] = int(row)
    return patches


def _detalle_parece_contrato_filtro(detalle: str, caso: str) -> bool:
    """True si el detalle es el volcado SQL/scope de un filtro, no del caso visual."""
    norm_d = _norm_text(detalle)
    norm_c = _norm_text(caso)
    if not norm_d:
        return False
    if "mock_categorygroup" in norm_d or "faltan opciones respecto" in norm_d:
        if "category" in norm_d and "category" not in norm_c and "categoria" not in norm_c:
            return True
        if "etailer" in norm_d and "etailer" not in norm_c and "store" not in norm_c:
            return True
        if "keyword" in norm_d and "keyword" not in norm_c:
            return True
    if "elemento(s) del layout con fallo" in norm_d:
        return True
    return False


def _resumir_detalle_filtro(detalle: str) -> str:
    detalle = _sanitizar_texto_planilla(detalle)
    partes: list[str] = []
    if "mock_categorygroup" in detalle.lower():
        partes.append("El slicer no usa el campo de categoría definido en el contrato.")
    m_faltan = re.search(
        r"Faltan opciones respecto al universo acordado:\s*([^;]+)",
        detalle,
        flags=re.IGNORECASE,
    )
    if m_faltan:
        n = len([x for x in m_faltan.group(1).split(",") if x.strip()])
        partes.append(f"Faltan {n} opción(es) en el slicer respecto al universo acordado.")
    if re.search(r"Hay opciones de más", detalle, flags=re.IGNORECASE):
        partes.append("Hay opciones de más en el slicer respecto al universo acordado.")
    if partes:
        return " ".join(partes)
    return _truncar_obs(detalle, 160)


def _detalle_visual_caso(automation: dict[str, Any], caso: str) -> str:
    det = _sanitizar_texto_planilla((automation.get("detalle") or "").strip())
    if det and not _detalle_parece_contrato_filtro(det, caso):
        return _truncar_obs(det, 160)
    lectura = (automation.get("lectura_qa") or "").strip()
    if "·" in lectura:
        lectura = lectura.split("·", 1)[-1].strip()
    if lectura:
        return _truncar_obs(lectura, 120)
    return ""


def _fallos_resumen_para_caso(caso: str, automation: dict[str, Any]) -> str:
    det = _sanitizar_texto_planilla((automation.get("detalle") or "").strip())
    norm_caso = _norm_text(caso)
    if "Visual #" in det and "|" in det:
        partes = [p.strip() for p in det.split("|") if p.strip()]
        tokens = [t for t in re.findall(r"[a-z0-9]{5,}", norm_caso)]
        elegidas = [p for p in partes if any(t in _norm_text(p) for t in tokens)]
        if "estetica" in norm_caso:
            elegidas = elegidas or [p for p in partes if "estetica" in _norm_text(p)]
        if "colorcoding" in norm_caso or "color" in norm_caso:
            elegidas = elegidas or [p for p in partes if "color" in _norm_text(p)]
        if elegidas:
            return _truncar_obs("; ".join(elegidas[:2]), 220)
    n = automation.get("fallidos") or 0
    if n:
        return f"«{caso}»: revisar layout de la hoja ({n} hallazgo(s) automáticos en visuales)."
    return f"«{caso}»: revisar layout o comportamiento esperado en la hoja."


def _truncar_obs(texto: str, max_len: int = 220) -> str:
    t = (texto or "").strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 3].rstrip() + "..."


def _observaciones_para_desarrollo(
    case: dict[str, Any],
    automation: dict[str, Any],
    inferred: dict[str, str],
) -> str:
    capa = automation.get("capa") or ""
    tablero = (case.get("tablero") or "").strip()
    caso = (case.get("caso_de_prueba") or "").strip()

    if capa == "filtros":
        nombre = automation.get("nombre_filtro") or caso.replace("Validar filtro de ", "")
        resumen = _resumir_detalle_filtro(automation.get("detalle") or "")
        return _truncar_obs(f"«{caso}» (filtro «{nombre}», hoja «{tablero}»): {resumen}")

    if capa == "indicadores":
        det = _sanitizar_texto_planilla((automation.get("detalle") or "").strip())
        if det and len(det) < 180 and "faltan opciones" not in det.lower():
            extra = det
        else:
            extra = "El valor difiere del cálculo de referencia del periodo."
        return _truncar_obs(f"«{caso}» (hoja «{tablero}»): {extra}")

    if capa == "visuales":
        extra = _detalle_visual_caso(automation, caso)
        if extra:
            return _truncar_obs(f"«{caso}» (hoja «{tablero}»): {extra}")
        return _truncar_obs(f"«{caso}» (hoja «{tablero}»): el elemento no cumple lo esperado.")

    if capa == "visuales_resumen":
        return _truncar_obs(_fallos_resumen_para_caso(caso, automation))

    if capa == "alcance":
        det = _sanitizar_texto_planilla((automation.get("detalle") or "").strip())
        extra = _truncar_obs(det, 120) if det else "Indicadores visibles fuera del alcance acordado."
        return _truncar_obs(f"«{caso}» (hoja «{tablero}»): {extra}")

    return _truncar_obs(f"«{caso}» (hoja «{tablero}»): revisar el comportamiento esperado.")


def _revision_from_run(
    automation: dict[str, Any] | None,
    *,
    case: dict[str, Any],
    binding: dict[str, Any] | None,
    inferred: dict[str, str],
    fecha: str,
    caps: dict[str, Any] | None = None,
) -> dict[str, str]:
    block = _empty_revision_block()
    if not automation:
        return block
    veredicto = automation.get("veredicto")
    capa = automation.get("capa") or ""
    block["fecha_auditoria"] = fecha

    if veredicto == "correcto":
        block["estado"] = veredicto_to_estado(veredicto)
        return block

    if veredicto == "fallido":
        block["estado"] = veredicto_to_estado(veredicto)
        tipo, prioridad, controlado = _error_metadata_for_capa(capa, caps=caps)
        block["tipo_error"] = tipo
        block["prioridad"] = prioridad
        block["controlado_por"] = controlado
        block["observaciones_qa"] = _observaciones_para_desarrollo(case, automation, inferred)
        return block

    if veredicto == "no aplica":
        block["estado"] = veredicto_to_estado(None)
        return block

    block["estado"] = veredicto_to_estado(veredicto)
    return block


def header_rows(revision_count: int = 2) -> list[list[str]]:
    row1 = ["", "", "", "", "", ""]
    row2 = list(FIXED_HEADERS)
    for rev in range(1, revision_count + 1):
        row1.append(f"Revision {rev}")
        row1.extend([""] * (REVISION_WIDTH - 1))
        row2.extend(
            [
                "Estado",
                "Tipo de error",
                "Prioridad ",
                "Controlado por",
                "Resuelto por",
                "Fecha de Auditoría",
                "Fecha de Revisión",
                "Captura 1",
                "Captura 2",
                "Observaciones QA",
                "Observaciones Desarrollo",
            ]
        )
    return [row1, row2]


def _row_to_sheet_values(
    case: dict[str, Any],
    revision_blocks: list[dict[str, str]],
) -> list[str]:
    fixed = [
        case.get("id") or "",
        case.get("caso_de_prueba") or "",
        case.get("pasos_a_seguir") or "",
        case.get("resultado_esperado") or "",
        case.get("tablero") or "",
        case.get("tipo_prueba") or "",
    ]
    for block in revision_blocks:
        fixed.extend(block.get(name, "") for name in REVISION_FIELD_NAMES)
    return fixed


def export_planilla(
    *,
    catalog: dict[str, Any],
    kpi: dict[str, Any] | None = None,
    filtros: dict[str, Any] | None = None,
    visuales: dict[str, Any] | None = None,
    tablero_aliases: dict[str, str] | None = None,
    planilla_bindings: dict[str, Any] | None = None,
    board_qa_root: Path | None = None,
    modo: str,
    revision_index: int = 1,
    nombre_hoja_nueva: str | None = None,
    hoja_planilla: str | None = None,
    entrada_previa: dict[str, Any] | None = None,
    solo_fallidos_anterior: bool = False,
    run_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if modo not in ("recorrida", "regresion"):
        raise ContractError("modo debe ser recorrida o regresion.")

    caps_root = board_qa_root
    if caps_root is None and catalog.get("_board_qa_root"):
        caps_root = Path(str(catalog["_board_qa_root"]))

    def _caps() -> dict[str, Any]:
        return _load_revision_capsules(caps_root)

    if modo == "recorrida":
        catalog_work = dict(catalog)
        catalog_work["cases"] = sorted(
            [c for c in (catalog.get("cases") or []) if not c.get("catalog_nuevo")],
            key=lambda c: int(c.get("sheet_row") or 0),
        )
    else:
        catalog_work = augment_catalog_with_harness(
            catalog,
            kpi,
            filtros,
            visuales,
            tablero_aliases=tablero_aliases,
        )
    index = build_automation_index(kpi, filtros, visuales)
    fecha = date.today().strftime("%d/%m/%Y")
    cases_in = catalog_work.get("cases") or []

    prev_by_key: dict[str, dict[str, Any]] = {}
    if entrada_previa:
        for row in entrada_previa.get("filas") or []:
            prev_by_key[row.get("case_key") or ""] = row

    selected_cases: list[dict[str, Any]] = []
    for case in cases_in:
        if solo_fallidos_anterior and entrada_previa:
            prev = prev_by_key.get(_case_result_key(case))
            if not prev:
                continue
            prev_estado = (prev.get("revision") or {}).get("estado") or ""
            if prev_estado not in _estados_error_para_filtro_previo():
                continue
        selected_cases.append(case)

    if modo == "regresion" and not selected_cases and solo_fallidos_anterior:
        selected_cases = list(cases_in)

    if modo == "regresion" and not solo_fallidos_anterior:
        selected_cases = list(cases_in)

    if modo == "recorrida":
        selected_cases = list(cases_in)

    filas_out: list[dict[str, Any]] = []
    patches: list[dict[str, Any]] = []
    caps_estado = _caps()["estado"]
    counts = {
        caps_estado["aprobado"]: 0,
        caps_estado["error"]: 0,
        caps_estado["sin_revisar"]: 0,
    }
    catalog_patches_all: list[dict[str, Any]] = []
    from .planilla_visual_match import PageVisualState

    page_visual_states: dict[str, PageVisualState] = {}

    sheet_title = hoja_planilla
    if modo == "regresion":
        sheet_title = nombre_hoja_nueva or f"Revision {fecha}"

    for case in selected_cases:
        tab_key = _tablero_lookup_key(case.get("tablero") or "", tablero_aliases)
        pv_state = page_visual_states.setdefault(tab_key, PageVisualState())
        binding = resolve_case_binding(
            case,
            index,
            tablero_aliases=tablero_aliases,
            planilla_bindings=planilla_bindings,
            visuales=visuales,
            page_visual_state=pv_state,
        )
        auto = _lookup_automation(binding, index, tablero_aliases=tablero_aliases)
        inferred = _infer_pasos_y_resultado(case, binding, auto)
        catalog_patches_all.extend(_catalog_field_patches(case, inferred))
        case_for_row = {**case, **inferred}
        allowed_tipos = set(_caps().get("tipo_prueba") or [])
        prev_tipo = (case.get("tipo_prueba") or "").strip()
        capa_bind = (binding or {}).get("capa") or (auto or {}).get("capa")
        tipo_norm = _normalizar_tipo_prueba_catalogo(
            case_for_row.get("tipo_prueba"),
            capa=str(capa_bind) if capa_bind else None,
        )
        if not (case.get("tipo_prueba") or "").strip() and inferred.get("tipo_prueba_inferido"):
            tipo_norm = inferred["tipo_prueba_inferido"]
        case_for_row["tipo_prueba"] = tipo_norm
        if (
            tipo_norm
            and prev_tipo not in allowed_tipos
            and case.get("sheet_row")
            and (auto is not None or binding)
        ):
            catalog_patches_all.append(
                {
                    "sheet_row": int(case["sheet_row"]),
                    "col": "F",
                    "field": "tipo_prueba",
                    "value": tipo_norm,
                }
            )
        revision = _revision_from_run(
            auto,
            case=case_for_row,
            binding=binding,
            inferred=inferred,
            fecha=fecha,
            caps=_caps(),
        )

        prev_block = None
        if modo == "recorrida" and entrada_previa:
            prev = prev_by_key.get(_case_result_key(case))
            if prev and prev.get("revision"):
                prev_block = prev["revision"]

        revision_blocks: list[dict[str, str]]
        if modo == "recorrida":
            blocks_count = max(revision_index, 1)
            revision_blocks = [_empty_revision_block() for _ in range(blocks_count)]
            for i in range(blocks_count):
                if i + 1 == revision_index:
                    if auto:
                        revision_blocks[i] = revision
                    elif prev_block:
                        revision_blocks[i] = prev_block
                elif prev_block and entrada_previa:
                    prev_rev = (prev_by_key.get(_case_result_key(case)) or {}).get(
                        "revisiones"
                    )
                    if isinstance(prev_rev, list) and i < len(prev_rev):
                        revision_blocks[i] = prev_rev[i]
        else:
            revision_blocks = [revision, _empty_revision_block()]

        estado = revision_blocks[0 if modo == "regresion" else revision_index - 1].get(
            "estado", "Sin revisar"
        )
        if auto:
            counts[estado] = counts.get(estado, 0) + 1
        else:
            counts["Sin revisar"] = counts.get("Sin revisar", 0) + 1

        fila = {
            "case_key": _case_result_key(case),
            "sheet_row": case.get("sheet_row"),
            "catalog": case_for_row,
            "catalog_patches": _catalog_field_patches(case, inferred),
            "revision": revision if auto else _empty_revision_block(),
            "revisiones": revision_blocks,
            "automation": auto,
            "binding": binding,
            "catalog_nuevo": bool(case.get("catalog_nuevo")),
        }
        filas_out.append(fila)

        if auto and sheet_title and case.get("sheet_row"):
            start = revision_start_col(
                revision_index if modo == "recorrida" else 1
            )
            col = _col_letter(start)
            row = int(case["sheet_row"])
            rev_idx = revision_index if modo == "recorrida" else 1
            block = revision_blocks[rev_idx - 1]
            patches.append(
                {
                    "range": f"'{sheet_title}'!{col}{row}:{_col_letter(start + REVISION_WIDTH - 1)}{row}",
                    "values": [[block.get(n, "") for n in REVISION_FIELD_NAMES]],
                }
            )

    grid_rows = header_rows(revision_count=2)
    for fila in filas_out:
        grid_rows.append(
            _row_to_sheet_values(fila["catalog"], fila["revisiones"])
        )

    extras: list[dict[str, Any]] = []
    for key, auto in index.items():
        if auto.get("veredicto") != "fallido":
            continue
        pk, capa, internal = key
        if capa == "visuales":
            extras.append(
                {
                    "tablero": pk,
                    "capa": capa,
                    "identificador": internal,
                    "detalle": auto.get("detalle"),
                    "lectura_qa": auto.get("lectura_qa"),
                }
            )

    source = catalog.get("source") or {}
    template_title = source.get("sheet_title") or source.get("template_sheet_title")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "modo": modo,
        "spreadsheet_id": source.get("spreadsheet_id"),
        "template_sheet_title": template_title,
        "template_sheet_id": source.get("template_sheet_id"),
        "sheet_title": sheet_title,
        "revision_index": revision_index if modo == "recorrida" else 1,
        "solo_fallidos_anterior": solo_fallidos_anterior,
        "run": run_meta or {},
        "resumen": {
            "filas_catalogo": len(selected_cases),
            "con_automatizacion": sum(1 for f in filas_out if f.get("automation")),
            "estados_automatizados": counts,
        },
        "filas": filas_out,
        "grid_csv": _grid_to_csv(grid_rows),
        "sheets_patch": patches,
        "extras_sin_fila_catalogo": extras,
        "catalog_field_patches": catalog_patches_all,
        "catalog_augmented": catalog_work.get("catalog_augmented"),
        "publicar_solo_automatizados": True,
        "limpiar_bloques_revision_en_recorrida": bool(
            (_caps().get("politica") or {}).get(
                "recorrida_limpiar_revision_antes_de_publicar"
            )
            and modo == "recorrida"
        ),
    }
    try:
        from .planilla_publish import build_publish_plan

        payload["publish_plan"] = build_publish_plan(
            payload,
            template_sheet_id=source.get("template_sheet_id"),
            template_sheet_title=template_title,
        )
    except (ValueError, TypeError):
        payload["publish_plan"] = None
    return payload


def _grid_to_csv(rows: Iterable[list[str]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def load_corrida_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))
