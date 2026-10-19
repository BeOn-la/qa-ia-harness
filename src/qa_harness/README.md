# Paquete `qa_harness`

## Núcleo genérico (cualquier repo con `qa.json`)

| Módulo | Función |
|--------|---------|
| `cli.py` | Subcomandos `qa-harness`. |
| `contract.py` | Validación de manifiesto y reglas del contrato v1. |
| `runner.py` | `check` y `run` sobre controles declarados. |
| `gate.py` | `gate`: checkout limpio + controles requeridos + manuales. |
| `reporting.py` | `report.json` / Markdown desde resultados. |
| `process.py` | Ejecución de procesos (argv, timeouts, fases). |
| `parsers.py` | Parseo JSON/JUnit de salida de controles. |
| `provenance.py` | Commit, dirty state, hashes de archivos. |
| `common.py` | Códigos de salida y errores de contrato. |
| `sqlserver.py` | Ejecución SQL acotada al contrato. |
| `sql_profiles.py` | Carga de `.qa-profiles.local.json` y rutas al framework SQL. |

## Extensiones Power BI / planilla (consumidor beon-pbi)

| Módulo | Función |
|--------|---------|
| `board_profiles.py` | `resolve-board`: ref arrastrada → `board_id`, rutas QA. |
| `kpi_catalog.py` | Lee `qa/kpi-catalog.yml` del consumidor. |
| `pbi_kpi_month.py` | Oráculos mensuales from-dax vs from-definition. |
| `pbi_filter_scope.py` | Filtros del reporte vs `scope-filters.json`. |
| `pbi_por_hoja.py` | KPI / filtros / visuales agregados por hoja del informe. |
| `report_pages.py` | Páginas del `.Report` (PBIR JSON). |
| `report_filters.py` | Filtros a nivel página/visual. |
| `report_visuals.py` | Metadatos de visuales del informe. |
| `page_expectations.py` | Expectativas por hoja (`page-expectations.json`). |
| `visual_interpretation.py` | Interpretación de visuales vs contrato. |
| `planilla_qa.py` | Catálogo planilla, export recorrida/regresión. |
| `planilla_bindings.py` | Enlace filas planilla ↔ resultados de corrida. |
| `planilla_visual_match.py` | Matching visual planilla ↔ PBIR. |
| `planilla_publish.py` | Plan de publicación a Google Sheets. |
| `corrida_planilla.py` | Orquestación KPI + filtros + visuales + export. |

## Comandos CLI relevantes

| Comando | Módulo principal |
|---------|------------------|
| `check`, `run`, `gate`, `report` | `runner`, `gate`, `reporting` |
| `resolve-board` | `board_profiles` |
| `pbi-kpi-month` | `pbi_kpi_month` |
| `pbi-filter-scope` | `pbi_filter_scope` |
| `pbi-kpi-por-hoja`, `pbi-filtros-por-hoja`, `pbi-visuales-por-hoja` | `pbi_por_hoja` |
| `export-planilla`, `corrida-planilla`, `planilla-cobertura` | `planilla_qa`, `corrida_planilla` |
