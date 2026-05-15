---
title: "PRD: Desarrollo guiado por especificaciones y eficiencia agéntica"
date: 2026-05-06
category: enhancement
status: needs-triage
reporter: "Codex"
---

# PRD: Desarrollo guiado por especificaciones y eficiencia agéntica

## Problem Statement

El repositorio ya contiene gobernanza sólida, Serena MCP, Caveman, TDD, triage local, `build_all.py`, Mission Control y múltiples scripts de operación. La fricción actual no es falta de capacidad, sino dispersión: agentes y humanos deben saltar entre canon, pendientes, scripts, skills, comandos y documentación antes de saber qué cambiar, qué probar y qué no tocar.

Además, algunos comandos de entrada rápida pueden fallar por detalles operativos pequeños. Cuando eso ocurre, la economía de tokens y tiempo se degrada porque el agente reconstruye contexto manualmente o el humano debe depurar la plataforma antes de avanzar en la tesis.

## Solution

Adoptar una capa mínima de Spec Driven Development (SDD) compatible con el flujo existente:

1. Toda mejora técnica no trivial empieza como una especificación local en `00_sistema_tesis/pendientes/`.
2. La especificación declara objetivo, rutas afectadas, interfaz pública esperada, pruebas de aceptación y requisitos de trazabilidad.
3. El agente usa Caveman para salida concisa, Serena para contexto compacto y `agent_task_router.py` para decidir ruta de ejecución.
4. La implementación sigue TDD por rebanadas verticales: una prueba de comportamiento, cambio mínimo, verificación enfocada y cierre con auditoría proporcional.
5. Solo se promueve a decisión DEC o validación VAL-STEP cuando el Tesista lo autorice explícitamente.

## User Stories

1. Como Tesista, quiero que cada cambio relevante tenga una especificación breve antes de editar código, para entender alcance, riesgos y criterio de aceptación.
2. Como agente de IA, quiero un punto de entrada único para contexto, rutas afectadas y pruebas esperadas, para no releer todo el repositorio.
3. Como humano desarrollador, quiero comandos de estado y tooling que fallen de forma diagnóstica, para no perder tiempo con errores no accionables.
4. Como mantenedor del canon, quiero que SDD no marque nada como validado automáticamente, para conservar soberanía humana y trazabilidad.
5. Como operador de OpenClaw, quiero que las mejoras se hagan por rutas pequeñas y verificables, para simplificar sin romper servicios existentes.

## Implementation Decisions

- Mantener la estructura del repositorio. No reorganizar carpetas ni mover canon en esta primera fase.
- Usar `00_sistema_tesis/pendientes/` como cola SDD inicial, con estado `needs-triage` hasta revisión humana.
- Definir una plantilla compacta de spec que combine PRD, issue local, pruebas esperadas y preflight de gobernanza.
- Conectar SDD con lo ya existente: `CONTEXT.md`, skills locales, `agent_task_router.py`, Serena MCP y `build_all.py`.
- Corregir primero comandos de entrada rápida que rompen flujo (`check_agent_context_tools.py`, `tesis.py status`) antes de ampliar automatización.
- Evitar decisiones DEC nuevas en esta fase salvo que el Tesista pida formalización canónica.

## Testing Decisions

- Las pruebas deben verificar comportamiento público, no detalles internos.
- Para tooling de agentes: probar que el CLI corre sin `PYTHONPATH` manual y devuelve estado estructurado.
- Para canon/status: probar que eventos mal formados se reportan como fallos auditables en vez de provocar excepciones.
- Para SDD: agregar pruebas ligeras de plantilla/estructura si se introduce un generador o verificador de specs.
- Ejecutar siempre pruebas enfocadas antes de `build_all.py`; usar `build_all.py --group ...` cuando el cambio sea acotado y el full build esté bloqueado por deuda no relacionada.

## Out of Scope

- Reorganización global de `07_scripts/`.
- Migración de canon, ledger o matriz a un esquema nuevo.
- Autovalidación de tareas o cierre automático de Step IDs.
- Exposición de evidencia privada a servicios cloud.
- Cambios profundos a Mission Control, OpenClaw o Docker Compose sin especificación propia.

## Further Notes

Primera ola recomendada:

1. Reparar tooling de entrada rápida y comandos de estado.
2. Crear plantilla SDD mínima y verificador de estructura.
3. Añadir comando operativo para crear specs desde CLI sin tocar canon protegido.
4. Integrar el verificador SDD como paso liviano de `build_all.py` o como gate por tag.
5. Revisar la cola `pendientes/` y convertir mejoras grandes en specs pequeñas listas para agente.

_Última actualización: `2026-05-15`._
