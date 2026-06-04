---
title: "PRD: Desarrollo guiado por especificaciones y eficiencia agÃ©ntica"
date: 2026-05-06
category: enhancement
status: closed
reporter: "Codex"
step_id: "validación humana interna no pública"
trace_status: "validado"
---

# PRD: Desarrollo guiado por especificaciones y eficiencia agÃ©ntica

## Problem Statement

El repositorio ya contiene gobernanza sÃ³lida, Serena MCP, Caveman, TDD, triage local, `build_all.py`, Mission Control y mÃºltiples scripts de operaciÃ³n. La fricciÃ³n actual no es falta de capacidad, sino dispersiÃ³n: agentes y humanos deben saltar entre canon, pendientes, scripts, skills, comandos y documentaciÃ³n antes de saber quÃ© cambiar, quÃ© probar y quÃ© no tocar.

AdemÃ¡s, algunos comandos de entrada rÃ¡pida pueden fallar por detalles operativos pequeÃ±os. Cuando eso ocurre, la economÃ­a de tokens y tiempo se degrada porque el agente reconstruye contexto manualmente o el humano debe depurar la plataforma antes de avanzar en la tesis.

## Solution

Adoptar una capa mÃ­nima de Spec Driven Development (SDD) compatible con el flujo existente:

1. Toda mejora tÃ©cnica no trivial empieza como una especificaciÃ³n local en `00_sistema_tesis/pendientes/`.
2. La especificaciÃ³n declara objetivo, rutas afectadas, interfaz pÃºblica esperada, pruebas de aceptaciÃ³n y requisitos de trazabilidad.
3. El agente usa Caveman para salida concisa, Serena para contexto compacto y `agent_task_router.py` para decidir ruta de ejecuciÃ³n.
4. La implementaciÃ³n sigue TDD por rebanadas verticales: una prueba de comportamiento, cambio mÃ­nimo, verificaciÃ³n enfocada y cierre con auditorÃ­a proporcional.
5. Solo se promueve a decisiÃ³n DEC o validaciÃ³n VAL-STEP cuando el Tesista lo autorice explÃ­citamente.

## User Stories

1. Como Tesista, quiero que cada cambio relevante tenga una especificaciÃ³n breve antes de editar cÃ³digo, para entender alcance, riesgos y criterio de aceptaciÃ³n.
2. Como agente de IA, quiero un punto de entrada Ãºnico para contexto, rutas afectadas y pruebas esperadas, para no releer todo el repositorio.
3. Como humano desarrollador, quiero comandos de estado y tooling que fallen de forma diagnÃ³stica, para no perder tiempo con errores no accionables.
4. Como mantenedor del canon, quiero que SDD no marque nada como validado automÃ¡ticamente, para conservar soberanÃ­a humana y trazabilidad.
5. Como operador de OpenClaw, quiero que las mejoras se hagan por rutas pequeÃ±as y verificables, para simplificar sin romper servicios existentes.

## Implementation Decisions

- Mantener la estructura del repositorio. No reorganizar carpetas ni mover canon en esta primera fase.
- Usar `00_sistema_tesis/pendientes/` como cola SDD inicial, con estado `needs-triage` hasta revisiÃ³n humana.
- Definir una plantilla compacta de spec que combine PRD, issue local, pruebas esperadas y preflight de gobernanza.
- Conectar SDD con lo ya existente: `CONTEXT.md`, skills locales, `agent_task_router.py`, Serena MCP y `build_all.py`.
- Corregir primero comandos de entrada rÃ¡pida que rompen flujo (`check_agent_context_tools.py`, `tesis.py status`) antes de ampliar automatizaciÃ³n.
- Evitar decisiones DEC nuevas en esta fase salvo que el Tesista pida formalizaciÃ³n canÃ³nica.

## Testing Decisions

- Las pruebas deben verificar comportamiento pÃºblico, no detalles internos.
- Para tooling de agentes: probar que el CLI corre sin `PYTHONPATH` manual y devuelve estado estructurado.
- Para canon/status: probar que eventos mal formados se reportan como fallos auditables en vez de provocar excepciones.
- Para SDD: agregar pruebas ligeras de plantilla/estructura si se introduce un generador o verificador de specs.
- Ejecutar siempre pruebas enfocadas antes de `build_all.py`; usar `build_all.py --group ...` cuando el cambio sea acotado y el full build estÃ© bloqueado por deuda no relacionada.

## Out of Scope

- ReorganizaciÃ³n global de `07_scripts/`.
- MigraciÃ³n de canon, ledger o matriz a un esquema nuevo.
- AutovalidaciÃ³n de tareas o cierre automÃ¡tico de Step IDs.
- ExposiciÃ³n de evidencia privada a servicios cloud.
- Cambios profundos a Mission Control, OpenClaw o Docker Compose sin especificaciÃ³n propia.

## Further Notes

Primera ola recomendada:

1. Reparar tooling de entrada rÃ¡pida y comandos de estado.
2. Crear plantilla SDD mÃ­nima y verificador de estructura.
3. AÃ±adir comando operativo para crear specs desde CLI sin tocar canon protegido.
4. Integrar el verificador SDD como paso liviano de `build_all.py` o como gate por tag.
5. Revisar la cola `pendientes/` y convertir mejoras grandes en specs pequeÃ±as listas para agente.


## Cierre de Trazabilidad
Validado formalmente en validación humana interna no pública. Implementado 	esis.py spec new y reparado alidate_sdd_specs.py.

_Última actualización: `2026-06-03`._
