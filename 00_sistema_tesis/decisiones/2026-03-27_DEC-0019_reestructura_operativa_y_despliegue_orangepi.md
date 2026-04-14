<!-- SISTEMA_TESIS:PROTEGIDO -->

# DEC-0019 Reestructura Operativa y Despliegue Orange Pi

- Fecha: 2026-03-27
- Estado: aceptada
- Alcance: arquitectura | operacion | despliegue

## Contexto
El repositorio ya contaba con canon, auditoria y publicacion sanitizada, pero no con una estructura operativa suficiente para instalacion real inminente sobre Orange Pi 5 Plus ni con capas separadas para manifests, bootstrap, runtime opcional y contratos de datos.

## Decision
Adoptar una reestructura operativa profunda, conservando el canon soberano en `00_sistema_tesis/` y agregando `docs/`, `manifests/`, `bootstrap/`, `runtime/`, `data_contracts/`, `benchmarks/`, `ops/`, `config/systemd/` y `config/env/` como capa operativa verificable y desplegable.

## Consecuencias
- Positivas: mejora despliegue real, validacion y separacion de responsabilidades.
- Negativas: aumenta el numero de artefactos a mantener sincronizados.
- Riesgo controlado: se conserva compatibilidad temporal con rutas existentes mientras la migracion se estabiliza.

## Referencias

- [DEC-0005](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0005_orangepi_como_base.md)
- [DEC-0014](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- [DEC-0017](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-26_DEC-0017_operacion_humana_dual_y_superficies_privada_publica.md)

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-14`._
