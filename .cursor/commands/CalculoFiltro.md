---
description: Validar filtros del tablero vs scope contractual (Confluence) para el board_id configurado.
---

# /CalculoFiltro

`integrations/cursor/BOARD-QA.md`. Arrastrar tablero en `{{args}}`; `qa-harness resolve-board --ref "{{args}}"` → `pbip_path`, `report_path`, `version_id`, `board_qa_root`, `scope_confluence_url`.

## Procedimiento

1. `qa-harness resolve-board --ref "{{args}}"`
2. Scope contractual en `{board_qa_root}/scope-filters.json` (sincronizado con Confluence).
3. Ejecutar por hojas:

```powershell
qa-harness pbi-filtros-por-hoja --profile staging --ref "{{args}}"
qa-harness pbi-filtros-por-hoja --profile staging --ref "{{args}}" --hoja "Home"
```

## Entregable

Por cada **hoja**: casos de prueba de cada filtro del contrato (`scope-filters.json`) con veredicto `correcto`, `fallido` o `no aplica`, más valores que devuelve el modelo vía SQL. Texto al usuario en español claro, sin abreviaturas.

Legado (sin hojas): `qa-harness pbi-filter-scope`.

Argumentos: `{{args}}` = referencia arrastrada al tablero (o `board_id` legacy).
