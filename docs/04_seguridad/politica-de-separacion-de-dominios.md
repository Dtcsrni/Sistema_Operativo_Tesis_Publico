# Politica de Separacion de Dominios

Fuente maquina-legible: `manifests/domain_boundaries.yaml`.

No mezclar por defecto origen personal, proceso profesional, trazabilidad academica y artefactos tecnicos finales.

## Reglas operativas
- No HTTP interdominio por default.
- Intercambio solo por `archivo_draft`, `spool_local` o `cli_explicita`.
- Los secretos se leen solo por el dominio autorizado.
- Orange Pi es clon operativo y no workspace principal de autoria.
- La validacion fisica de host queda como gate externo; no debe confundirse con cierre arquitectonico desde escritorio.

_Última actualización: `2026-04-13`._
