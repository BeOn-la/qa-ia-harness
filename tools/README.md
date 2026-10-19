# `tools/` — scripts de operación

No forman parte del paquete Python instalado; se invocan desde PowerShell o Python en la raíz del repo.

## SQL y perfiles

| Script | Uso |
|--------|-----|
| `Init-SqlProfilesFromSqlFramework.ps1` | Copia `.env.*` de **qa-sql-testing-framework** a `config/sql/` y genera `.qa-profiles.local.json`. |
| `Invoke-QAProfile.ps1` | Carga un perfil y ejecuta `qa-harness` con variables de entorno SQL. |
| `Invoke-PbiKpiMonthOracles.ps1` | Atajo a `qa-harness pbi-kpi-month` con perfil local. |

## Planilla Google Sheets

| Script | Uso |
|--------|-----|
| `import_planilla_catalog.py` | Importar catálogo de casos desde fuentes externas. |
| `ingest_sheet_csv_to_catalog.py` | CSV (columnas A–F) → `planilla-catalog.json`. |
| `ingest_mcp_read_range_json.py` | Salida MCP `read_range` → catálogo. |
| `pull_planilla_catalog_from_sheets.py` | Bajar rango de la planilla vía API/ADC. |
| `merge_mcp_catalog.py` | Fusionar actualizaciones parciales del catálogo. |
| `gen_planilla_harness_bindings.py` | Generar `planilla-harness-bindings.json` en el consumidor. |
| `publish_export_batches.py` | Trocear `publish_plan` para subida por lotes. |

Scripts de corrida en el consumidor (ej. Softys) pueden vivir en `<Cliente>/qa/tools/`; ver **beon-pbi**.
