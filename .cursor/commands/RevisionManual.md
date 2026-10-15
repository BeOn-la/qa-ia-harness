---
description: Checklist manual de lo no cubierto por /CalculoKPI, Filtro, Scope y Visuales.
---

# /RevisionManual

Arrastrar tablero en `{{args}}`; `qa-harness resolve-board --ref "{{args}}"` según `integrations/cursor/BOARD-QA.md`. No repetir ítems ya OK en la sesión.

## Plantilla (adaptar por tablero)

1. Power BI Desktop — refresh y comparación mes vs oráculos SQL.
2. KPI con NULL en Test / columnas SP pendientes (Jira en `board.yml` si existe).
3. Drill SKU / `ISINSCOPE` en medidas de detalle.
4. Target, vs PP, `PREVIOUSMONTH` (no automatizados hoy).
5. KPI fuera de matriz home (ej. price-index).
6. RLS / Service (si aplica).
7. Refresh `EXEC pbi.*` performance.
8. Regresión UX / i18n.
9. `open_questions` en fichas KPI sin cerrar.
10. Evidencia en `{board_qa_root}/test-evidence/`.

## Entregable

| ID | Área | Qué revisar | Por qué manual | Prioridad |

Bloqueantes vs seguimiento.

Argumentos: `{{args}}` = referencia al tablero + contexto de comandos ya corridos.
