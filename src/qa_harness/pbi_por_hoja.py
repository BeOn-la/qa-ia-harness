from __future__ import annotations

from pathlib import Path
from typing import Any

from .board_profiles import kpi_catalog_root, resolve_board_from_ref
from .common import ContractError
from .kpi_catalog import load_kpi_catalog
from .pbi_filter_scope import compare_filter, run_filter_scope_sql_values
from .pbi_kpi_month import run_month_oracles
from .report_filters import discover_page_filter_ids, load_scope_filters
from .report_pages import (
    dax_measures_on_page,
    kpi_shown_on_page,
    list_report_pages,
    page_result_shell,
    select_pages,
)
from .page_expectations import (
    audit_page_names,
    contracted_kpi_ids,
    evaluate_scope_on_page,
    expectation_for_page,
    load_page_expectations,
    load_scope_kpis,
)
from .visual_interpretation import (
    cluster_visuals_by_row,
    evaluate_visual_contextual,
    list_visuals_enriched,
    load_bookmark_active_section,
    load_bookmark_labels,
    load_page_id_to_name,
)
from .page_expectations import expected_kpi_ids_on_page
from .sql_profiles import harness_root, load_local_profiles_config


def _veredicto_oraculo(row: dict[str, Any] | None) -> str:
    if row is None:
        return "fallido"
    if row.get("compare_status") == "pass":
        return "correcto"
    return "fallido"


