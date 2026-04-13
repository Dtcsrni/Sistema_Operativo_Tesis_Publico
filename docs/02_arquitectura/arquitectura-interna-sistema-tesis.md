# Arquitectura Interna del Sistema de Tesis

Fuente maquina-legible:
- `manifests/system_tesis_architecture_contract.yaml`
- `manifests/system_tesis_canonical_schema.yaml`
- `manifests/system_tesis_cli_contracts.yaml`

## Capas
- `canon`: eventos, estado, ledger, configuracion soberana y referencias de trazabilidad.
- `proyecciones`: wiki, dashboard, README y otros derivados materializados.
- `auditoria_guardrails`: validadores, chequeos de integridad, enforcement de gobernanza y conformidad.
- `publicacion`: bundle publico sanitizado y sus validaciones.

## Fronteras
- Solo el canon puede actuar como fuente de verdad.
- Las proyecciones nunca escriben de regreso al canon.
- La publicacion sale de artefactos sanitizados, no de ediciones manuales sobre el downstream.
- La auditoria lee canon y derivados, pero no introduce acoplamientos implícitos entre capas.

## Interfaces obligatorias
- `canon -> proyecciones`: materializacion controlada.
- `canon -> auditoria_guardrails`: lectura controlada para validacion.
- `canon -> publicacion`: sanitizacion y build.
- `auditoria_guardrails -> publicacion`: gate previo a publicar.

## Contratos internos
- El esquema canonico tiene version explicita y politica de compatibilidad hacia atras.
- Los comandos criticos de `tesis.py` deben mantener contratos de entrada/salida declarados.
- Los cambios breaking en esquema o CLI requieren actualizar el contrato correspondiente y registrar migracion.

## Acoplamientos prohibidos
- `edge_iot` escribiendo canon.
- `publicacion` escribiendo canon.
- derivados usados como fuente primaria.
- Orange Pi usada como nodo principal de autoria o decision arquitectonica.

_Última actualización: `2026-04-13`._
