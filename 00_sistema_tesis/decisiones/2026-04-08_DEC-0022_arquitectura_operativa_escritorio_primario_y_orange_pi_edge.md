<!-- SISTEMA_TESIS:PROTEGIDO -->

# DEC-0022 Arquitectura Operativa Escritorio Primario y Orange Pi Edge

- Fecha: 2026-04-08
- Estado: aceptada
- Alcance: arquitectura | operacion | despliegue

## Contexto
La separacion por dominios en Orange Pi y la reestructura operativa ya existen, pero hacia falta fijar con mas precision donde vive el trabajo principal de tesis y cual es el papel exacto del nodo edge para evitar ambiguedades futuras.

## Decision
Adoptar una arquitectura operativa **desktop-first** con dos nodos complementarios:

1. **`desktop_workspace`:** PC de escritorio con Visual Studio Code como estacion principal de autoria, diseno, analisis, construccion documental y mantenimiento del repositorio soberano.
2. **`orange_pi_edge`:** Orange Pi como nodo edge operativo para `edge_iot` y para capacidades locales que convenga ejecutar ahi por hardware, proximidad fisica o control del stack IoT.

La integracion oficial entre ambos nodos se fija por **sincronizacion Git y artefactos/contratos explicitos**, incluyendo `git_sync`, `artefactos_generados`, `contratos_de_datos` y `logs_o_evidencia_edge`.

Como flujo normal quedan prohibidos:

- la autoria principal de tesis en Orange Pi;
- la edicion arquitectonica primaria en Orange Pi;
- la dependencia de un workspace compartido montado por red como via principal de trabajo.

La Orange Pi si puede ejecutar operacion tecnica extendida del stack IoT, diagnostico, pruebas locales y hotfixes operativos del dominio edge cuando queden trazados, pero no sustituye al escritorio como superficie principal de tesis.

## Consecuencias
- Positivas: aclara responsabilidades por nodo, reduce deriva operativa y preserva la Orange Pi para lo que mejor resuelve en campo.
- Negativas: exige documentar mejor la sincronizacion y evitar que el clon operativo de Orange Pi se trate como repo principal.
- Riesgo controlado: se conserva el layout actual de `/srv/tesis/repo` y `/srv/tesis/workspace/edge`, pero redefinidos como clon operativo y workspace de ejecucion local.

## Referencias

- [DEC-0017](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-26_DEC-0017_operacion_humana_dual_y_superficies_privada_publica.md)
- [DEC-0019](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-27_DEC-0019_reestructura_operativa_y_despliegue_orangepi.md)
- [DEC-0020](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-27_DEC-0020_openclaw_como_capa_asistiva_opcional_y_evaluable.md)

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-13`._
