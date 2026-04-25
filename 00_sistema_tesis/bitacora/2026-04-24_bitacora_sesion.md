# Bitácora de sesión 2026-04-24

- **ID de Sesión:** codex-local-20260424-openclaw-host-real-closeout-v1
- **Cadena de Confianza (Anterior):** `sha256/3efbcd9217b8002c1ebed7347e88420f36756532b2144746500e5e525db2d840`
- **Bloque principal:** B0
- **Tipo de sesión:** implementación | validación | administración | despliegue

## Infraestructura de Sesión
- **OS:** Windows 11 / WSL + `tesis-edge` Debian 12
- **Python:** `/usr/bin/python3` local, `/opt/tesis-os/venvs/openclaw/bin/python` en edge
- **Herramientas Clave:** Codex, Caveman, Serena check, OpenClaw, Docker, Conduit, systemd, SSH, pytest, `build_all.py`

## Objetivo de la sesión
Cerrar los pendientes host-real de OpenClaw: levantar `llama.cpp server` en la PC Windows, exponerlo al edge por el túnel estable y habilitar Matrix local privado en `tesis-edge` como canal remoto principal.

## Tareas del día
- [x] Reconciliar el estado Serena/Caveman inicial y registrar el bloqueo del perfil HTTP recomendado.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Levantar `llama.cpp server` en Windows y exponerlo desde `tesis-edge` en `127.0.0.1:21434`.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Desplegar Matrix local privado con Conduit en `tesis-edge` y habilitar `openclaw-matrix-bot.service`.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Ejecutar smoke end-to-end Matrix y validar registro de sesión/mensajes en SQLite.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Ejecutar pruebas focalizadas y preparar cierre documental/canónico.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Trabajo realizado
- Se corrigió `runtime/openclaw/wrappers/openclaw-llamacpp-server.ps1` para no usar `$host`, variable reservada de PowerShell, y permitir arranque real en Windows.
- Se arrancó `llama-server.exe` en Windows con `mistral-nemo:12b`, bind `0.0.0.0:21435`, contexto 4096 y offload `auto`.
- Se configuró `openclaw-desktop-tunnel.service` para publicar en `tesis-edge` `127.0.0.1:21434 -> 172.17.176.1:21435`.
- Se elevó la persistencia Windows a tarea programada `\OpenClawLlamaCppServer` con `BootTrigger`, usuario `SYSTEM` y `RunLevel=HighestAvailable`; el script Startup temporal fue eliminado para evitar doble arranque.
- Se creó backup operativo `/etc/tesis-os/openclaw.env.bak.matrix_llamacpp_20260424_022222`.
- Se desplegó Conduit en Docker como `openclaw-conduit`, escuchando solo en `127.0.0.1:6167`, sin federación pública.
- Se creó `@openclaw:tesis-edge.local`, una sala privada de control y un usuario operador local para smoke.
- Se actualizó `/etc/tesis-os/openclaw.env` con `OPENCLAW_MATRIX_*` sin exponer secretos en el repo.
- Se corrigió `runtime/openclaw/systemd/openclaw-matrix-bot.service` para invocar el wrapper con `bash`, evitando fallo `status=126` por falta de bit ejecutable.

## Evidencia Técnica e Integridad
- **Commits:** pendiente al cierre de esta sesión.
- **Archivos Clave:** `runtime/openclaw/wrappers/openclaw-llamacpp-server.ps1`, `runtime/openclaw/systemd/openclaw-matrix-bot.service`, `/etc/tesis-os/openclaw.env`, `/srv/tesis/matrix/conduit/conduit.toml`, tarea Windows `\OpenClawLlamaCppServer`.
- **Validación local focal:** `python3 -m pytest -q -s tests/test_openclaw_runtime.py tests/test_openclaw_cli.py tests/test_openclaw_notifier.py` -> `54 passed`.
- **Smoke llama.cpp Windows:** `http://172.17.176.1:21435/health` -> `{"status":"ok"}` tras arranque desde tarea `SYSTEM`; inferencia `/v1/chat/completions` -> respuesta `OK`.
- **Smoke edge:** `http://127.0.0.1:21434/health` -> `{"status":"ok"}`; `pasarela estado` reporta `active_runtime=pc_native_llamacpp` y `llamacpp.ready=true`.
- **Smoke Matrix:** `openclaw-matrix-bot.service=active`; `matrix estado` reporta `configured=true`; SQLite registra `sessions=1` y `session_messages=2`.
- **Validación del Sistema:** Auditoría `build_all.py` aprobada con perfil `historial interno no público/build_all_profile_20260424_083427.json`.

## Trabajo asistido con IA y gobernanza
- **Proveedor de asistencia:** proveedor de IA no publicado
- **Modelo/Versión de asistencia:** modelo de IA no publicado
- **Objetivo:** completar el cierre host-real de OpenClaw preservando soberanía local, fallback edge y trazabilidad verificable.
- **Nivel de Razonamiento:** alto
- **Alineación Ética:**
    - [x] Transparencia (NIST RMF)
      - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
    - [x] Soberanía Humana (UNESCO)
      - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
    - [x] Responsabilidad (ISO 42001)
      - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

### Validación de Soberanía (Handshake)
- **Pregunta Crítica:** ¿Autorizas implementar el cierre host-real de OpenClaw con Matrix edge local y llama.cpp Windows service?
- **Respuesta Erick Vega:** "PLEASE IMPLEMENT THIS PLAN:"
- **Criterio de Aceptación:** [x] Validado.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** [validación humana interna no pública]
  - **Texto exacto de confirmación verbal:** "PLEASE IMPLEMENT THIS PLAN:"
  - **Hash de confirmación verbal:** `hash omitido:omitido`
  - **Fuente de verdad de confirmación:** `00_sistema_tesis/canon/events.jsonl :: validación humana interna no pública :: human_validation.confirmation_text`
  - **Hash (Contenido):** `hash omitido:omitido`
  - **Fingerprint:** `hash omitido:omitido`
  - **Nivel de Riesgo:** Alto
  - **Modo:** Confirmación Verbal
  - **Pregunta crítica o disparador:** instrucción humana directa para implementar el plan de cierre de pendientes OpenClaw.
  - **Fuente de conversación registrada:** evento interno no público

## Economía de uso
- Presupuesto vs Avance: el costo se concentró en ejecución host-real, smoke remoto y reparación de fallos concretos (`$host` reservado, unit `status=126`, túnel apuntando a Ollama).
- Qué se evitó: exponer tokens en git o en salida pública, declarar Matrix listo sin sesión real y marcar `llama.cpp` como listo antes de tener `/health` e inferencia.
- Qué ameritaría subir razonamiento en la siguiente sesión: hardening de Matrix con cliente remoto/E2EE, rotación de tokens y revisión de resiliencia post-reinicio físico.

## Siguiente paso concreto
Rotar o custodiar los tokens Matrix fuera de salida conversacional y hacer una prueba de reinicio físico cuando convenga confirmar el `BootTrigger` fuera de esta sesión.

[LID]: log_sesiones_trabajo_registradas.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../07_scripts/build_all.py

_Última actualización: `2026-04-25`._
