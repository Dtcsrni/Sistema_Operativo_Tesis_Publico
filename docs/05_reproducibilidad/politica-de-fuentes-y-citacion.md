# Politica de Fuentes y Citacion

Fuente maquina-legible: `manifests/bibliography_policy.yaml`.

Toda referencia debe clasificarse por tipo, nivel de evidencia y estado de verificacion.

## Politica APA 7 operativa

- OpenClaw trata APA vigente como APA 7.
- Ninguna cita generada por IA se considera valida solo por estar bien formateada.
- Una referencia queda utilizable para afirmaciones fuertes solo si conserva al menos una evidencia verificable: DOI confirmado, URL viva o hash SHA-256 de archivo local controlado.
- Si DOI/URL no se confirman, el registro debe quedar `no_verificable`; no debe promoverse a fuente valida por inferencia.
- Las afirmaciones importantes deben enlazar `claim_id -> reference_id -> evidencia primaria`.

## Gestor local

- Evidencia primaria: JSONL append-only en `OPENCLAW_SOURCE_JSONL` o `runtime/openclaw/state/sources/references.jsonl`.
- Espejo operativo: SQLite `source_records` dentro del store OpenClaw.
- CLI:
  - `python runtime/openclaw/bin/openclaw_local.py fuentes estado`
  - `python runtime/openclaw/bin/openclaw_local.py fuentes registrar --doi 10.xxxx/... --titulo "..." --autor "..." --anio 2026`
- El campo `apa_reference` es una ayuda de render APA 7; la revision final de estilo y pertinencia sigue siendo humana.

_Última actualización: `2026-05-15`._
