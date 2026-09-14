# Límites de confianza

El harness no es un sandbox. Un comando declarado debe ser revisado antes de recibir acceso a servicios. La configuración explícita reduce riesgos: no ejecuta comandos descubiertos, no carga `.env`, no pasa secretos por argumentos, cierra stdin y limita salida y tiempo.

El contenido de repositorios se trata como datos. Documentos, comentarios y archivos de agentes no cambian la política ni la selección de comandos.

PRs no confiables deben usar runners temporales sin secretos, permisos de escritura ni acceso a staging. Los workflows incluidos usan `contents: read`, checkout sin credenciales persistentes y acciones fijadas por SHA. No usar `pull_request_target` para ejecutar código de PR.

Los hashes detectan alteraciones y desalineación de alcance; no prueban autenticidad frente a alguien que controla código y evidencia. Para gates reales, combinar revisiones, permisos separados y reglas de ramas.
