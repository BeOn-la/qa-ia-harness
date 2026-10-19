# Ejemplo API

| Archivo | Rol |
|---------|-----|
| `qa.json` | Manifiesto de controles y perfiles. |
| `QRD.md` | Plan de QA del ejemplo. |
| `spec.md` | Especificación funcional mínima. |
| `app.py` | Aplicación bajo prueba. |
| `checks.py` | Controles invocados por `qa-harness run`. |

```powershell
qa-harness check --repo examples/api --profile local
qa-harness run --repo examples/api --profile local --output .qa-runs/demo
```
