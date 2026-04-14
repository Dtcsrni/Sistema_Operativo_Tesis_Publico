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

- [DEC-0014](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- [DEC-0017](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-26_DEC-0017_operacion_humana_dual_y_superficies_privada_publica.md)

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-13`._
