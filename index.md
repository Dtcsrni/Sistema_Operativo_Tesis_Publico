# Bundle público sanitizado

Definir la exportación pública sanitizada, legible y reproducible del sistema operativo de tesis sin exponer trazabilidad privada ni infraestructura sensible.

- **Generado:** `2026-03-26`
- **Estado:** `ok`
- **Origen canónico (commit):** `649ba20fe80cad06192b8ca2a64825a9bd75d164`
- **Fingerprint del bundle:** `0e53832a3817ff82ccd0d17e7317cee7610dc21a7156dcf2661a9091fdeaa9ea`
- **Aviso:** Este bundle público es un artefacto derivado y sanitizado. No se corrige a mano; se reconstruye desde la base privada.

## Superficies

- **Privada:** canon, ledger, matriz, bitácoras, backlog y auditoría completa.
- **Pública:** derivado sanitizado para lectura humana, divulgación y evaluación externa.
- **IA:** apoyo opcional; la operación del bundle público no depende de IA.

## Artefactos incluidos

- `06_dashboard/publico/README_publico.md` ← `README.md`
- `06_dashboard/publico/wiki/bitacora.md` ← `06_dashboard/wiki/bitacora.md`
- `06_dashboard/publico/wiki/bloques.md` ← `06_dashboard/wiki/bloques.md`
- `06_dashboard/publico/wiki/decisiones.md` ← `06_dashboard/wiki/decisiones.md`
- `06_dashboard/publico/wiki/experimentos.md` ← `06_dashboard/wiki/experimentos.md`
- `06_dashboard/publico/wiki/gobernanza.md` ← `06_dashboard/wiki/gobernanza.md`
- `06_dashboard/publico/wiki/hipotesis.md` ← `06_dashboard/wiki/hipotesis.md`
- `06_dashboard/publico/wiki/implementacion.md` ← `06_dashboard/wiki/implementacion.md`
- `06_dashboard/publico/wiki/index.md` ← `06_dashboard/wiki/index.md`
- `06_dashboard/publico/wiki/planeacion.md` ← `06_dashboard/wiki/planeacion.md`
- `06_dashboard/publico/wiki/sistema.md` ← `06_dashboard/wiki/sistema.md`
- `06_dashboard/publico/wiki/tesis.md` ← `06_dashboard/wiki/tesis.md`
- `06_dashboard/publico/wiki_html/bitacora.html` ← `06_dashboard/generado/wiki/bitacora.html`
- `06_dashboard/publico/wiki_html/bloques.html` ← `06_dashboard/generado/wiki/bloques.html`
- `06_dashboard/publico/wiki_html/decisiones.html` ← `06_dashboard/generado/wiki/decisiones.html`
- `06_dashboard/publico/wiki_html/experimentos.html` ← `06_dashboard/generado/wiki/experimentos.html`
- `06_dashboard/publico/wiki_html/gobernanza.html` ← `06_dashboard/generado/wiki/gobernanza.html`
- `06_dashboard/publico/wiki_html/hipotesis.html` ← `06_dashboard/generado/wiki/hipotesis.html`
- `06_dashboard/publico/wiki_html/implementacion.html` ← `06_dashboard/generado/wiki/implementacion.html`
- `06_dashboard/publico/wiki_html/index.html` ← `06_dashboard/generado/wiki/index.html`
- `06_dashboard/publico/wiki_html/planeacion.html` ← `06_dashboard/generado/wiki/planeacion.html`
- `06_dashboard/publico/wiki_html/sistema.html` ← `06_dashboard/generado/wiki/sistema.html`
- `06_dashboard/publico/wiki_html/tesis.html` ← `06_dashboard/generado/wiki/tesis.html`
- `06_dashboard/publico/dashboard/index.html` ← `06_dashboard/generado/index.html`
- `06_dashboard/publico/dashboard/estilos.css` ← `06_dashboard/generado/estilos.css`
- `06_dashboard/publico/dashboard/app.js` ← `06_dashboard/generado/app.js`
- `06_dashboard/publico/dashboard/manifest.webmanifest` ← `06_dashboard/generado/manifest.webmanifest`
- `06_dashboard/publico/dashboard/sw.js` ← `06_dashboard/generado/sw.js`
- `06_dashboard/publico/dashboard/icon.svg` ← `06_dashboard/generado/icon.svg`
- `06_dashboard/publico/dashboard/badges/integrity.svg` ← `06_dashboard/generado/badges/integrity.svg`
- `06_dashboard/publico/dashboard/badges/ledger.svg` ← `06_dashboard/generado/badges/ledger.svg`
- `06_dashboard/publico/dashboard/badges/security_status.svg` ← `06_dashboard/generado/badges/security_status.svg`

## Reglas aplicadas

- rutas_locales_file_uri
- rutas_locales_windows_repo
- identificadores_validacion
- hashes_sha256
- curp_personal
- [reporte_interno_redactado]
- [bitacora_privada]/
- [reportes_privados]/
- file_uri_redaction
- absolute_windows_path_redaction
- val_step_redaction
- sha256_redaction
- private_canon_redaction
- agent_identity_redaction

## Qué revisar siempre

- `README_publico.md`
- `dashboard/index.html`
- `wiki/index.md`
- `manifest_publico.json`


