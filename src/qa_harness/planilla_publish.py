from __future__ import annotations

from typing import Any

from .planilla_qa import (
    CORRIDA_REPO_REVISION_1_START_COL,
    REVISION_FIELD_NAMES,
    REVISION_WIDTH,
    _col_letter,
    revision_start_col,
)


def build_publish_plan(
    export: dict[str, Any],
    *,
    template_sheet_id: int | None = None,
    template_sheet_title: str | None = None,
) -> dict[str, Any]:
    """
    Plan ordenado para publicar en Google Sheets vía MCP (plugin-google-sheets).

    Regla de formato: nunca reescribir A:F salvo import inicial del catálogo.
    En regresión se duplica la pestaña plantilla (formato + validaciones / cápsulas)
    y solo se limpian / escriben columnas de revisión.
    """
    spreadsheet_id = export.get("spreadsheet_id")
    if not spreadsheet_id:
        raise ValueError("export sin spreadsheet_id; completar source en el catálogo.")

    modo = export.get("modo")
    target_sheet = export.get("sheet_title") or ""
    template_title = template_sheet_title or export.get("template_sheet_title") or ""
    rev_index = int(export.get("revision_index") or 1)

    filas = sorted(
        [f for f in export.get("filas") or [] if f.get("sheet_row")],
        key=lambda f: int(f["sheet_row"]),
    )
    if not filas:
        return {
            "spreadsheet_id": spreadsheet_id,
            "modo": modo,
            "target_sheet_title": target_sheet,
            "pasos": [],
            "notas": ["Sin filas con sheet_row; nada que publicar."],
        }

    first_row = int(filas[0]["sheet_row"])
    last_row = int(filas[-1]["sheet_row"])

    pasos: list[dict[str, Any]] = []
    notas = [
        "Las cápsulas (validación de datos) viven en la pestaña plantilla; "
        "duplicar la pestaña antes de escribir valores de revisión.",
        "No usar write_range sobre A:F salvo parches C/D documentados (celdas vacías en catálogo).",
        "batch_clear_values borra solo valores; mantiene formato y validaciones.",
    ]

    if modo == "regresion":
        if template_sheet_id is None:
            notas.append(
                "Falta template_sheet_id en catálogo: el agente debe leer get_spreadsheet "
                f"y usar la pestaña plantilla '{template_title}'."
            )
        pasos.append(
            {
                "orden": 1,
                "herramienta_mcp": "copy_sheet_to_another_spreadsheet",
                "argumentos": {
                    "spreadsheetId": spreadsheet_id,
                    "sheetId": template_sheet_id,
                    "destinationSpreadsheetId": spreadsheet_id,
                },
                "resultado_esperado": "Nueva pestaña 'Copy of …' al final del documento.",
            }
        )
        pasos.append(
            {
                "orden": 2,
                "herramienta_mcp": "rename_sheet_tab",
                "argumentos": {
                    "spreadsheetId": spreadsheet_id,
                    "sheetId": "{{sheetId_de_la_copia}}",
                    "title": target_sheet,
                },
                "nota": "Reemplazar sheetId con el devuelto en el paso 1.",
            }
        )
        clear_end_col = _col_letter(revision_start_col(2) + REVISION_WIDTH - 1)
        pasos.append(
            {
                "orden": 3,
                "herramienta_mcp": "batch_clear_values",
                "argumentos": {
                    "spreadsheetId": spreadsheet_id,
                    "ranges": [
                        f"'{target_sheet}'!G{first_row}:{clear_end_col}{last_row}",
                    ],
                },
                "nota": "Limpia ambos bloques Revision 1 y 2 antes de cargar la corrida.",
            }
        )
        write_start = rev_index
    else:
        write_start = rev_index
        if export.get("limpiar_bloques_revision_en_recorrida"):
            clear_end_col = _col_letter(revision_start_col(2) + REVISION_WIDTH - 1)
            pasos.append(
                {
                    "orden": len(pasos) + 1,
                    "herramienta_mcp": "batch_clear_values",
                    "argumentos": {
                        "spreadsheetId": spreadsheet_id,
                        "ranges": [
                            f"'{target_sheet}'!G{first_row}:{clear_end_col}{last_row}",
                        ],
                    },
                    "nota": "Recorrida completa: limpia Revision 1 y 2 antes de volver a cargar.",
                }
            )

    solo_auto = bool(export.get("publicar_solo_automatizados", modo == "recorrida"))

    catalog_steps = _catalog_new_row_af_steps(filas, sheet_title=target_sheet)
    for step in catalog_steps:
        pasos.append(
            {
                "orden": len(pasos) + 1,
                "herramienta_mcp": "write_range",
                "argumentos": {
                    "spreadsheetId": spreadsheet_id,
                    "sheet": target_sheet,
                    "cells": step["cells"],
                    "values": step["values"],
                    "parseInput": False,
                },
                "nota": step.get("nota"),
            }
        )

    catalog_steps = _catalog_field_write_steps(
        filas,
        sheet_title=target_sheet,
        only_automated=solo_auto,
    )
    for step in catalog_steps:
        pasos.append(
            {
                "orden": len(pasos) + 1,
                "herramienta_mcp": "write_range",
                "argumentos": {
                    "spreadsheetId": spreadsheet_id,
                    "sheet": target_sheet,
                    "cells": step["cells"],
                    "values": step["values"],
                    "parseInput": False,
                },
                "nota": step.get("nota"),
            }
        )

    batches = _revision_write_batches(
        filas,
        sheet_title=target_sheet,
        revision_index=write_start,
        only_automated=solo_auto,
    )
    for i, batch in enumerate(batches, start=len(pasos) + 1):
        pasos.append(
            {
                "orden": i,
                "herramienta_mcp": "write_range",
                "argumentos": {
                    "spreadsheetId": spreadsheet_id,
                    "sheet": target_sheet,
                    "cells": batch["cells"],
                    "values": batch["values"],
                    "parseInput": False,
                },
                "filas": batch.get("row_count"),
            }
        )

    return {
        "schema_version": 1,
        "spreadsheet_id": spreadsheet_id,
        "modo": modo,
        "template_sheet_title": template_title,
        "template_sheet_id": template_sheet_id,
        "target_sheet_title": target_sheet,
        "revision_index": write_start,
        "fila_desde": first_row,
        "fila_hasta": last_row,
        "pasos": pasos,
        "notas": notas,
        "mapeo_capas": _mapeo_capas_doc(),
    }


