# `tests/` — pruebas unitarias

Suite estándar del núcleo y de las extensiones PBI/planilla.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

| Área | Archivos (ejemplos) |
|------|---------------------|
| Contrato / runner | `test_harness.py` |
| Perfiles tablero | `test_board_profiles.py`, `test_board_resolve_ref.py` |
| KPI / filtros SQL | `test_pbi_kpi_month.py`, `test_pbi_filter_scope.py` |
| Informe PBIR | `test_report_pages.py`, `test_report_visuals.py` |
| Planilla | `test_planilla_*.py`, `test_visual_interpretation.py` |
| Fixtures | `fixtures/`, `fixture_worker.py` |

Los ejemplos end-to-end con SQL disposable están en `../examples/sql/run_disposable.py`, no en esta carpeta.
