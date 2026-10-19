# `examples/` — consumidores sintéticos

Demuestran cómo un repo producto declara `qa.json`, QRD y controles sin depender de Power BI.

| Carpeta | Qué prueba |
|---------|------------|
| [api/](api/) | App Python mínima + checks en proceso. |
| [sql/](sql/) | Controles SQL contra contenedor SQL Server **aislado** (`run_disposable.py`). |

Verificación rápida:

```powershell
.\.venv\Scripts\python.exe examples/verify.py api
.\.venv\Scripts\python.exe examples/sql/run_disposable.py
```

Para tableros reales usar **beon-pbi** + comandos `pbi-*` del harness, no estos ejemplos.