def _catalog_new_row_af_steps(
    filas: list[dict[str, Any]],
    *,
    sheet_title: str,
) -> list[dict[str, Any]]:
    """Filas nuevas del harness: escribe A:F completas (no pisa catálogo original)."""
    steps: list[dict[str, Any]] = []
    for fila in filas:
        if not fila.get("catalog_nuevo") or not fila.get("sheet_row"):
            continue
        cat = fila.get("catalog") or {}
        row = int(fila["sheet_row"])
        steps.append(
            {
                "cells": f"A{row}:F{row}",
                "values": [
                    [
                        cat.get("id") or "",
                        cat.get("caso_de_prueba") or "",
                        cat.get("pasos_a_seguir") or "",
                        cat.get("resultado_esperado") or "",
                        cat.get("tablero") or "",
                        cat.get("tipo_prueba") or "",
                    ]
                ],
                "nota": "Fila agregada por corrida (caso no estaba en planilla); conservar en catálogo JSON.",
            }
        )
    return steps


def _catalog_field_write_steps(
    filas: list[dict[str, Any]],
    *,
    sheet_title: str,
    only_automated: bool,
) -> list[dict[str, Any]]:
    """Escribe C/D solo cuando el catálogo local tenía el campo vacío (parches por fila)."""
    steps: list[dict[str, Any]] = []
    for fila in filas:
        if only_automated and not fila.get("automation"):
            continue
        patches = fila.get("catalog_patches") or []
        if not patches:
            continue
        row = int(fila["sheet_row"])
        for p in patches:
            col = p["col"]
            steps.append(
                {
                    "cells": f"{col}{row}",
                    "values": [[p["value"]]],
                    "nota": (
                        f"Completar {p['field']} vacío en catálogo; no sobrescribir texto manual existente."
                    ),
                }
            )
    return steps


