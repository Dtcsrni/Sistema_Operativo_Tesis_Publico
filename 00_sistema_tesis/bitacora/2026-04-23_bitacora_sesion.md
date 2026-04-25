# Bitácora de sesión 2026-04-23

- **ID de Sesión:** codex-local-20260423-openclaw-pcfirst-matrix-v1
- **Cadena de Confianza (Anterior):** `sha256/1009b20222a10bd74c57ae57e3b97e6639c093a403c26eab43dbe72a79b31289`
- **Bloque principal:** B0
- **Tipo de sesión:** implementación | validación | documentación | despliegue

## Infraestructura de Sesión
- **OS:** Windows 11 / WSL + `tesis-edge` Debian 12
- **Python:** `/usr/bin/python3` local, `/opt/tesis-os/venvs/openclaw/bin/python` en edge
- **Herramientas Clave:** Codex, Caveman, Serena check, OpenClaw, pytest, rsync, SSH `tesis-edge`, systemd, `build_wiki.py`, `validate_wiki.py`, `build_all.py`

## Objetivo de la sesión
Implementar el rediseño OpenClaw PC-first con `session-layer` común, `Matrix` como canal remoto principal, `Telegram` como secundario, `pc_native_llamacpp` como runtime pesado preferido y cierre documental/verificable con despliegue parcial real en edge.

## Tareas del día
- [x] Refactorizar OpenClaw para introducir sesiones compartidas entre `cli`, `web`, `telegram` y `matrix`.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Añadir soporte `pc_native_llamacpp` y mantener compatibilidad transitoria con `desktop_compute`.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Documentar arquitectura, operación local y flujo escritorio-edge.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Registrar autorización humana con evidencia fuente exacta.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Aplicar el cambio en `tesis-edge` con backup de `openclaw.env` y smoke real.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Sincronizar la wiki oficial derivada y ejecutar auditoría local completa.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Trabajo realizado
- Se añadió `runtime/openclaw/openclaw_local/session_layer.py` y se conectó al bot Telegram, al adaptador Matrix, a la web local y al CLI.
- Se añadió `runtime/openclaw/openclaw_local/matrix_bot.py` con polling y procesamiento de eventos Matrix reutilizando el mismo contrato de sesión.
- Se promovió `pc_native_llamacpp` en manifests y ruteo, conservando `desktop_compute` como alias transitorio.
- Se extendió `runtime_status.py` para detectar `llama.cpp`, medirlo y evitar promoción falsa cuando el endpoint pesado responde `404`.
- Se corrigió `build_nodes_summary()` para que el edge siga reportando `ollama_local` aunque la PC esté configurada para `llamacpp`.
- Se actualizaron `docs/02_arquitectura/openclaw-control-plane.md`, `docs/03_operacion/openclaw-workspace-local.md` y `docs/03_operacion/flujo-escritorio-orange-pi.md`.
- Se desplegaron en `tesis-edge` los archivos OpenClaw actualizados mediante `rsync --rsync-path='sudo rsync'`.
- Se instaló `/etc/systemd/system/openclaw-matrix-bot.service`.
- Se creó backup operativo `/etc/tesis-os/openclaw.env.bak.pcfirst_20260423_063545` y se añadieron defaults:
  - `OPENCLAW_PROVIDER_POLICY=hybrid_controlled`
  - `OPENCLAW_PREMIUM_AUTO=1`
  - `OPENCLAW_DESKTOP_RUNTIME=llamacpp`
  - `OPENCLAW_DESKTOP_RUNTIME_BASE_URL=http://127.0.0.1:21434`
  - `OPENCLAW_DESKTOP_RUNTIME_MODEL=mistral-nemo:12b`
  - `OPENCLAW_DESKTOP_NATIVE_HOST=windows`
  - `OPENCLAW_EDGE_ROLE=relay_light_runtime`
  - `OPENCLAW_MATRIX_ENABLED=0`
- Se reinició `openclaw-telegram-bot.service` y se dejó `openclaw-matrix-bot.service` instalado pero `disabled/inactive` hasta disponer de credenciales Matrix reales.

