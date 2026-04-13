<!-- SISTEMA_TESIS:PROTEGIDO -->

# DEC-0023 Serena MCP como Capa Comun para Agentes

- Fecha: 2026-04-08
- Estado: aceptada
- Alcance: arquitectura | operacion | gobernanza

## Contexto
El repositorio ya habia incorporado Serena MCP como servidor local y ya existia una integracion operativa comprobada con Codex. Posteriormente tambien se implemento un adapter interno para que OpenClaw consuma Serena MCP como capacidad auxiliar de contexto compacto y preflight de gobernanza. Hacia falta fijar una decision canonica que unifique esa linea de integracion sin mezclarla con la arquitectura `desktop-first` de [DEC-0022](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-04-08_DEC-0022_arquitectura_operativa_escritorio_primario_y_orange_pi_edge.md) ni con el ruteo de proveedores de inferencia.

## Decision
Adoptar a `serena-local` como la capa oficial comun de contexto compacto, preflight de gobernanza y cambio controlado para agentes del proyecto bajo las siguientes reglas:

1. `Codex` en VS Code mantiene a Serena MCP como integracion MCP local oficial del proyecto.
2. `OpenClaw` consume Serena MCP mediante un adapter interno auxiliar y no como proveedor de modelo, por lo que `route_task` y el registro de proveedores siguen separados de Serena.
3. Los hosts o agentes compatibles con MCP pueden integrar `serena-local` usando el contrato comun documentado por el proyecto, sin que eso implique crear conectores dedicados para cada host en esta fase.
4. Serena MCP se usa por defecto para contexto y gobernanza cuando haya `target_paths`, contexto documental relevante o riesgo operativo suficiente, pero la integracion debe seguir siendo modular, reversible y no obligatoria para flujos puramente diagnosticos o de solo lectura cuando el adapter no este disponible.
5. Ninguna integracion con Serena sustituye la soberania humana, el protocolo de [DEC-0014](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md) ni el pipeline base del sistema.

## Consecuencias
- Positivas: unifica la capa de contexto/gobernanza para agentes, evita mezclar MCP con proveedores de inferencia y facilita onboarding para hosts compatibles.
- Negativas: introduce una superficie adicional de configuracion y exige documentacion operativa mas precisa para degradacion, timeouts y transporte.
- Riesgo controlado: si Serena falla, los flujos no mutantes pueden degradar con estado explicito; los bloqueos de gobernanza no deben ocultarse ni omitirse.

## Soporte de Validacion
- **Soporte principal:** [validación humana interna no pública]
- **Regularizacion de implementacion existente:** [validación humana interna no pública]

## Referencias

- [DEC-0014](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- [DEC-0018](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-26_DEC-0018_evidencia_fuente_conversacion_codex_para_confirmacion_verbal.md)
- [DEC-0020](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-27_DEC-0020_openclaw_como_capa_asistiva_opcional_y_evaluable.md)
- [DEC-0022](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-04-08_DEC-0022_arquitectura_operativa_escritorio_primario_y_orange_pi_edge.md)
- [contrato_serena_mcp_agentes.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/contrato_serena_mcp_agentes.md)
- [operacion_serena_mcp_codex.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/operacion_serena_mcp_codex.md)
- [openclaw-workspace-local.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/docs/03_operacion/openclaw-workspace-local.md)

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-13`._
