# Operación SQL

El núcleo no incorpora un driver SQL. El consumidor conserva scripts, seeds y adaptadores. El perfil SQL declara variables de servidor/base, destinos permitidos, identidad esperada, baseline y migraciones.

El preflight debe obtener identidad real desde el servidor y producir `server`, `database`, `engine_version` y `baseline_sha256`. Antes de setup, el harness compara esa evidencia contra la configuración. No basta con repetir valores de variables de entorno.

Usar DDL y seeds sintéticos versionados, preservar constraints y verificar que el seed produjo los escenarios. Preferir una base por ejecución. En una base compartida, usar identificadores propios, limpieza precisa y exclusión mutua si el esquema no permite aislar.

No ejecutar tests, seeds o limpieza en producción. Si cleanup falla, el lock de destino queda marcado como contaminado y la próxima ejecución se bloquea. Revisar la evidencia, limpiar el espacio afectado y registrar la resolución antes de retirar explícitamente el lock.

El ejemplo incluido usa SQL Server Developer en Docker, sin puertos publicados y con una red aislada. Ese TLS/configuración es exclusiva del fixture y no debe copiarse a Azure.
