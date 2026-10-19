---
description: Oráculos SQL mensuales (from-dax vs from-definition) y resumen de compare por tablero configurado.
---

# /CalculoKPI

Leer `integrations/cursor/BOARD-QA.md`. **Tablero:** arrastrar `.Report` / `.pbip` / `.SemanticModel` en `{{args}}` (ej. `@beon-pbi/Softys/Softys.Report`).

## Resolver tablero (obligatorio)

```powershell
qa-harness resolve-board --ref "{{args}}"
```

Usar `board_id`, `version_id` y rutas del JSON en el resto del comando.

## Ejecutar (por hojas del informe)

```powershell
qa-harness pbi-kpi-por-hoja --profile staging --ref "{{args}}"
# solo una hoja:
qa-harness pbi-kpi-por-hoja --profile staging --ref "{{args}}" --hoja "Home"
```

## Entregable

Por cada **hoja**: todos los indicadores del catálogo como **casos de prueba** con veredicto `correcto`, `fallido` o `no aplica` (si el indicador no se muestra en esa hoja). Incluir valores del oráculo cuando aplica. Responder en español claro, sin abreviaturas en el texto al usuario.

Oráculo plano (legado): `qa-harness pbi-kpi-month --profile staging --ref "{{args}}"`.

Argumentos: `{{args}}` = referencia arrastrada al artefacto PBIP del tablero. Opcional en el mismo mensaje: `perfil=staging`, `selector=All`. Legacy: solo `board_id` si no hay ruta.
