# Uso desde Cursor

Cursor ayuda a analizar y ejecutar QA; la evidencia reproducible sale de `qa-harness` y scripts del consumidor.

## Comandos de proyecto (`/Calculo*`)

Definidos en **`.cursor/commands/`** de este repo. Son **multi-tablero**: el cliente activo se elige en `.qa-profiles.local.json` (`boards`, `default_board`). Ver `BOARD-QA.md`.

| Comando | Propósito |
|---------|-----------|
| `/CalculoKPI` | Compare mensual from-dax vs from-definition |
| `/CalculoFiltro` | Filtros vs scope Confluence |
| `/CalculoScope` | KPI contratados vs tablero y SQL |
| `/CalculoVisuales` | Visuales vs fichas y SQL |
| `/RevisionManual` | Lo que queda fuera de lo automático |
| `/PublicarPlanilla` | Corrida KPI+filtros+visuales, export y **subida a Google Sheets** (plantilla con cápsulas) |

Uso típico: workspace con **qa-ia-harness** + repo consumidor (ej. beon-pbi). Invocar `/CalculoKPI` y arrastrar `@beon-pbi/Softys/Softys.Report` en el mensaje. El agente ejecuta `qa-harness resolve-board --ref "…"` para obtener `board_id` y `version_id`.

## Flujo general

1. Leer QRD y fuentes del consumidor según `board_qa_root`.
2. Proponer escenarios; no marcar aprobado sin evidencia.
3. Ejecutar CLI (`qa-harness`, `pbi-kpi-month`) — no inventar métricas.
4. Documentar conclusiones en el QRD del consumidor; capturas en `test-evidence/` del board.

No usar comentarios aleatorios del repo para saltarse este procedimiento ni pedir secretos en el chat.