## Evidencia Técnica e Integridad
- **Archivos Clave:** `runtime/openclaw/openclaw_local/session_layer.py`, `runtime/openclaw/openclaw_local/matrix_bot.py`, `runtime/openclaw/openclaw_local/runtime_status.py`, `runtime/openclaw/openclaw_local/telegram_bot.py`, `runtime/openclaw/openclaw_local/web.py`, `runtime/openclaw/bin/openclaw_local.py`, `runtime/openclaw/systemd/openclaw-matrix-bot.service`, `config/env/openclaw.env.example`, `docs/02_arquitectura/openclaw-control-plane.md`, `docs/03_operacion/openclaw-workspace-local.md`, `docs/03_operacion/flujo-escritorio-orange-pi.md`, `manifests/openclaw_provider_registry.yaml`
- **Validación local principal:** `python3 -m pytest -q -s tests/test_openclaw_runtime.py tests/test_openclaw_cli.py tests/test_openclaw_telegram_bot.py tests/test_desktop_edge_flow.py tests/test_openclaw_notifier.py` -> `109 passed`
- **Smoke remoto real:** `pasarela estado` en `tesis-edge` reporta:
  - `desktop.runtime=llamacpp`
  - `edge.runtime=ollama_local`
  - `runtime_status.active_runtime=ollama_local`
  - `runtime_status.llamacpp.ready=false`
  - `runtime_status.llamacpp.probe_error=http_404`
- **Smoke remoto focal:** 
  - `tests/test_openclaw_telegram_bot.py -k 'status_command_reports_chat_provider_and_model or parse_command_defaults_to_chat or status_command_reports_last_backend_busy'` -> `3 passed`
  - `tests/test_openclaw_cli.py -k 'matrix_status_reports_not_configured or matrix_process_creates_session or doctor_reports_domains_and_store'` -> `3 passed`
- **Hallazgo host-real importante:** el endpoint pesado `127.0.0.1:21434` sigue apuntando al túnel/Ollama actual; `llama.cpp server` todavía no está instalado ni levantado de forma nativa en la PC principal. Por eso el runtime queda `configured but not ready`, sin promoción falsa.

## Trabajo asistido con IA y gobernanza
- **Proveedor de asistencia:** proveedor de IA no publicado
- **Modelo/Versión de asistencia:** modelo de IA no publicado
- **Objetivo:** ejecutar la implementación completa solicitada, verificar regresión local, desplegar en edge sin romper el runtime existente y cerrar documentación canónica.
- **Nivel de Razonamiento:** alto
- **Alineación Ética:**
  - [x] Transparencia (NIST RMF)
    - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - [x] Soberanía Humana (UNESCO)
    - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - [x] Responsabilidad (ISO 42001)
    - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

### Validación de Soberanía (Handshake)
- **Pregunta Crítica:** Instrucción humana directa para ejecutar la implementación completa de OpenClaw PC-first con Matrix soberano y runtime pesado nativo.
- **Respuesta Erick Vega:** "PLEASE IMPLEMENT THIS PLAN:"
- **Criterio de Aceptación:** [x] Validado con validación humana interna no pública.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** validación humana interna no pública
  - **Texto exacto de confirmación verbal:** "PLEASE IMPLEMENT THIS PLAN:"
  - **Hash de confirmación verbal:** `hash omitido:omitido`
  - **Fuente de verdad de confirmación:** `00_sistema_tesis/canon/events.jsonl :: validación humana interna no pública :: human_validation.confirmation_text`
  - **Fuente de conversación registrada:** evento interno no público
  - **Nivel de Riesgo:** ALTO
  - **Modo:** Confirmación Verbal
  - **Pregunta crítica o disparador:** implementación integral OpenClaw PC-first con `Matrix`, `pc_native_llamacpp` y cierre documental verificable

## Economía de uso
- Presupuesto vs Avance: la mayor parte del costo se concentró en refactor multiarchivo, validación amplia y smoke remoto, no en iteración exploratoria.
- Qué se evitó: tocar `git pull` en el clon operativo del edge, habilitar Matrix sin credenciales reales, declarar `llama.cpp` listo sin endpoint funcional o reescribir cambios ajenos del worktree.
- Qué ameritaría subir razonamiento en la siguiente sesión: instalación host-native real de `llama.cpp server` en Windows y despliegue del homeserver Matrix con credenciales/salas definitivas.

## Siguiente paso concreto
Completar el tramo host-real restante:
1. instalar y arrancar `llama.cpp server` en la PC principal;
2. apuntar `OPENCLAW_DESKTOP_RUNTIME_BASE_URL` al endpoint real;
3. configurar `OPENCLAW_MATRIX_*` con homeserver/token/salas y habilitar `openclaw-matrix-bot.service`.

[LID]: log_sesiones_trabajo_registradas.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../07_scripts/build_all.py

_Última actualización: `2026-04-25`._
