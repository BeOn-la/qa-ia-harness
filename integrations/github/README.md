# Integración GitHub Actions

| Archivo | Uso |
|---------|-----|
| `consumer-workflow.yml.example` | Plantilla para copiar al repo consumidor (modo informativo al inicio). |

Flujo típico: checkout → `pip install qa-ia-harness` o submodule → `qa-harness run` → subir artefacto `.qa-runs/` → `gate` en el commit mergeable.

Detalle: [../../docs/github-actions.md](../../docs/github-actions.md).
