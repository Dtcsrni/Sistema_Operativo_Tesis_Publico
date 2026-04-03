<!-- SISTEMA_TESIS:PROTEGIDO -->

# DEC-0020 OpenClaw como Capa Asistiva Opcional y Evaluable

- Fecha: 2026-03-27
- Estado: aceptada
- Alcance: arquitectura | seguridad | metodologia

## Contexto
Se requiere integrar OpenClaw sin convertirlo en dependencia estructural de la tesis ni del pipeline IoT base.

## Decision
Modelar OpenClaw como capa local-first opcional con conectividad hibrida, desacoplada del sistema base, con baseline obligatorio sin OpenClaw y criterios de evaluacion explicitos.

## Consecuencias
- Positivas: permite evaluar utilidad real, costo y riesgo sin comprometer la tesis si OpenClaw falla.
- Negativas: exige doble ruta operativa y comparacion controlada.

## Referencias

- [DEC-0014](../../06_dashboard/publico/NOTA_SEGURIDAD_Y_ACCESO.md)
- [DEC-0017](../../06_dashboard/publico/NOTA_SEGURIDAD_Y_ACCESO.md)

[LID]: [ruta_local_redactada]
[GOV]: [ruta_local_redactada]
[AUD]: [ruta_local_redactada]
