# Ejemplo SQL

| Archivo | Rol |
|---------|-----|
| `qa.json` | Declara controles SQL y política `read_only` / contenedor. |
| `QRD.md` / `specification.md` | Alcance del piloto SQL. |
| `baseline.sql` | Script de referencia. |
| `checks.py` | Orquesta consultas y aserciones. |
| `run_disposable.py` | Levanta contenedor temporal, corre variantes buena/mala y destruye el contenedor. |

No usa bases locales ni credenciales de staging/producción.