def _revision_write_batches(
    filas: list[dict[str, Any]],
    *,
    sheet_title: str,
    revision_index: int,
    only_automated: bool,
    max_rows_per_batch: int = 80,
) -> list[dict[str, Any]]:
    start_col = revision_start_col(revision_index)
    end_col = start_col + REVISION_WIDTH - 1
    col_a = _col_letter(start_col)
    col_b = _col_letter(end_col)

    pending: list[list[str]] = []
    pending_rows: list[int] = []
    batches: list[dict[str, Any]] = []

    def flush() -> None:
        if not pending:
            return
        r0 = pending_rows[0]
        r1 = pending_rows[-1]
        batches.append(
            {
                "cells": f"{col_a}{r0}:{col_b}{r1}",
                "values": [row[:] for row in pending],
                "row_count": len(pending),
            }
        )
        pending.clear()
        pending_rows.clear()

    for fila in filas:
        if only_automated and not fila.get("automation"):
            flush()
            continue
        rev_blocks = fila.get("revisiones") or []
        if revision_index - 1 >= len(rev_blocks):
            continue
        block = rev_blocks[revision_index - 1]
        row = int(fila["sheet_row"])
        if pending_rows and row != pending_rows[-1] + 1:
            flush()
        pending_rows.append(row)
        pending.append([block.get(name, "") for name in REVISION_FIELD_NAMES])
        if len(pending) >= max_rows_per_batch:
            flush()
    flush()
    return batches


