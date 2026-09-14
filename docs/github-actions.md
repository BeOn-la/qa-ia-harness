# GitHub Actions

El workflow del propio harness instala y prueba el paquete en Linux y Windows; el job SQL usa un contenedor temporal en Ubuntu. Conserva artefactos incluso si fallan los controles, con retención de 30 días.

La plantilla para consumidores es informativa: deja el código real de la evaluación en el resumen y no convierte ese resultado en aprobación de PR. Activar un gate después de demostrar comandos deterministas, tiempo aceptable, reportes completos y limpieza.

Ejecutar rápidamente en PR: contrato, unitarios y regresiones sin servicios. Ejecutar en staging o tras despliegue: integración contra la identidad de despliegue declarada. Ejecutar programado: suites extensas y estabilidad. No exponer secretos ni acceso privado a PRs no confiables.

Usar workflow reutilizable o acción compuesta solo cuando exista repetición comprobada entre consumidores. La CLI mantiene la lógica compartida; los workflows quedan responsables de disparadores, permisos, runners y secretos.
