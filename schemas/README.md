# `schemas/` — contratos JSON v1

Schemas usados por `contract.py` y por la documentación en `docs/contract.md`.

| Archivo | Describe |
|---------|----------|
| `manifest.json` | Estructura de `qa.json` (manifiesto del consumidor). |
| `results.json` | Resultado de un control individual. |
| `decisions.json` | Resolución de controles manuales junto al reporte. |
| `planilla_revision_capsules.json` | Metadatos de cápsulas para revisión automática en planilla. |

El reporte agregado (`report.json`) se documenta en `docs/contract.md`; validar cambios de schema con `tests/test_harness.py` y consumidores de ejemplo.