def run_kpi_por_hoja(
    *,
    harness_root_path: Path | None = None,
    profile: str,
    board_id: str | None = None,
    board_ref: str | None = None,
    hoja: str | None = None,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    if board_ref and board_id:
        raise ContractError("Usar solo --board o --ref, no ambos.")

    root = harness_root_path or harness_root()
    config = load_local_profiles_config(root)
    bid, board, ctx = resolve_board_from_ref(root, config, board_ref or board_id)
    report_path = Path(ctx["report_path"] or "")
    if not report_path.is_dir():
        raise ContractError("resolve-board no devolvió report_path.")

    board_path = Path(ctx["board_qa_root"])
    catalog = load_kpi_catalog(kpi_catalog_root(root, board) / "kpi-catalog.yml")
    catalog_ids = {str(e["kpi_id"]) for e in catalog}
    scope_doc = load_scope_kpis(board_path)
    contracted = contracted_kpi_ids(scope_doc)
    page_expectations = load_page_expectations(board_path)

    oracle = run_month_oracles(
        harness_root_path=root,
        profile=profile,
        board_id=board_id,
        board_ref=board_ref,
        timeout_seconds=timeout_seconds,
    )
    by_kpi = {str(r.get("kpi_id")): r for r in oracle.get("rows", []) if r.get("kpi_id")}

    all_pages = list_report_pages(report_path)
    pages = select_pages(all_pages, hoja)
    revision_nombres_hojas = audit_page_names(
        page_expectations,
        [p.display_name for p in all_pages],
    )
    hojas_out: list[dict[str, Any]] = []
    for page in pages:
        measures = dax_measures_on_page(report_path, page.page_id)
        shown_ids = {
            str(entry["kpi_id"])
            for entry in catalog
            if kpi_shown_on_page(entry, measures)
        }
        spec = expectation_for_page(page_expectations, page.display_name)
        alcance = evaluate_scope_on_page(
            spec=spec,
            contracted=contracted,
            shown_kpi_ids=shown_ids,
            catalog_ids=catalog_ids,
        )

        casos: list[dict[str, Any]] = []
        casos.append(
            {
                "tipo_caso": "alcance contractual en la hoja",
                "nombre_caso": "Indicadores visibles vs contrato",
                "se_muestra_en_esta_hoja": True,
                "veredicto_comparacion_sql": "no aplica",
                "veredicto_alcance": alcance.get("veredicto_alcance"),
                "detalle": alcance.get("detalle"),
                "indicadores_contrato_faltantes": alcance.get(
                    "indicadores_contrato_faltantes_en_hoja", []
                ),
                "indicadores_fuera_de_contrato": alcance.get(
                    "indicadores_fuera_de_contrato_en_hoja", []
                ),
            }
        )
        for entry in catalog:
            shown = kpi_shown_on_page(entry, measures)
            caso: dict[str, Any] = {
                "tipo_caso": "oráculo sql mensual del indicador",
                "identificador_indicador": entry["kpi_id"],
                "nombre_indicador_en_inicio": entry.get("home_label", ""),
                "nombre_medida_dax": entry["dax_measure"],
                "pertenece_al_contrato": str(entry["kpi_id"]) in contracted,
                "se_muestra_en_esta_hoja": shown,
            }
            if not shown:
                caso["veredicto_comparacion_sql"] = "no aplica"
                caso["detalle"] = (
                    "Este indicador no está en los visuales de la hoja; no se exige oráculo aquí."
                )
            else:
                row = by_kpi.get(str(entry["kpi_id"]))
                caso["veredicto_comparacion_sql"] = _veredicto_oraculo(row)
                if row is None:
                    caso["detalle"] = "Falta fila en el oráculo mensual (from-dax vs from-definition)."
                elif caso["veredicto_comparacion_sql"] == "fallido":
                    caso["detalle"] = "Los dos oráculos SQL no coinciden dentro de tolerancia."
                else:
                    caso["detalle"] = "Coinciden from-dax y from-definition."
                if row:
                    caso["valor_desde_logica_dax"] = row.get("from_dax")
                    caso["valor_desde_definicion"] = row.get("from_definition")
                    caso["diferencia_absoluta"] = row.get("abs_delta")
                    caso["cantidad_filas_universo"] = row.get("row_count")
            casos.append(caso)
        shell = page_result_shell(page)
        shell["interpretacion_hoja"] = alcance.get("interpretacion_hoja") or (
            spec.get("interpretacion") if spec else None
        )
        shell["tipo_hoja"] = alcance.get("tipo_hoja")
        shell["validacion_alcance"] = alcance
        shell["casos_de_prueba"] = casos
        hojas_out.append(shell)

    hay_fallos = any(
        c.get("veredicto_comparacion_sql") == "fallido"
        or c.get("veredicto_alcance") == "fallido"
        for h in hojas_out
        for c in h["casos_de_prueba"]
    )
    return {
        "capa": "indicadores clave de rendimiento",
        "estado_general": "correcto" if not hay_fallos else "con fallos",
        "codigo_salida": 0 if not hay_fallos else 1,
        "perfil_sql": profile,
        "identificador_tablero": bid,
        "version_tablero": ctx.get("version_id"),
        "referencia_contrato_indicadores": scope_doc.get("scope_label"),
        "revision_nombres_hojas": revision_nombres_hojas,
        "hojas": hojas_out,
        "indicadores_fallidos_globales": oracle.get("failed_kpi_ids") or [],
        "detalle_tecnico_oraculo_mensual": oracle,
    }


def run_filtros_por_hoja(
    *,
    harness_root_path: Path | None = None,
    profile: str,
    board_id: str | None = None,
    board_ref: str | None = None,
    hoja: str | None = None,
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    if board_ref and board_id:
        raise ContractError("Usar solo --board o --ref, no ambos.")

    root = harness_root_path or harness_root()
    config = load_local_profiles_config(root)
    bid, board, ctx = resolve_board_from_ref(root, config, board_ref or board_id)
    report_path = Path(ctx["report_path"] or "")
    board_path = Path(ctx["board_qa_root"])
    scope_doc = load_scope_filters(board_path)
    sql_values = run_filter_scope_sql_values(
        root,
        config,
        profile,
        board_id,
        board_ref,
        timeout_seconds,
    )

    pages = select_pages(list_report_pages(report_path), hoja)
    hojas_out: list[dict[str, Any]] = []
    try:
        page_expectations = load_page_expectations(board_path)
    except ContractError:
        page_expectations = {"hojas": {}}

    for page in pages:
        spec = expectation_for_page(page_expectations, page.display_name)
        page_filters = discover_page_filter_ids(report_path, page.page_id)
        casos: list[dict[str, Any]] = []
        for filter_id, spec in scope_doc["filters"].items():
            refs = page_filters.get(filter_id)
            caso: dict[str, Any] = {
                "identificador_filtro": filter_id,
                "nombre_filtro": spec.get("label", filter_id),
                "se_muestra_en_esta_hoja": bool(refs),
            }
            if not refs:
                caso["veredicto_contrato"] = "no aplica"
                caso["valores_en_modelo"] = []
                caso["detalle"] = "Este filtro no tiene slicer ni campo equivalente en la hoja."
            else:
                cmp = compare_filter(filter_id, spec, sql_values, refs)
                caso["veredicto_contrato"] = (
                    "correcto" if cmp["status"] == "ok" else "fallido"
                )
                caso["valores_en_modelo"] = cmp["valores"]
                caso["detalle"] = cmp.get("detail") or "Valores del modelo alineados al contrato."
                caso["campos_en_visuales"] = refs
            casos.append(caso)
        shell = page_result_shell(page)
        shell["interpretacion_hoja"] = spec.get("interpretacion") if spec else None
        shell["tipo_hoja"] = spec.get("tipo_hoja") if spec else None
        shell["casos_de_prueba"] = casos
        hojas_out.append(shell)

    hay_fallos = any(
        c.get("veredicto_contrato") == "fallido"
        for h in hojas_out
        for c in h["casos_de_prueba"]
    )
    return {
        "capa": "filtros del informe",
        "estado_general": "correcto" if not hay_fallos else "con fallos",
        "codigo_salida": 0 if not hay_fallos else 1,
        "perfil_sql": profile,
        "identificador_tablero": bid,
        "version_tablero": ctx.get("version_id"),
        "referencia_contrato": scope_doc.get("scope_label"),
        "hojas": hojas_out,
    }


def run_visuales_por_hoja(
    *,
    harness_root_path: Path | None = None,
    profile: str,
    board_id: str | None = None,
    board_ref: str | None = None,
    hoja: str | None = None,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    if board_ref and board_id:
        raise ContractError("Usar solo --board o --ref, no ambos.")

    root = harness_root_path or harness_root()
    config = load_local_profiles_config(root)
    bid, board, ctx = resolve_board_from_ref(root, config, board_ref or board_id)
    report_path = Path(ctx["report_path"] or "")
    board_path = Path(ctx["board_qa_root"])

    catalog = load_kpi_catalog(kpi_catalog_root(root, board) / "kpi-catalog.yml")
    catalog_ids = {str(e["kpi_id"]) for e in catalog}
    scope_kpi_doc = load_scope_kpis(board_path)
    contracted = contracted_kpi_ids(scope_kpi_doc)
    page_expectations = load_page_expectations(board_path)
    scope_filter_doc = load_scope_filters(board_path)

    oracle = run_month_oracles(
        harness_root_path=root,
        profile=profile,
        board_id=board_id,
        board_ref=board_ref,
        timeout_seconds=timeout_seconds,
    )
    oracle_by_kpi = {str(r.get("kpi_id")): r for r in oracle.get("rows", []) if r.get("kpi_id")}

    sql_values = run_filter_scope_sql_values(
        root,
        config,
        profile,
        board_id,
        board_ref,
        min(timeout_seconds, 180),
    )

    all_pages = list_report_pages(report_path)
    pages = select_pages(all_pages, hoja)
    revision_nombres_hojas = audit_page_names(
        page_expectations,
        [p.display_name for p in all_pages],
    )
    contract_names = {
        str(r.get("identificador_indicador")): str(r.get("nombre_en_contrato", ""))
        for r in scope_kpi_doc.get("indicadores_contratados", [])
        if r.get("identificador_indicador")
    }
    bookmark_labels = load_bookmark_labels(report_path)
    bookmark_sections = load_bookmark_active_section(report_path)
    page_id_to_name = load_page_id_to_name(report_path)

    hojas_out: list[dict[str, Any]] = []
    for page in pages:
        page_spec = expectation_for_page(page_expectations, page.display_name)
        expected_on_page = expected_kpi_ids_on_page(page_spec, contracted)
        strict = bool(
            page_spec and page_spec.get("validacion_alcance") == "resumen_estricto_contrato"
        )

        page_filter_map = discover_page_filter_ids(report_path, page.page_id)
        filter_verdicts: dict[str, dict[str, Any]] = {}
        for filter_id, fspec in scope_filter_doc["filters"].items():
            if filter_id not in page_filter_map:
                continue
            filter_verdicts[filter_id] = compare_filter(
                filter_id,
                fspec,
                sql_values,
                page_filter_map[filter_id],
            )

        enriched = list_visuals_enriched(report_path, page.page_id)
        row_map = cluster_visuals_by_row(enriched)
        casos: list[dict[str, Any]] = []
        for orden, visual in enumerate(enriched, start=1):
            caso = {
                "tipo_caso": "visual del informe",
                "orden_en_hoja": orden,
                "posicion_en_canvas": {
                    "x": round(visual.x, 1),
                    "y": round(visual.y, 1),
                    "ancho": round(visual.width, 1),
                    "alto": round(visual.height, 1),
                },
                **evaluate_visual_contextual(
                    visual=visual,
                    page_display_name=page.display_name,
                    row_peers=row_map.get(visual.visual_id, [visual]),
                    page_spec=page_spec,
                    contracted=contracted,
                    expected_on_page=expected_on_page,
                    strict_contract=strict,
                    catalog=catalog,
                    filter_verdicts=filter_verdicts,
                    oracle_by_kpi=oracle_by_kpi,
                    contract_names=contract_names,
                    bookmark_labels=bookmark_labels,
                    bookmark_sections=bookmark_sections,
                    page_id_to_name=page_id_to_name,
                    page_visuals=enriched,
                ),
            }
            casos.append(caso)

        shell = page_result_shell(page)
        shell["interpretacion_hoja"] = page_spec.get("interpretacion") if page_spec else None
        shell["tipo_hoja"] = page_spec.get("tipo_hoja") if page_spec else None
        shell["cantidad_visuales"] = len(casos)
        shell["casos_de_prueba"] = casos
        hojas_out.append(shell)

    hay_fallos = any(
        c.get("veredicto") == "fallido" for h in hojas_out for c in h["casos_de_prueba"]
    )
    return {
        "capa": "visuales del informe",
        "estado_general": "correcto" if not hay_fallos else "con fallos",
        "codigo_salida": 0 if not hay_fallos else 1,
        "perfil_sql": profile,
        "identificador_tablero": bid,
        "version_tablero": ctx.get("version_id"),
        "referencia_contrato_indicadores": scope_kpi_doc.get("scope_label"),
        "revision_nombres_hojas": revision_nombres_hojas,
        "hojas": hojas_out,
    }
