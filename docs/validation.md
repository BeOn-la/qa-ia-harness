# Validación registrada

La primera validación local del núcleo ejecutó 31 pruebas adversas en consumidores Git temporales. Cubrió resultados malformados, ausencia de reporte, suites vacías, fallo posterior, timeout, salida interactiva, cambios de alcance, evidencia alterada, secreto en log, preguntas abiertas, controles no seleccionados, reintentos y contaminación SQL simulada.

También se ejecutaron las variantes correcta y defectuosa de los consumidores API y SQL. En ambos casos la variante correcta devolvió 0 y la defectuosa devolvió 1. El SQL corrió dentro de un contenedor Docker temporal, con cinco filas sintéticas y limpieza verificada. Estas ejecuciones quedaron marcadas exploratorias porque los consumidores sintéticos aún no estaban comprometidos como checkouts definitivos, por diseño.

No se afirma ejecución remota en GitHub Actions ni validación sobre un producto BeOn hasta que existan pilotos seleccionados y evidencia correspondiente.
