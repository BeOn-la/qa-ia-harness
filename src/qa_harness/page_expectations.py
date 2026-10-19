from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import ContractError


def load_scope_kpis(board_qa_root: Path) -> dict[str, Any]:
    path = board_qa_root / "scope-kpis.json"
    if not path.is_file():
        raise ContractError(f"Falta lista de indicadores contratados: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    rows = data.get("indicadores_contratados")
    if not isinstance(rows, list) or not rows:
        raise ContractError("scope-kpis.json debe tener indicadores_contratados[].")
    return data


def contracted_kpi_ids(scope_doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in scope_doc["indicadores_contratados"]:
        kid = row.get("identificador_indicador")
        if isinstance(kid, str) and kid:
            out.add(kid)
    return out


def load_page_expectations(board_qa_root: Path) -> dict[str, Any]:
    path = board_qa_root / "page-expectations.json"
    if not path.is_file():
        raise ContractError(f"Falta definición de hojas: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    hojas = data.get("hojas")
    if not isinstance(hojas, dict):
        raise ContractError("page-expectations.json debe tener objeto 'hojas'.")
    return data


def audit_page_names(
    expectations: dict[str, Any],
    report_display_names: list[str],
) -> dict[str, Any]:
    """Detecta desalineación entre page.json y page-expectations.json."""
    defined = set(expectations.get("hojas", {}).keys())
    actual = set(report_display_names)
    solo_en_informe = sorted(actual - defined)
    solo_en_definicion = sorted(defined - actual)
    alineado = not solo_en_informe and not solo_en_definicion
    return {
        "nombres_alineados": alineado,
        "hojas_en_informe_sin_definicion": solo_en_informe,
        "definiciones_sin_hoja_en_informe": solo_en_definicion,
        "detalle": (
            "Los nombres de hoja coinciden con page-expectations.json."
            if alineado
            else "Revisar displayName del informe vs claves en page-expectations.json."
        ),
    }


def load_alcance_ajustes_planilla(board_qa_root: Path) -> dict[str, Any]:
    path = board_qa_root / "alcance-ajustes-planilla.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data.get("por_hoja") if isinstance(data.get("por_hoja"), dict) else {}


def _aplicar_ajustes_alcance(
    display_name: str,
    faltantes: list[str],
    fuera: list[str],
    ajustes_por_hoja: dict[str, Any],
) -> tuple[list[str], list[str]]:
    reglas = ajustes_por_hoja.get(display_name) or {}
    no_exigir = set(reglas.get("no_exigir_visibles") or [])
    no_fuera = set(reglas.get("no_marcar_fuera_contrato") or [])
    f = [x for x in faltantes if x not in no_exigir]
    u = [x for x in fuera if x not in no_fuera]
    return f, u


def expectation_for_page(expectations: dict[str, Any], display_name: str) -> dict[str, Any] | None:
    hojas = expectations.get("hojas", {})
    spec = hojas.get(display_name)
    if isinstance(spec, dict):
        return spec
    return None


def expected_kpi_ids_on_page(
    spec: dict[str, Any] | None,
    contracted: set[str],
) -> set[str]:
    if spec is None:
        return set()
    return _expected_ids_for_page(spec, contracted)


def _expected_ids_for_page(
    spec: dict[str, Any],
    contracted: set[str],
) -> set[str]:
    raw = spec.get("indicadores_esperados")
    if raw == "todos_los_del_contrato":
        return set(contracted)
    if isinstance(raw, list):
        return {str(x) for x in raw}
    return set()


def evaluate_scope_on_page(
    *,
    spec: dict[str, Any] | None,
    contracted: set[str],
    shown_kpi_ids: set[str],
    catalog_ids: set[str],
    display_name: str = "",
    alcance_ajustes_por_hoja: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validación de alcance según el rol de la hoja (contrato vs visuales)."""
    if spec is None:
        return {
            "veredicto_alcance": "sin_definicion",
            "detalle": "No hay entrada en page-expectations.json para esta hoja.",
            "indicadores_contrato_faltantes_en_hoja": [],
            "indicadores_fuera_de_contrato_en_hoja": [],
        }

    modo = spec.get("validacion_alcance", "")
    interpretacion = spec.get("interpretacion", "")
    tipo_hoja = spec.get("tipo_hoja", "")

    if modo == "no_aplica" or modo == "solo_informativo":
        return {
            "tipo_hoja": tipo_hoja,
            "interpretacion_hoja": interpretacion,
            "veredicto_alcance": "no aplica",
            "detalle": "Esta hoja no exige validación de alcance contractual.",
            "indicadores_contrato_faltantes_en_hoja": [],
            "indicadores_fuera_de_contrato_en_hoja": [],
        }

    esperados = _expected_ids_for_page(spec, contracted)
    faltantes = sorted(esperados - shown_kpi_ids)
    # Fuera de contrato: visibles en hoja, en catálogo del tablero, no en los 10 del scope
    fuera = sorted((shown_kpi_ids & catalog_ids) - contracted)
    if alcance_ajustes_por_hoja and display_name:
        faltantes, fuera = _aplicar_ajustes_alcance(
            display_name, faltantes, fuera, alcance_ajustes_por_hoja
        )

    if modo == "resumen_estricto_contrato":
        veredicto = "correcto"
        partes: list[str] = []
        if faltantes:
            veredicto = "fallido"
            partes.append(
                "Faltan indicadores del contrato en el resumen: " + ", ".join(faltantes)
            )
        if fuera:
            veredicto = "fallido"
            partes.append(
                "Hay indicadores en la hoja que no están en el contrato: " + ", ".join(fuera)
            )
        if not partes:
            partes.append("El resumen muestra exactamente los indicadores contratados.")
        return {
            "tipo_hoja": tipo_hoja,
            "interpretacion_hoja": interpretacion,
            "veredicto_alcance": veredicto,
            "detalle": " ".join(partes),
            "indicadores_contrato_faltantes_en_hoja": faltantes,
            "indicadores_fuera_de_contrato_en_hoja": fuera,
        }

    if modo in ("deben_aparecer_todos_los_del_contrato", "subconjunto_contrato"):
        veredicto = "correcto" if not faltantes else "fallido"
        detalle = (
            "Todos los indicadores esperados aparecen en la hoja."
            if not faltantes
            else "Faltan indicadores esperados: " + ", ".join(faltantes)
        )
        if modo == "deben_aparecer_todos_los_del_contrato" and fuera:
            detalle += (
                " (En esta hoja pueden existir indicadores extra del tablero: "
                + ", ".join(fuera)
                + ".)"
            )
        return {
            "tipo_hoja": tipo_hoja,
            "interpretacion_hoja": interpretacion,
            "veredicto_alcance": veredicto,
            "detalle": detalle,
            "indicadores_contrato_faltantes_en_hoja": faltantes,
            "indicadores_fuera_de_contrato_en_hoja": fuera if modo == "resumen_estricto_contrato" else [],
        }

    return {
        "tipo_hoja": tipo_hoja,
        "interpretacion_hoja": interpretacion,
        "veredicto_alcance": "sin_definicion",
        "detalle": f"Modo de validación desconocido: {modo}",
        "indicadores_contrato_faltantes_en_hoja": [],
        "indicadores_fuera_de_contrato_en_hoja": [],
    }
