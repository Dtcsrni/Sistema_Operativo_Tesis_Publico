# Implementacion OpenClaw PC-first con Matrix y runtime pesado nativo

## Estado
- Estado actual: implementado y validado en repositorio.
- Politica operativa: `desktop-first`, `local-first`, `hybrid_controlled`.
- Plano remoto principal: `Matrix`.
- Canal secundario: `Telegram`.
- Runtime pesado preferido: `pc_native_llamacpp`.
- Runtime ligero edge: `ollama_local`.

## Componentes implementados
- `session-layer` comun para `cli`, `web_local`, `matrix` y `telegram`.
- API local de sesiones y trazas:
  - `POST /sessions`
  - `POST /sessions/{id}/messages`
  - `GET /sessions/{id}`
  - `GET /nodes`
  - `GET /providers`
  - `POST /sessions/{id}/approve`
  - `GET /traces/{id}`
- Adaptador `matrix_bot.py` con polling y proceso de eventos por sala.
- Adaptador Telegram adelgazado sobre el mismo contrato de sesion.
- Deteccion explicita de `llama.cpp server` y seleccion de `pc_native_llamacpp` como carril pesado cuando el endpoint esta realmente listo.
- Persistencia SQLite de sesiones, mensajes y trazas.

## Archivos de referencia
- Arquitectura: `docs/02_arquitectura/openclaw-control-plane.md`
- Operacion local: `docs/03_operacion/openclaw-workspace-local.md`
- Flujo escritorio edge: `docs/03_operacion/flujo-escritorio-orange-pi.md`
- Runtime compartido: `runtime/openclaw/openclaw_local/session_layer.py`
- Bot Matrix: `runtime/openclaw/openclaw_local/matrix_bot.py`
- Bot Telegram: `runtime/openclaw/openclaw_local/telegram_bot.py`
- Estado runtime: `runtime/openclaw/openclaw_local/runtime_status.py`
- API web: `runtime/openclaw/openclaw_local/web.py`

## Estado host real verificado el 2026-04-24
- `tesis-edge` mantiene `openclaw-telegram-bot.service` activo como canal secundario.
- `openclaw-matrix-bot.service` esta habilitado y activo contra un homeserver Conduit local privado en `127.0.0.1:6167`.
- La configuracion edge apunta a `OPENCLAW_DESKTOP_RUNTIME=llamacpp`.
- El endpoint `OPENCLAW_DESKTOP_RUNTIME_BASE_URL=http://127.0.0.1:21434` expone el `llama.cpp server` de la PC Windows via reverse tunnel.
- `pasarela estado` reporta `active_runtime=pc_native_llamacpp` y `runtime_status.llamacpp.ready=true`.
- El edge conserva `ollama_local` como fallback si el carril pesado deja de responder.
- El arranque Windows quedó persistido como tarea programada `\OpenClawLlamaCppServer` con `BootTrigger`, usuario `SYSTEM` y `RunLevel=HighestAvailable`.

## Cierre de validacion
- Suite local focalizada OpenClaw: `109 passed`.
- Wiki regenerada y validada.
- `python3 07_scripts/build_all.py` ejecutado con resultado `OK`.

## Pendientes host-real fuera del repo
- Confirmar el `BootTrigger` con una prueba de reinicio físico cuando sea operativo hacerlo.
- Rotar/custodiar tokens Matrix fuera de la salida conversacional y mantener `/etc/tesis-os/openclaw.env` como fuente privada de runtime.
- Evaluar hardening de Matrix remoto/E2EE antes de exponer clientes fuera de la red local.

_Última actualización: `2026-04-25`._
