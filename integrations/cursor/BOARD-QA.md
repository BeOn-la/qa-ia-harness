# Contexto tablero (comandos /Calculo*)

Los comandos en `.cursor/commands/` son **genéricos**. El tablero activo se resuelve desde **qa-ia-harness** (no hardcodear cliente en el prompt).

## Cómo invocar (recomendado)

Arrastrá al chat la carpeta **`.Report`**, el **`.pbip`** o el **`.SemanticModel`** del tablero, por ejemplo:

`@beon-pbi/Softys/Softys (1).Report`

Eso va en `{{args}}` del comando. El agente **no debe asumir** el tablero: primero resuelve identidad y versión.

```powershell
qa-harness resolve-board --ref "{{args}}"
```

La salida incluye `board_id`, `version_id` (desde `{board_qa_root}/board.yml` si existe), `label`, y rutas `pbip_path` / `report_path` / `semantic_model_path`.

Alternativa legacy: primer token = `board_id` registrado en `.qa-profiles.local.json`. Si `{{args}}` está vacío → `default_board`.

## Configuración

Archivo local (no commitear): `.qa-profiles.local.json` (copiar desde `.qa-profiles.local.json.example`).

| Campo | Uso |
|-------|-----|
| `default_board` | Solo si no arrastrás ruta ni pasás `board_id` |
| `boards.<id>.board_qa_root` | Carpeta `<Cliente>/qa` del consumidor (client.yml, board.yml, sql/) |
| `boards.<id>.consumer_repo_root` | Repo del PBIP (ej. beon-pbi) |
| `boards.<id>.pbip_relative` | Ruta al `.pbip` desde consumer_repo_root |
| `boards.<id>.report_relative` | Opcional si el nombre de `.Report` no coincide con el stem del `.pbip` (cambio de versión / reporte nuevo) |
| `boards.<id>.kpi_catalog_root` | `qa/kpi-catalog.yml` + `kpi-definitions/` |
| `boards.<id>.scope_confluence_url` | Scope contractual (Confluence) |
| `profiles.*.env_file` | Credenciales SQL (staging/local) |

### Versión del tablero

Hasta definir versionado formal, la referencia operativa es **`version_id` en `{board_qa_root}/board.yml`** del consumidor. Si reemplazás o borrás un reporte anterior, actualizá `pbip_relative` / `report_relative` en el perfil local y `pbip_manifest` (y `version_id`) en `board.yml`.

## Resolver tablero en cada comando

1. Ejecutar `qa-harness resolve-board --ref "<contenido de {{args}}>"` (o equivalente con rutas del workspace).
2. Usar `board_id` y rutas del bloque `resolution` para PBIP, SQL y evidencia.
3. Metadatos: `{board_qa_root}/client.yml`, `{board_qa_root}/board.yml`.
4. SQL mensual: `{board_qa_root}/sql/_lib/params_range.sql`, runner `{board_qa_root}/sql/run_month_oracles.py`.

## Organización por hojas del informe

Los comandos `/Calculo*` entregan resultados **agrupados por hoja** (nombre visible del `.Report`). Cada hoja incluye una lista de **casos de prueba** (un registro por indicador o por filtro contractual, sin omitir filas: si no aplica en esa hoja, veredicto `no aplica`).

| Capa | Comando CLI | Una sola hoja |
|------|-------------|----------------|
| Indicadores (oráculo SQL mensual) | `qa-harness pbi-kpi-por-hoja --profile staging --ref "<ruta>"` | `--hoja "Home"` |
| Filtros (contrato + SQL) | `qa-harness pbi-filtros-por-hoja --profile staging --ref "<ruta>"` | `--hoja "Share of Search"` |
| Visuales (cada visual vs contrato / SQL) | `qa-harness pbi-visuales-por-hoja --profile staging --ref "<ruta>"` | `--hoja "Home"` |

Comandos planos (sin desglose por hoja, legado): `pbi-kpi-month`, `pbi-filter-scope`.

### Planilla Google (resumen por caso de prueba)

`qa-harness export-planilla` une KPI + filtros (+ visuales opcional) con `{board_qa_root}/manual-cases/planilla-catalog.json`.

| `--modo` | Uso |
|----------|-----|
| `recorrida` | Misma pestaña: actualiza `sheets_patch` del bloque `--revision` (iteración de lógica QA) |
| `regresion` | Nueva pestaña (`--nombre-hoja-nueva`): corrida completa; la pestaña anterior queda como evidencia |

Salida: JSON (`--output`) con **`publish_plan`** (pasos MCP ordenados). Ver `PUBLICAR-PLANILLA.md` y `/PublicarPlanilla`. No importar CSV en Drive (rompe cápsulas).

`qa-harness corrida-planilla --profile staging --ref "<ruta>" --modo recorrida|regresion` ejecuta las tres capas y escribe en `test-evidence/`.

### Interpretación de cada hoja (consumidor)

En `{board_qa_root}`:

- `scope-kpis.json` — los **10 indicadores del contrato** (Confluence) mapeados a `identificador_indicador` del catálogo.
- `page-expectations.json` — qué significa cada **nombre de hoja** del informe y qué validación de alcance aplica.

En cada ejecución de `pbi-kpi-por-hoja`, cada hoja incluye `interpretacion_hoja`, `tipo_hoja` y un primer caso de prueba **alcance contractual en la hoja** (faltantes / de más en Home, subconjuntos en módulos).

## Convención consumidor (beon-pbi u otro)

Por tablero/cliente:

```
<Cliente>/qa/
  client.yml
  board.yml          # version_id, pbip_manifest, scope
  QA-KPI-COVERAGE.md
  sql/
    run_month_oracles.py
    compare/month/all-kpis.sql
    from-dax/month/*.sql
    from-definition/month/*.sql
```

Repo compartido: `qa/kpi-catalog.yml`, `qa/kpi-definitions/*.yml`.

## Idioma y evidencia

- Respuestas al usuario: **español rioplatense**, técnico y conciso.
- No inventar métricas: ejecutar scripts o declarar bloqueo (credenciales, MCP, Desktop).
- Evidencia manual sugerida: `{board_qa_root}/test-evidence/`.
