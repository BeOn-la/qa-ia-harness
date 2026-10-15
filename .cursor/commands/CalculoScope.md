---
description: KPI y módulos contratados en scope vs catálogo, reporte y harness SQL.
---

# /CalculoScope

Seguir `integrations/cursor/BOARD-QA.md`. Arrastrar tablero en `{{args}}` y ejecutar `qa-harness resolve-board --ref "{{args}}"` antes de analizar.

## Fuentes

- `{board_qa_root}/scope-kpis.json` (10 indicadores contrato)
- `{board_qa_root}/page-expectations.json` (rol de cada hoja)
- Confluence (`scope_confluence_url`) para contrastar texto
- Catálogo `{kpi_catalog_root}/kpi-catalog.yml`

## Ejecutar (por hoja)

```powershell
qa-harness pbi-kpi-por-hoja --profile staging --ref "{{args}}"
```

El **primer caso de prueba** de cada hoja es *alcance contractual en la hoja* (faltantes / de más según el tipo de hoja). Home usa validación estricta.

## Entregable

Por hoja: interpretación en español, veredicto de alcance, luego cada indicador del catálogo. Sin omitir filas (`no aplica` cuando corresponda).

Argumentos: `{{args}}` = `.Report` / `.pbip` / `.SemanticModel` del tablero (o `board_id` legacy).
