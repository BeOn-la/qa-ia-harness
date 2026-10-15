---
description: Corrida automática (KPI+filtros+visuales), export a planilla y publicación en Google Sheets con formato plantilla.
---

# /PublicarPlanilla

Leer `integrations/cursor/BOARD-QA.md` y **`integrations/cursor/PUBLICAR-PLANILLA.md`**.

**Tablero:** arrastrar `.Report` / `.pbip` en `{{args}}`.

## 0. Catálogo alineado a la planilla (primera vez o si cambió el Excel)

Leer con MCP `read_range` la pestaña plantilla (`Revision 14/10/26`, celdas **A3:F** hasta la última fila con casos) y regenerar:

```powershell
# CSV en stdin desde export MCP o archivo _sheet_export.csv
Get-Content _sheet_export.csv -Raw | .\.venv\Scripts\python.exe tools\ingest_sheet_csv_to_catalog.py -o ..\beon-pbi\Softys\qa\manual-cases\planilla-catalog.json `
  --spreadsheet-id 1IiB3WAUIJQJNzJSmC6oLI2aZiGJYGW_qOqj1P8Bbo-Y --sheet-title "Revision 14/10/26" --template-sheet-id 0
```

## 1. Resolver tablero y rutas

```powershell
qa-harness resolve-board --ref "{{args}}"
```

`board_qa_root` → catálogo `{board_qa_root}/manual-cases/planilla-catalog.json` y `board.yml` → `planilla_qa.spreadsheet_id`.

## 2. Corrida automática (guardar evidencia)

```powershell
$ev = "<board_qa_root>/test-evidence"
qa-harness pbi-kpi-por-hoja --profile staging --ref "{{args}}" | Out-File -Encoding utf8 "$ev/kpi-por-hoja.json"
qa-harness pbi-filtros-por-hoja --profile staging --ref "{{args}}" | Out-File -Encoding utf8 "$ev/filtros-por-hoja.json"
qa-harness pbi-visuales-por-hoja --profile staging --ref "{{args}}" | Out-File -Encoding utf8 "$ev/visuales-por-hoja.json"
```

## 3. Export + plan de publicación Drive

**Recorrida** (misma pestaña, pisa Revision N):

```powershell
qa-harness export-planilla --catalog <catalog> --kpi $ev/kpi-por-hoja.json --filtros $ev/filtros-por-hoja.json --visuales $ev/visuales-por-hoja.json `
  --modo recorrida --revision 1 --hoja-planilla "Revision 14/10/26" `
  --output $ev/export-planilla.json
```

**Regresión** (nueva pestaña en el mismo documento):

```powershell
qa-harness export-planilla ... --modo regresion --nombre-hoja-nueva "Revision DD/MM/YY" `
  --entrada-previa $ev/export-planilla.json --output $ev/export-planilla-regresion.json
```

El JSON incluye `publish_plan.pasos` para Google Sheets MCP.

## 4. Publicar en Google (obligatorio)

Autenticar MCP `plugin-google-sheets-google-sheets` si hace falta.

Si el título de la pestaña tiene `/` (ej. `Revision 14/10/26`), **renombrar** antes de `write_range` (ej. `Revision 14-10-26`); ver `PUBLICAR-PLANILLA.md`.

Ejecutar **en orden** cada paso de `publish_plan.pasos`:

| Modo | Acción clave |
|------|----------------|
| `regresion` | `copy_sheet_to_another_spreadsheet` (mismo `spreadsheetId` origen y destino) → `rename_sheet_tab` → `batch_clear_values` en columnas de revisión → `write_range` por lotes |
| `recorrida` | Solo `write_range` en filas automatizadas (no tocar A:F) |

**No** importar CSV sobre la plantilla: pierde cápsulas y formato.

Confirmar URL del spreadsheet en `board.yml` → `planilla_qa.url`.

## Entregable al usuario

- Resumen `resumen` del export (aprobados / error / sin revisar).
- En **Error**: Tipo de error, Prioridad, Controlado por y Obs. QA (ver `PUBLICAR-PLANILLA.md`).
- Link a la pestaña publicada.
- Lista breve de `extras_sin_fila_catalogo` si hay fallos sin fila en catálogo.

Argumentos: `{{args}}` = referencia al tablero. En el mensaje: `modo=recorrida|regresion`, `revision=1`, `hoja=…` si aplica.
