# Contrato Maestro de Dominios

Fuente maquina-legible:
- `manifests/domain_runtime_isolation.yaml`
- `manifests/domain_network_policy.yaml`
- `manifests/interdomain_exchange_contract.yaml`
- `manifests/domain_backup_policy.yaml`
- `manifests/b0_external_gates.yaml`

## Objetivo
Congelar el contrato de separacion entre `sistema_tesis`, `openclaw`, `edge_iot`, `administrativo` y `personal` para cerrar B0 desde escritorio sin fingir validaciones de host real.

## Reglas no negociables
- No HTTP interdominio por default.
- El intercambio entre dominios ocurre solo por `archivo_draft`, `spool_local` o `cli_explicita`.
- Los secretos se leen solo desde el dominio autorizado.
- Orange Pi es clon operativo y superficie de validacion local, no workspace principal de autoria.
- Ningun artefacto derivado se trata como fuente de verdad del canon.

## Dominios operativos
- `sistema_tesis`: canon, auditoria, publicacion y operacion documental.
- `openclaw`: capa asistiva opcional, con entrada solo por `localhost` y sin convertirse en puente interdominio.
- `edge_iot`: runtime edge separado del canon y de la publicacion.
- `administrativo`: backups, observabilidad y operacion de mantenimiento.
- `personal`: workspace logico sin servicio persistente.

## Contratos permitidos
- `openclaw -> sistema_tesis`: `archivo_draft` en `outbox`.
- `sistema_tesis -> openclaw`: `cli_explicita` con gatillo humano.
- `edge_iot -> sistema_tesis`: `spool_local` para evidencia tecnica.

## Contratos prohibidos
- HTTP entre dominios como flujo normal.
- Lectura libre de workspaces cruzados.
- Acceso directo a SQLite o estado interno de otro dominio.
- Lectura de secretos de otro dominio.
- Edicion primaria en Orange Pi.

## Cierre B0 desde escritorio
- El repo puede dejar cerrados los contratos, manifests, scripts y pruebas de conformidad.
- La validacion real en Orange Pi queda como gate externo documentado en `manifests/b0_external_gates.yaml`.
- `ENT-013` puede quedar listo para validacion, pero no validado, hasta ejecutar pruebas reales de host.

_Última actualización: `2026-04-25`._
