---
description: Visuales del informe por hoja vs contrato, filtros SQL y oráculo de indicadores.
---

# /CalculoVisuales

`integrations/cursor/BOARD-QA.md`. Arrastrar tablero en `{{args}}`; `qa-harness resolve-board --ref "{{args}}"`.

## Ejecutar

```powershell
qa-harness pbi-visuales-por-hoja --profile staging --ref "{{args}}"
qa-harness pbi-visuales-por-hoja --profile staging --ref "{{args}}" --hoja "Home"
```

## Qué hace

Por cada **hoja**, lista **todas** las visuales del `.Report` como casos de prueba:

| Tipo | Veredicto |
|------|-----------|
| Formas, botones, diseño | `no aplica` |
| Slicer de filtro contractual | `correcto` / `fallido` (mismos valores SQL que `/CalculoFiltro`) |
| Tarjeta / gráfico con indicador del contrato | `correcto` / `fallido` (oráculo mensual SQL) |
| Indicador fuera del contrato en Home | `fallido` |
| Medidas de apoyo (vs Target, filtros aplicados, etc.) | `no aplica` |

Cada hoja incluye `interpretacion_hoja` desde `page-expectations.json`.

## Entregable al usuario

Por hoja: nombre, interpretación, cantidad de visuales, tabla de casos con `nombre_caso`, `veredicto`, `detalle` en español claro (sin abreviaturas).

Argumentos: `{{args}}` = `.Report` / `.pbip`; opcional `--hoja` o nombre en el mensaje.
