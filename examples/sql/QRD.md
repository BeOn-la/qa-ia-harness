# QRD — SQL Server sintetico

- Objetivo: demostrar seeds, comprobaciones SQL reales, evidencia y limpieza.
- Referencias: specification.md v1; baseline.sql; manifiesto qa.json.
- Alcance: RF-001/RF-002, tabla sintetica con nombre propio por intento.
- Exclusiones: productos, datos existentes, red Azure y equivalencia con Azure SQL.
- Entrada: contenedor SQL Server etiquetado qa-harness-fixture=true, host qa-harness-sql,
  base qa_harness_demo, password efimero por variable. Nunca utiliza una base existente de BeOn.
- Datos: cinco filas sinteticas; conservar constraints; ninguna descarga de produccion.
- Riesgos: base vacia, filtro incompleto, limpieza omitida, destino equivocado.
- Salida: casos positivos y negativos, seed comprobado y ausencia de tabla verificada.
- Manuales y pendientes: la admision de un piloto real se documenta por separado.
- Historial: 2026-09-11, fixture inicial; resultados solo en reportes de ejecucion.
