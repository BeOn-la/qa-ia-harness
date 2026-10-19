# qa-ia-harness

QA reproducible para un QA dedicado: declara el alcance, ejecuta controles no interactivos y conserva evidencia vinculada al checkout evaluado.

El núcleo no conoce reglas de negocio ni requiere IA durante la ejecución. Cursor puede ayudar a analizar y proponer regresiones, pero los tests, seeds, QRD y decisiones quedan en cada repositorio consumidor.

## Estado

La versión `0.1.0` incluye una CLI Python, contratos JSON v1, ejemplos sintéticos de API/lógica y SQL Server, pruebas adversas y un workflow de GitHub Actions. No adopta dependencias de `sdd-ia-harness` ni `qa-sql-testing-framework`.

Los pilotos reales quedan pendientes de seleccionar explícitamente; no se presume acceso a productos, bases o GitHub remoto.

## Instalación y primer uso

Requiere Python 3.12+ y Git. Desde este repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\qa-harness.exe check --repo examples/api --profile local
.\.venv\Scripts\qa-harness.exe run --repo examples/api --profile local --output .qa-runs/first
.\.venv\Scripts\qa-harness.exe gate --repo examples/api --input examples/api/.qa-runs/first/report.json
```

Las ejecuciones locales sobre un checkout sin commit o modificado son exploratorias: pueden aprobar los controles ejecutados, pero `gate` queda incompleto. Repetir en el commit definitivo para evidencia utilizable.

| Código de `run` | Significado |
|---|---|
| 0 | Todos los controles automáticos seleccionados aprobaron. |
| 1 | Falló una validación. |
| 2 | Error de configuración, infraestructura, reporte o cambio durante la ejecución. |
| 3 | Bloqueado, vacío, omitido, cancelado, incompleto o inestable. |

Un 0 de `run` no aprueba el producto: `gate` también comprueba identidad, controles requeridos, definiciones y evidencia manual.

## Verificación incluida

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe examples/verify.py api
.\.venv\Scripts\python.exe examples/sql/run_disposable.py
```

El ejemplo SQL crea exclusivamente un contenedor SQL Server temporal y aislado, con contraseña aleatoria, cinco filas sintéticas y sin puertos publicados. Prueba una variante correcta y otra defectuosa, verifica la limpieza y elimina solo su propio contenedor. No utiliza bases locales, staging ni producción.

## Adoptar en un producto

1. Completar [la admisión del piloto](templates/pilot-admission.md).
2. Crear un [QRD](templates/QRD.md) y `qa.json` a partir de [la plantilla](templates/manifest.template.json).
3. Declarar comandos existentes y revisados; no se descubren ni ejecutan comandos desde documentación del consumidor.
4. Revisar escenarios, esperados, tests y fixtures con los referentes correspondientes.
5. Ejecutar, revisar los reportes y repetir sobre el commit final.
6. Incorporar el workflow de [GitHub Actions](integrations/github/consumer-workflow.yml.example) inicialmente como informativo.

## Conexión SQL (qa-sql-testing-framework)

El núcleo **no** carga `.env` por diseño. Para reutilizar los perfiles de `qa-sql-testing-framework` (local, test, prod):

```powershell
.\tools\Init-SqlProfilesFromSqlFramework.ps1
# Opcional: -SqlFrameworkRoot "C:\ruta\qa-sql-testing-framework" -Force

.\tools\Invoke-QAProfile.ps1 -Profile staging qa-harness run --repo <consumidor> --profile <nombre-en-qa.json>
```

Eso copia `.env.local`, `.env.test` y `.env.prod` a `config/sql/` (ignorado por Git) y crea `.qa-profiles.local.json`. Un `qa.json` del repo consumidor puede fijar otro servidor/base en `sql_target`; el harness valida que coincida con el entorno cargado.

En `qa-sql-testing-framework`, `pbi-qa` y `tools/mssql_common.py` pueden usar el mismo perfil con `MSSQL_ENV_FILE` o `QA_DB_PROFILE` (ver README de ese repo).

### KPI tablero Softys (oráculos mensuales)

Compara **from-dax** vs **from-definition** para octubre (rango en `beon-pbi/Softys/qa/sql/_lib/params_range.sql`), usando el runner SQL del consumidor y credenciales del perfil local.

1. Copiar `.qa-profiles.local.json.example` → `.qa-profiles.local.json` y ajustar `pbi_qa.board_qa_root` / `framework_root`.
2. Sincronizar perfiles SQL: `.\tools\Init-SqlProfilesFromSqlFramework.ps1`
3. Ejecutar:

```powershell
.\tools\Invoke-PbiKpiMonthOracles.ps1 -Profile staging
# o
.\.venv\Scripts\qa-harness.exe pbi-kpi-month --profile staging
```

Salida JSON en stdout; exit **0** si todos los `compare_status` son `pass`. Opcional: `--kpi title-compliance`.

Comandos Cursor (**multi-tablero**): `/CalculoKPI`, `/CalculoFiltro`, `/CalculoScope`, `/CalculoVisuales`, `/RevisionManual` en `.cursor/commands/`. Arrastrar `.Report` / `.pbip` al invocar; resolver con `qa-harness resolve-board --ref "<ruta>"`. Perfiles en `.qa-profiles.local.json` → `boards`. Ver `integrations/cursor/BOARD-QA.md`.

## Mapa del repositorio

| Carpeta | README |
|---------|--------|
| `src/` | [src/README.md](src/README.md) — paquete `qa_harness` |
| `docs/` | [docs/README.md](docs/README.md) — contrato, método, **arquitectura (diagramas)** |
| `tools/` | [tools/README.md](tools/README.md) — perfiles SQL y planilla |
| `tests/` | [tests/README.md](tests/README.md) |
| `schemas/` | [schemas/README.md](schemas/README.md) |
| `examples/` | [examples/README.md](examples/README.md) |
| `integrations/` | [integrations/README.md](integrations/README.md) |
| `templates/` | [templates/README.md](templates/README.md) |
| `config/` | [config/README.md](config/README.md) |
| `.cursor/` | [.cursor/README.md](.cursor/README.md) — comandos `/Calculo*` |

## Documentación

- [Arquitectura y flujos (Mermaid)](docs/architecture.md)
- [Contrato y CLI](docs/contract.md)
- [Método de QA y QRD](docs/methodology.md)
- [Operación SQL](docs/sql.md)
- [Política SQL](docs/sql-security.md)
- [Límites de confianza](docs/security.md)
- [Integración con Cursor](integrations/cursor/README.md)
- [Plan de entrega y validación](docs/implementation-plan.md)
