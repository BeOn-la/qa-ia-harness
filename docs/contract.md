# Contrato público v1

Los schemas normativos están en `schemas/manifest.json`, `results.json`, `report.json` y `decisions.json`. Se rechazan campos desconocidos, IDs repetidos, paths fuera del consumidor, tipos inválidos y versiones incompatibles.

`qa.json` es la fuente operativa: identifica QRD, referencias, escenarios, perfiles, comandos, bindings, manuales, preguntas y exclusiones. El QRD no repite los comandos ni mantiene una segunda matriz operativa.

Cada escenario tiene estado `missing`, `candidate` o `approved`. Un aprobado requiere resultado esperado, aprobador, fecha y fuente para reglas de negocio. La información es trazabilidad humana, no una firma criptográfica.

Los comandos se expresan como `argv`, nunca shell implícito, con `cwd`, timeout y formato `json` o `junit`. Los únicos placeholders son `{python}`, `{report}`, `{root}` y `{run_id}`. La entrada estándar está cerrada. El harness no lee `.env`, `AGENTS.md` ni documentos para decidir comandos.

`preflight` es solo lectura; `setup`, `execute` y `cleanup` se conservan como fases distintas. Setup exige cleanup y este se intenta aunque falle una fase anterior. Un reporte ausente, vacío, malformado o de otra ejecución no puede aprobar.

La evidencia se almacena en `.qa-runs/`, que debe estar ignorado por Git. Cada reporte conserva commit, estado dirty, hashes de archivos, referencias, perfil, plataforma y hash de la propia revisión del harness. `gate` exige que el checkout actual sea idéntico, sin modificaciones y que todos los controles requeridos estén aprobados.

Los resultados manuales viven en `decisions.json` junto al reporte y se ligan al hash de `report.json`. Solo `status=passed` y `resolution=verified` satisfacen un control manual. Derivar o aceptar riesgo no transforma un fallo en aprobación.