def build_corrida_repo_publish_plan(
    *,
    spreadsheet_id: str,
    template_sheet_id: int | None,
    template_sheet_title: str,
    target_sheet_title: str,
    data_row_count: int,
    adc_batch_ranges: list[str],
    board_qa_tools_relative: str = "tools",
) -> dict[str, Any]:
    """
    Plan para pestaña Corrida repo (grid A–G + revisiones, columna E Resultado Obtenido).
    Subida de datos preferida: ADC (upload_corrida_repo_batches.py), sin embed de values en el plan.
    """
    last_row = max(data_row_count, 3)
    end_col = _col_letter(
        CORRIDA_REPO_REVISION_1_START_COL + REVISION_WIDTH * 2 - 1
    )
    pasos: list[dict[str, Any]] = []
    notas = [
        "Corrida repo: orden de hojas Alcance → KPI → Filtros → Visuales; IDs 0001… sin catálogo manual.",
        "Columna E = Resultado Obtenido; revisión 1 en H–R, revisión 2 en S–AC.",
        "Subida preferida: python tools/upload_corrida_repo_batches.py (ADC, 2–3 lotes, RAW).",
        "Fallback MCP (sin ADC): make_corrida_repo_batches.py --profile mcp-micro y write_range por chunk_*.json.",
    ]
    if template_sheet_id is None:
        notas.append(
            "Falta template_sheet_id en board.yml → planilla_qa; usar get_spreadsheet."
        )
    pasos.append(
        {
            "orden": 1,
            "herramienta_mcp": "copy_sheet_to_another_spreadsheet",
            "argumentos": {
                "spreadsheetId": spreadsheet_id,
                "sheetId": template_sheet_id,
                "destinationSpreadsheetId": spreadsheet_id,
            },
            "resultado_esperado": "Nueva pestaña 'Copy of …' al final.",
        }
    )
    pasos.append(
        {
            "orden": 2,
            "herramienta_mcp": "rename_sheet_tab",
            "argumentos": {
                "spreadsheetId": spreadsheet_id,
                "sheetId": "{{sheetId_de_la_copia}}",
                "title": target_sheet_title,
            },
            "nota": "Título sin / (ej. Corrida repo 16-10-26).",
        }
    )
    pasos.append(
        {
            "orden": 3,
            "herramienta_mcp": "insert_rows_or_columns",
            "argumentos": {
                "spreadsheetId": spreadsheet_id,
                "sheetId": "{{sheetId_pestaña_destino}}",
                "dimension": "COLUMNS",
                "position": 5,
                "count": 1,
                "inheritBefore": True,
            },
            "nota": "Inserta columna E (Resultado Obtenido) antes de Tablero.",
        }
    )
    pasos.append(
        {
            "orden": 4,
            "herramienta_mcp": "batch_clear_values",
            "argumentos": {
                "spreadsheetId": spreadsheet_id,
                "ranges": [f"'{target_sheet_title}'!A3:{end_col}{last_row}"],
            },
        }
    )
    pasos.append(
        {
            "orden": 5,
            "herramienta_mcp": "(script local)",
            "argumentos": {
                "comandos": [
                    f"cd {board_qa_tools_relative} && python make_corrida_repo_batches.py --profile adc",
                    "python upload_corrida_repo_batches.py",
                ],
                "requisito": "gcloud auth application-default login",
                "lotes_adc": adc_batch_ranges,
            },
            "nota": (
                "Sube el mismo grid que batches.json (valueInputOption=RAW). "
                "No incluir values en el chat del agente."
            ),
        }
    )
    pasos.append(
        {
            "orden": 6,
            "herramienta_mcp": "(script local)",
            "argumentos": {
                "comando": (
                    f"python {board_qa_tools_relative}/apply_corrida_sheet_from_template.py "
                    f'--target "{target_sheet_title}" --data-rows {last_row}'
                ),
            },
            "nota": "Extiende cápsulas (tipo H, revisión I:S) y formato fecha auditoría; requiere ADC Google.",
        }
    )
    return {
        "schema_version": 1,
        "modo": "corrida_repo",
        "spreadsheet_id": spreadsheet_id,
        "template_sheet_title": template_sheet_title,
        "template_sheet_id": template_sheet_id,
        "target_sheet_title": target_sheet_title,
        "fila_desde": 1,
        "fila_hasta": last_row,
        "columnas_fijas": "A–G (incluye Resultado Obtenido en E)",
        "pasos": pasos,
        "notas": notas,
        "subida_datos": {
            "preferida": "adc",
            "script": "tools/upload_corrida_repo_batches.py",
            "batch_ranges": adc_batch_ranges,
        },
        "subida_datos_fallback_mcp": {
            "generar": "python tools/make_corrida_repo_batches.py --profile mcp-micro",
            "archivos": "test-evidence/_corrida_repo_sheet/micro_upload/chunk_*.json",
            "nota": "Solo si no hay ADC; leer cada JSON y write_range sin truncar values.",
        },
        "artefactos": {
            "grid": "test-evidence/_corrida_repo_sheet/grid.json",
            "batches_adc": "test-evidence/_corrida_repo_sheet/batches.json",
        },
    }


def _mapeo_capas_doc() -> list[dict[str, str]]:
    return [
        {
            "tipo_prueba_planilla": "Filtros",
            "comando_harness": "pbi-filtros-por-hoja",
            "caso_catalogo": "Validar filtro de …",
            "columna_estado": "Revision N → Estado",
        },
        {
            "tipo_prueba_planilla": "KPI/Calculos",
            "comando_harness": "pbi-kpi-por-hoja",
            "caso_catalogo": "Validar KPI …",
            "columna_estado": "Oráculo SQL mensual (no la tarjeta visual en Home salvo caso manual)",
        },
        {
            "tipo_prueba_planilla": "(vacío / UI)",
            "comando_harness": "pbi-visuales-por-hoja + RevisionManual",
            "caso_catalogo": "Botones, estética, gráficos",
            "columna_estado": "Sin revisar hasta Desktop/manual; visuales fallidos en extras",
        },
        {
            "tipo_prueba_planilla": "Alcance (futuro en planilla)",
            "comando_harness": "pbi-kpi-por-hoja (primer caso por hoja)",
            "caso_catalogo": "Indicadores vs contrato",
            "columna_estado": "Observaciones QA automáticas",
        },
    ]
