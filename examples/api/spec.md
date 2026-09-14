# Contrato ficticio de cotizacion — v1

Este documento aprueba exclusivamente el comportamiento del consumidor sintetico.
No contiene reglas de un producto BeOn.

## RF-001
Recibir cantidad entera entre 1 y 10000 y precio entero no negativo expresado en centavos.
Booleanos no son cantidades. Entradas invalidas devuelven 400 con el error especifico.

## RF-002
Devolver 200 y total_cents = cantidad * precio.
Ejemplo independiente: 3 unidades a 125 centavos devuelven 375.
Las respuestas invalid_quantity, invalid_type y out_of_range estan descritas por checks.py
y deben revisarse junto con este contrato ficticio.

Aprobacion de fixture: fixture-maintainer, 2026-09-11.
