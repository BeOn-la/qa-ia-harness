# Planilla Google ↔ comandos `/Calculo*`

## Qué automatizamos vs qué sigue manual

| Fila en la planilla (catálogo A–F) | Origen automático | Comando |
|-----------------------------------|-------------------|---------|
| `Validar filtro de …` + Tipo **Filtros** | Contrato `scope-filters.json` + SQL | `/CalculoFiltro` → `pbi-filtros-por-hoja` |
| `Validar KPI …` + **KPI/Calculos** | Oráculo mensual from-dax / from-definition | `/CalculoKPI` → `pbi-kpi-por-hoja` |
| Primer caso por hoja (alcance contractual) | `scope-kpis.json` + visuales en PBIP | `/CalculoScope` (mismo JSON KPI) |
| Botones, estética, gráficos sin mapping | Desktop / ojo humano | `/RevisionManual` |
| Visuales no listadas en catálogo | Interpretación PBIP | `/CalculoVisuales` → `extras_sin_fila_catalogo` |

La planilla **no se regenera desde el PBIP**: el catálogo (`manual-cases/planilla-catalog.json`) es la lista que ya usaban QA y desarrollo. El harness **rellena columnas de revisión** según la política en `schemas/planilla_revision_capsules.json`.

### Política de columnas de revisión (Revision N)

| Campo | Cuándo se escribe |
|-------|-------------------|
| **Estado** | `Aprobado` si la corrida automática OK; `Error` si falló (no usar «Rechazado»). |
| **Tipo de error**, **Prioridad**, **Controlado por** | Solo si Estado = `Error`, con valores de cápsula (ej. Datos / Alta / Desarrollo). |
| **Observaciones QA** | Solo en **Error**: **un comentario por fila/caso** (sin listas largas de filtros de otra hoja ni volcado de toda la página). Sin rutas de repos ni artefactos del harness. |
| **Tipo de prueba** (F) | Solo valores de cápsula: `Filtros`, `KPI/Calculos`, `Visuales` (no inventar tipos). |
| **Prioridad / Controlado por** | Solo valores listados en `planilla_revision_capsules.json` (`prioridad`, `controlado_por`). |
| **Observaciones Desarrollo** | Vacío en automático (lo completa el dev al corregir). |
| **Fecha de auditoría** | Fecha de la corrida automática. |
| **Pasos a seguir** / **Resultado esperado** (C/D) | Solo si la celda está **vacía** en catálogo: se infiere texto y se publica con `publish_plan` (no pisa texto manual). |

## Por qué puede tardar la publicación

1. **Corrida completa** (`corrida-planilla`): KPI + filtros + visuales sobre todas las hojas del `.Report` y SQL staging (varios minutos).
2. **Export grande**: cientos de filas con bloques de revisión de 11 columnas.
3. **Google Sheets MCP**: cada `write_range` es una llamada de red; conviene publicar con `tools/publish_export_batches.py` (lotes de ~15 filas) y no miles de parches celda a celda.
4. **Solo filas automatizadas** en recorrida (`publicar_solo_automatizados: true`): no reescribe toda la planilla, solo KPI/filtros/visuales mapeados (el resto queda Sin revisar hasta manual).

Observaciones en **Error**: texto corto y del **caso** (filtro/KPI/visual puntual), no el dump de toda la hoja.

## Formato y cápsulas (obligatorio)

