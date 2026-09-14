# Entrega y validación

## Entregado en esta versión

- Contrato v1, CLI `check`, `run`, `report` y `gate`.
- Trazabilidad de commit, especificaciones, QRD, manifiesto, baseline SQL y evidencia.
- Estados separados para fallo, error, bloqueo, omisión e inestabilidad.
- Consumidor API/lógica y SQL sintéticos; el último tiene seed, preflight, limpieza y una falla conocida reproducible.
- Pruebas adversas y workflow de validación limpia.

## Próximas etapas

1. Admitir un piloto API/lógica y uno SQL con `templates/pilot-admission.md`.
2. Integrar los comandos existentes de cada consumidor y revisar sus tests generados.
3. Ejecutar localmente sobre commits definitivos y comparar el valor con la suite actual.
4. Habilitar el workflow informativo en cada piloto.
5. Resolver acceso, aislamiento y conectividad de staging antes de pruebas allí.
6. Proponer gates obligatorios solo para controles estables y acordados.

La versión no selecciona pilotos, modifica productos ni se conecta a entornos existentes.
