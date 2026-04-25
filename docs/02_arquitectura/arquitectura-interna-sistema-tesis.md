# Arquitectura Interna del Sistema de Tesis

Fuente maquina-legible:
- `manifests/system_tesis_architecture_contract.yaml`
- `manifests/system_tesis_canonical_schema.yaml`
- `manifests/system_tesis_cli_contracts.yaml`
- `manifests/system_tesis_dependency_map.yaml`

## Capas
- `canon`: eventos, estado, ledger, configuracion soberana y referencias de trazabilidad.
- `proyecciones`: wiki, dashboard, README y otros derivados materializados.
- `auditoria_guardrails`: validadores, chequeos de integridad, enforcement de gobernanza y conformidad.
- `publicacion`: bundle publico sanitizado y sus validaciones.
- `memoria_derivada`: `MEMORY.md` como resumen operativo generado desde canon, backlog y validaciones humanas.

## Fronteras
- Solo el canon puede actuar como fuente de verdad.
- Las proyecciones nunca escriben de regreso al canon.
- La publicacion sale de artefactos sanitizados, no de ediciones manuales sobre el downstream.
- La auditoria lee canon y derivados, pero no introduce acoplamientos implícitos entre capas.
- `memoria_derivada` solo resume; no sustituye ledger, matriz ni canon.

## Interfaces obligatorias
- `canon -> proyecciones`: materializacion controlada.
- `canon -> auditoria_guardrails`: lectura controlada para validacion.
- `canon -> publicacion`: sanitizacion y build.
- `auditoria_guardrails -> publicacion`: gate previo a publicar.
- `canon -> memoria_derivada`: resumen operativo verificable para retoma rapida.

## Contratos internos
- El esquema canonico tiene version explicita y politica de compatibilidad hacia atras.
- Los comandos criticos de `tesis.py` deben mantener contratos de entrada/salida declarados.
- Los cambios breaking en esquema o CLI requieren actualizar el contrato correspondiente y registrar migracion.
- El mapa de dependencias debe mantener direccion unidireccional desde canon hacia derivados y prohibir ciclos.

## Acoplamientos prohibidos
- `edge_iot` escribiendo canon.
- `publicacion` escribiendo canon.
- `memoria_derivada` escribiendo canon.
- derivados usados como fuente primaria.
- Orange Pi usada como nodo principal de autoria o decision arquitectonica.

## Dependencias críticas
- `canon.py` gobierna `events.jsonl`, `state.json`, ledger y matriz.
- `validate_structure.py`, `validate_b0_architecture.py` y `validate_memory.py` solo leen canon/contratos y bloquean drift.
- `build_readme_portada.py`, `build_wiki.py`, `build_dashboard.py` y `build_memory.py` producen superficies derivadas.
- `publication.py` solo consume derivados ya validados.

_Última actualización: `2026-04-25`._
