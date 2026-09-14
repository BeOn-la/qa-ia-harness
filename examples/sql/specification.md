# Contrato SQL sintetico — v1

## RF-001
Una fila representa URL pendiente si Url IS NULL o LTRIM(RTRIM(Url)) = '-'.
La cadena vacia y una URL con contenido no representan pendientes.
Este es un ejemplo aislado inspirado en la referencia inspeccionada, no una aprobacion
de reglas vigentes de un producto BeOn.

## RF-002
Los cinco registros de baseline.sql deben existir al comenzar la validacion.
El resultado esperado por IDs es [1, 2, 3]. Los IDs 4 y 5 deben quedar fuera.
La tabla de la ejecucion debe eliminarse y su ausencia debe verificarse al terminar.

Aprobacion exclusiva del fixture: fixture-maintainer, 2026-09-11.
