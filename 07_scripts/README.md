# Manual de Scripts y Operación

Este directorio contiene la capa operativa del sistema. La CLI canónica es `07_scripts/tesis.py`. Los demás scripts sostienen validación, generación y compatibilidad.

## Rutas humanas principales

### 1. Retomar el proyecto
```powershell
python 07_scripts/tesis.py status
python 07_scripts/tesis.py next
python 07_scripts/tesis.py doctor
```

### 2. Auditar antes de cerrar trabajo
```powershell
python 07_scripts/tesis.py audit --check
python 07_scripts/build_all.py
```

### 3. Publicar la capa pública sanitizada
```powershell
python 07_scripts/tesis.py publish --check
python 07_scripts/tesis.py publish --build
python 07_scripts/install_hooks.py
python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --repo-url https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico.git --branch main --push
```

### 4. Corroborar confirmación verbal con evidencia fuente
```powershell
python 07_scripts/tesis.py session open --session-id codex-YYYYMMDD
python 07_scripts/tesis.py source scaffold --session-id codex-YYYYMMDD
python 07_scripts/tesis.py source auto-register --session-id codex-YYYYMMDD
python 07_scripts/tesis.py source register --session-id codex-YYYYMMDD --transcript ruta\\a\\transcripcion.md --quote "texto exacto"
# opcional: --screenshots ruta\\a\\captura_001.png
python 07_scripts/tesis.py source verify --step-id STEP_ID_REAL
python 07_scripts/tesis.py source status --check
```

### 5. Auto-firma controlada en pre-push
```powershell
$env:SISTEMA_TESIS_STEP_ID="validación humana interna no pública"
$env:SISTEMA_TESIS_SOURCE_EVENT_ID="EVT-XXXX"
$env:SISTEMA_TESIS_SESSION_ID="codex-YYYYMMDD"
python 07_scripts/tesis.py signoff sync --step-id $env:SISTEMA_TESIS_STEP_ID --source-event-id $env:SISTEMA_TESIS_SOURCE_EVENT_ID --session-id $env:SISTEMA_TESIS_SESSION_ID --check
```

### 6. Separar commits staged por Step ID automáticamente
```powershell
python 07_scripts/tesis.py split-staged
python 07_scripts/tesis.py split-staged --commit
```

## Qué hace `tesis.py`

- `status`: estado humano resumido del sistema.
- `next`: prioridades inmediatas desde backlog, riesgos y entregable vigente.
- `doctor`: salud operativa, drift, firmas y bundle público.
- `source register`: registra evidencia privada base (transcripción + cita exacta; capturas opcionales).
- `source scaffold`: crea/actualiza automáticamente el paquete privado inicial de evidencia para una sesión.
- `source auto-register`: registra evidencia usando automáticamente `transcripcion.md` del scaffold de sesión.
- `source verify`: comprueba que un `VAL-STEP` coincide con su `source_event_id` y con la evidencia local.
- `source status`: resume el estado repo/local de la evidencia fuente de conversación.
- `signoff sync`: firma automáticamente solo fuentes wiki directas (una fuente archivo por sección) que estén en drift, exigiendo `--step-id`, `--source-event-id` y `--session-id`.
- `split-staged`: separa automáticamente el índice actual en commits por `VAL-STEP`, preservando cambios unstaged.
- `audit --check`: consistencia del canon y proyecciones primarias.
- `materialize`: materializa ledger, matriz y proyecciones desde el canon.
- `publish --check|--build`: valida o genera la capa pública sanitizada.
- `sync`: separa commits operativos y derivados manteniendo enforcement del gate.
- `sync_public_repo.py`: publica un clon filtrado (`--mode mirror`) o solo bundle (`--mode bundle`) hacia el repo público derivado.
- Verifica hash por archivo entre origen canónico y destino público antes de commit/push.
- Reutiliza un solo fingerprint por ejecución y puede actualizar en la misma corrida el destino principal y el espejo local hermano.
- Emite `_sync_provenance.json` con commit/branch/fingerprint de sincronización.
- Emite `NOTA_SEGURIDAD_Y_ACCESO.md` con políticas y contacto del tesista.
- Requiere árbol privado limpio para garantizar sincronía exacta con el commit canónico (`--allow-dirty` solo bajo uso explícito).
- `install_hooks.py`: instala hooks `pre-commit`, `pre-push`, `post-commit` y `post-merge`; `pre-push` corre gate y luego `signoff sync` con `SISTEMA_TESIS_STEP_ID` y `SISTEMA_TESIS_SOURCE_EVENT_ID`; los últimos resincronizan automáticamente el espejo local en `main`.

## Scripts de soporte

- `build_all.py`: auditoría integral del sistema.
- `build_wiki.py`: genera wiki verificable Markdown y HTML.
- `build_dashboard.py`: genera dashboard HTML derivado.
- `build_readme_portada.py`: reconstruye `README.md`.
- `report_consistency.py`: resumen legible de consistencia.
- `validate_structure.py`: valida estructura y relaciones canónicas.
- `governance_gate.py`: gate agnóstico de agente para hooks, CI y prechecks.

## Capas operativas relacionadas

- `bootstrap/`: instalación por fases para host Windows y Orange Pi.
- `manifests/`: políticas y contratos máquina-legibles del sistema.
- `config/systemd/`: servicios y timers de referencia.
- `config/env/`: variables de entorno de ejemplo.
- `runtime/openclaw/`: integración opcional, políticas y healthcheck de OpenClaw.

## Criterio operativo

- La superficie canónica no pública es la fuente de verdad.
- La superficie pública es derivada, sanitizada y no editable a mano.
- La IA es opcional; la operación principal debe seguir siendo legible para humanos.
- Si un cambio afecta gobernanza, arquitectura o método, registra decisión y vuelve a auditar.

_Última actualización: `2026-04-04`._
