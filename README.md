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

## Documentación

- [Contrato y CLI](docs/contract.md)
- [Método de QA y QRD](docs/methodology.md)
- [Operación SQL](docs/sql.md)
- [Límites de confianza](docs/security.md)
- [Integración con Cursor](integrations/cursor/README.md)
- [Plan de entrega y validación](docs/implementation-plan.md)
# SQL access security

Real SQL integrations must declare `read_only` or `isolated_write`; the latter
requires `--allow-isolated-write` and a database principal limited to fixture
data. Read [SQL security policy](docs/sql-security.md) before using local or
staging credentials.
