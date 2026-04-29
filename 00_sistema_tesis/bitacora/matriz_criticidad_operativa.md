# Matriz de criticidad operativa

Fecha: 2026-04-27  
Alcance: fuentes canonicas, guardrails, build, publicacion y trazabilidad.

Pre-checks: [Integridad][LID] [Ética][GOV] [Auditoría][AUD] Contexto explícito | Confirmación verificable | Reproducibilidad mínima

## Criterios
- Criticidad `alta`: fallo bloquea gobernanza, build o trazabilidad minima.
- Criticidad `media`: fallo degrada controles o continuidad, pero hay mitigacion parcial.
- Criticidad `baja`: fallo afecta calidad operativa sin romper invariantes nucleares.

## Matriz

| Activo | Script(s) que escriben | Script(s) que leen/validan | Impacto de falla | Criticidad |
|---|---|---|---|---|
| `00_sistema_tesis/canon/events.jsonl` | `07_scripts/tesis.py materialize` | `07_scripts/tesis.py audit --check`, `07_scripts/validate_structure.py`, `07_scripts/governance_gate.py` | Rompe proyecciones, auditoria y evidencia de sesiones | alta |
| `00_sistema_tesis/canon/state.json` | `07_scripts/tesis.py materialize` | `07_scripts/tesis.py status`, `07_scripts/validate_structure.py` | Estado inconsistente para control operativo | alta |
| `00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md` | `07_scripts/new_log.py`, `07_scripts/update_ledger.py` | `07_scripts/verify_ledger.py`, `07_scripts/validate_structure.py`, `07_scripts/document_audit.py` | Debilita trazabilidad y verificabilidad metodologica | alta |
| `00_sistema_tesis/bitacora/matriz_trazabilidad.md` | `07_scripts/tesis.py materialize` | `07_scripts/validate_structure.py`, `07_scripts/document_audit.py` | Pérdida de visibilidad de decisiones y evidencia | alta |
| `00_sistema_tesis/config/ia_gobernanza.yaml` | Edicion humana controlada | `07_scripts/governance_gate.py`, `07_scripts/build_dashboard.py`, `07_scripts/validate_structure.py` | Desalineacion de politica IA y enforcement | alta |
| `manifests/domain_backup_policy.yaml` | Edicion humana controlada | `ops/respaldo/ejecutar_respaldo.sh`, `ops/recuperacion/restaurar_desde_emmc.sh`, `07_scripts/validate_structure.py` | Riesgo de backup no confiable o no recuperable | alta |
| `07_scripts/governance_gate.py` | Edicion humana controlada | Hooks (`pre-commit`, `pre-push`), CI `verify.yml` | Se pierde bloqueo preventivo en cambios sensibles | alta |
| `07_scripts/build_all.py` | Edicion humana controlada | Operacion manual y pipelines locales | Cadena de build/auditoria incompleta o inconsistente | alta |
| `07_scripts/secret_scanner.py` | Edicion humana controlada | `07_scripts/build_all.py` | Fuga de secretos no detectada en repo/canon | alta |
| `07_scripts/sync_public_repo.py` | Edicion humana controlada | `07_scripts/tesis.py publish --build`, CI `verify.yml`, hooks | Publicacion publica insegura o no sanitizada | alta |
| `.github/workflows/verify.yml` | Edicion humana controlada | GitHub Actions | Falsos verdes en CI, regresiones sin deteccion | media |
| `bootstrap/orangepi/51_hardening-edge-iot.sh` | Ejecucion bootstrap | Operacion edge | Superficie de ataque elevada por permisos | media |
| `07_scripts/validate_structure.py` | Edicion humana controlada | `07_scripts/build_all.py`, `governance_gate.py` | Falsos positivos/negativos de cumplimiento documental | media |
| `07_scripts/build_dashboard.py` | Edicion humana controlada | `07_scripts/build_all.py` | Dashboard inconsistente o roto | baja |

## Prioridad de remediacion
1. Fortalecer deteccion de secretos y manejo de credenciales en hooks.
2. Endurecer politica/flujo de backups (cifrado y verificacion fuerte).
3. Reducir privilegios en hardening edge y robustecer restore.
4. Disminuir fragilidad en `build_all.py` y `validate_structure.py`.
5. Aumentar cobertura de pruebas para scripts criticos.

[LID]: ../bitacora/log_sesiones_trabajo_registradas.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../../07_scripts/build_all.py

_Última actualización: `2026-04-29`._