El documento [QA - Tablero softys](https://docs.google.com/spreadsheets/d/1IiB3WAUIJQJNzJSmC6oLI2aZiGJYGW_qOqj1P8Bbo-Y/edit) es la **plantilla**:

- Filas 1–2: encabezados y bloques **Revision 1 / Revision 2**
- Columnas A–F: caso de prueba fijo (no pisar en corridas)
- Columnas G en adelante: validación de datos (cápsulas Estado, etc.)

**Regresión:** duplicar la pestaña plantilla con `copy_sheet_to_another_spreadsheet` (mismo spreadsheet), renombrar, limpiar valores de revisión, escribir resultados.

**Recorrida:** opcionalmente `batch_clear_values` en columnas de revisión (G en adelante) y luego escribir filas automatizadas (`limpiar_bloques_revision_en_recorrida` en el export). No crea pestaña nueva.

Nunca pegar CSV encima de la plantilla en Drive.

### Limitación MCP `write_range`

Google Sheets MCP **no escribe** en pestañas cuyo título contiene `/` (ej. `Revision 14/10/26`). Antes de publicar:

1. `rename_sheet_tab` → título sin barra (ej. `Revision 14-10-26`)
2. Ejecutar `write_range` / `batch_clear_values`
3. Opcional: volver a renombrar al título habitual (las lecturas con `read_range` toleran `/`)

En **regresión**, al duplicar la pestaña plantilla, conviene renombrar la copia sin `/` antes de automatizar.

## Flujo típico

1. Ajustás lógica del harness → `/PublicarPlanilla` con `modo=recorrida`.
2. Tablero corregido en repo → `modo=regresion` + pestaña nueva con fecha.
3. Opcional: `--solo-fallidos-anterior` para entregar al dev solo filas en **Error**.

## Sincronizar catálogo desde Sheets

Si cambian filas en la planilla manual:

1. MCP `read_range` pestaña plantilla **A3:F280** (o en tres rangos si el JSON es muy grande).
2. Guardar la respuesta en `qa-ia-harness/tools/_mcp_range_pull.json`.
3. `python tools/ingest_mcp_read_range_json.py tools/_mcp_range_pull.json -o .../manual-cases/planilla-catalog.json`

O: `python tools/pull_planilla_catalog_from_sheets.py` (tras el paso 2).

Incluir `template_sheet_id` en `source` del catálogo (desde `get_spreadsheet`).  
Alias planilla ↔ informe: `{board_qa_root}/planilla-tablero-aliases.json` (ver `board.yml`).

## Modo Corrida repo (evidencia por hoja, sin catálogo manual)

Cuando la planilla debe reflejar **toda** la corrida (alcance + KPI + filtros + visuales por hoja del informe), sin depender de `planilla-catalog.json`:

| Paso | Qué hace |
|------|----------|
| CLI | `qa-harness corrida-planilla --modo corrida_repo --ref …` |
| Grid | `{board_qa}/tools/build_corrida_repo_sheet.py` → `_corrida_repo_sheet/grid.json` (columna **E** = Resultado Obtenido) |
| Lotes ADC (preferido) | `make_corrida_repo_batches.py --profile adc` → `batches.json` (2–3 lotes, ~10k celdas c/u) |
| Subida datos | `upload_corrida_repo_batches.py` (ADC, **sin** pasar `values` por el agente → pocos tokens) |
| Fallback MCP | `--profile mcp-micro` → `micro_upload/chunk_*.json` solo si no hay ADC |
| `publish_plan` | MCP: copiar plantilla, columna E, limpiar → **script ADC** → `apply_corrida_sheet_from_template.py` |

Requisitos en `board_qa_root`: `tools/build_corrida_repo_sheet.py`, `tools/obs_corrida_sheet.py`, `alcance-ajustes-planilla.json` (si aplica), `board.yml` → `planilla_qa.spreadsheet_id` y `template_sheet_id`.

Política de texto: **Resultado esperado** = “debe mostrar”; **Resultado obtenido** = lo visto en tablero; periodo del oráculo en ambos cuando corresponda.

## CLI única

`qa-harness corrida-planilla` ejecuta KPI + filtros + visuales y:

- `recorrida` / `regresion` → `export-planilla` + `publish_plan` catálogo
- `corrida_repo` → grid + `publish_plan` corrida repo

Salida JSON en `test-evidence/` (ver ayuda del comando).
