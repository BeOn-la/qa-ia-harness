# Método de QA y QRD

El QRD es un plan de evaluación, no un reporte de ejecución. Reutiliza identificadores y referencias de especificaciones; no duplica requisitos ni convierte tests generados en evidencia.

Un cambio pequeño necesita objetivo, alcance, referencias, escenarios, controles y pendientes. Una funcionalidad añade riesgos, datos, entornos, trazabilidad y manuales. Una validación amplia puede añadir coordinación y cronograma si existe una necesidad real.

El template Word revisado aporta objetivo, referencias, supuestos, riesgos y métricas. Se simplifican recursos, cronograma y herramientas; Gantt, PERT, PEAQ y métricas de proceso se dejan opcionales. La evidencia ejecutada se conserva separada en `report.json`/`report.md`.

Para cada ambigüedad registrar fuente, pregunta, escenarios afectados, propuesta, estado y decisión humana. La IA puede proponer casos positivos, negativos, límites e invariantes, pero no aprueba reglas de negocio. Continuar con controles independientes y marcar los demás como bloqueados.

Separar siempre ejecución, severidad, certeza, fundamento y resolución. Una prueba no ejecutada, una suite vacía o una derivación no pueden figurar como aprobadas.
