# Espacio de Trabajo Local de OpenClaw

## Objetivo
Ofrecer una superficie híbrida `CLI + web + Matrix + Telegram` para operar `openclaw` con política `desktop-first`: la PC principal resuelve el carril pesado y el edge conserva continuidad 24/7.

## Flujo mínimo
1. Ejecutar `python runtime/openclaw/bin/openclaw_local.py doctor`.
2. Verificar nodos y proveedores efectivos con `pasarela estado`, `matrix estado`, `telegram estado`, `proveedor estado` y `presupuesto estado`.
3. Registrar una tarea con `tarea nueva` o evaluarla con `tarea enrutar`.
4. Correr `ejecutar --simulacion` para generar evidencia y, si corresponde, solicitud de aprobación.
5. Levantar la pasarela local con `pasarela servir` cuando existan dependencias web instaladas.
6. Operar sesiones por web local, CLI, Matrix o Telegram usando la misma `session-layer`.
7. Revisar aprobaciones pendientes y trazas con `/sessions`, `/traces/{id}` y la auditoría SQLite.

## Serena MCP en OpenClaw
- `OpenClaw` consume `serena-local` como capacidad auxiliar de contexto y gobernanza; no participa en el `provider_registry` ni reemplaza el ruteo de modelos.
- Cuando una tarea tiene `target_paths`, contexto documental, riesgo alto o modo académico, el CLI intenta usar Serena automáticamente.
- La salida JSON de `tarea nueva`, `tarea enrutar`, `ejecutar` y `academico ...` incluye un bloque `serena` con disponibilidad, herramientas invocadas, referencias recuperadas y resultado de preflight.
- Si Serena no está disponible, `OpenClaw` degrada solo en flujos de lectura o `--simulacion`; cuando Serena es obligatoria o la operación pretende mutar artefactos, el comando falla con estado explícito.
- Si `governance.preflight` devuelve `blocked`, el bloqueo se conserva en la salida y se anota también en el resumen de aprobación humana.
- Este adapter no vuelve accesible a Serena para cualquier chat externo por defecto; el host o runtime que quiera invocarlo debe registrar el MCP o consumir un bridge explicito.

## Configuración del adapter Serena
- `OPENCLAW_SERENA_ENABLED=1|0`: activa o desactiva la heurística automática.
- `OPENCLAW_SERENA_MODE=auto|required|off`: política por defecto del adapter interno.
- `OPENCLAW_SERENA_TRANSPORT=http|stdio`: transporte preferido del cliente interno.
- `OPENCLAW_SERENA_URL=http://127.0.0.1:8765/mcp`: endpoint HTTP cuando se usa `http`.
- `OPENCLAW_SERENA_SCRIPT=/ruta/a/07_scripts/serena_mcp.py`: script local cuando se usa `stdio`.
- `OPENCLAW_SERENA_PYTHON=/ruta/a/python`: intérprete para lanzar `serena_mcp.py`.
- `OPENCLAW_SERENA_TIMEOUT_MS=4000`: timeout por llamada.
- Por comando, `--modo-serena auto|required|off` permite exigir Serena, apagarla o dejar la heurística por defecto.
- Para diagnostico rapido del host local fuera de OpenClaw, usar `python 07_scripts/check_serena_access.py`.
- Default operativo recomendado en Orange Pi: `OPENCLAW_SERENA_ENABLED=1`, `OPENCLAW_SERENA_MODE=auto` y `OPENCLAW_SERENA_TRANSPORT=http`.
- `stdio` queda reservado como ruta diagnostica local y no como transporte normal del workspace.

## Flujos académicos v1
- `python runtime/openclaw/bin/openclaw_local.py academico estado-del-arte --id-tarea ... --archivo-entrada-json <archivo.json>`
- `python runtime/openclaw/bin/openclaw_local.py academico metodologia --id-tarea ... --archivo-entrada-json <archivo.json>`
- `python runtime/openclaw/bin/openclaw_local.py academico redaccion --id-tarea ... --archivo-entrada-json <archivo.json> --escribir-artefactos`
- `python runtime/openclaw/bin/openclaw_local.py academico exportar-propuesta --id-tarea ...`
- `python runtime/openclaw/bin/openclaw_local.py academico redaccion --id-tarea ... --archivo-entrada-json <archivo.json> --prefer-chatgpt-plus`

## ChatGPT Plus en OpenClaw
- `chatgpt_plus_web_assisted` es el carril web asistido para sesiones supervisadas por humano.
- Requiere `OPENCLAW_CHATGPT_PLUS_ENABLED=1` en el env del dominio académico y `OPENCLAW_WEB_ENABLED=1` en la superficie OpenClaw.
- Usa `--prefer-chatgpt-plus` cuando la tarea necesite priorizar ChatGPT Plus sobre otros proveedores web o locales.
- La salida de ruteo mantiene trazabilidad, costo estimado y gate humano cuando el modo web asistido se selecciona.
- Dependencias runtime: `runtime/openclaw/requirements-web.txt` instala `playwright`; el bootstrap intenta instalar Chromium administrado en `PLAYWRIGHT_BROWSERS_PATH=/var/lib/herramientas/openclaw/ms-playwright`.
- Preflight local: `python runtime/openclaw/bin/openclaw_local.py sesion-web estado`.
- Primer login supervisado: ejecutar en una sesión con navegador visible `OPENCLAW_WEB_SESSION_HEADLESS=0 python runtime/openclaw/bin/openclaw_local.py sesion-web login --timeout 900`, iniciar sesión manualmente en ChatGPT y cerrar cuando el perfil persistente quede autorizado.
- El perfil persistente vive fuera de Git en `OPENCLAW_WEB_SESSION_USER_DATA_DIR`; no se registran cookies, tokens, contraseñas ni exportes directos de ChatGPT en el repositorio.
- Para Telegram/chat, `chatgpt_plus_web_assisted` solo se usa cuando el mensaje lo pide explícitamente (`chatgpt`, `modelo premium`, `usa proveedor de IA no publicado`, `usa nube`) o cuando una tarea CLI pasa `--prefer-chatgpt-plus`; `OPENCLAW_CHATGPT_PLUS_ENABLED=1` no lo convierte en default.

## Gateway oficial OpenClaw
- La configuración oficial equivalente vive como plantilla sin secretos en `config/openclaw/openclaw.official.template.json`.
- La plantilla usa `models.providers.ollama`, `agents.defaults.maxConcurrent=1`, `contextTokens` reducido, `embeddedHarness.fallback=none` y `tools.deny=["group:web","browser"]` para no dar herramientas web a modelos pequeños.
- `openclaw-gateway.service` ejecuta el gateway Python local por defecto. El binario oficial `openclaw` solo se usa si `OPENCLAW_OFFICIAL_GATEWAY_ENABLED=1`, evitando instalaciones `npm` o sidecars durante el camino crítico del bot Telegram.
- Validación recomendada para el gateway oficial: `openclaw doctor`, `openclaw status --deep` y revisión de `~/.openclaw/openclaw.json` antes de habilitarlo en el edge.

## Session layer y API local
- La pasarela expone una `session-layer` común para `cli`, `web_local`, `matrix` y `telegram`.
- Endpoints operativos:
  - `GET /nodes`
  - `GET /providers`
  - `GET /sessions`
  - `POST /sessions`
  - `GET /sessions/{session_id}`
  - `POST /sessions/{session_id}/messages`
  - `POST /sessions/{session_id}/approve`
  - `GET /traces/{trace_id}`
- Cada sesión guarda `channel`, `target_node`, `provider_policy`, `premium_auto`, proveedor/modelo activos y mensajes persistidos.
- Los adaptadores de canal ya no deben implementar lógica propia de ruteo de modelos.

## Observabilidad local
- Log de servicio: `/var/log/openclaw/openclaw-gateway.log`
- Métricas de dominio: `/var/lib/node_exporter/textfile_collector/openclaw.prom`
- Scraping local vía `node_exporter` en `127.0.0.1:9100`
- `Prometheus` vive en `127.0.0.1:9090` y retiene 90 días en esta fase.

## Despliegue local en Orange Pi
- El entorno efectivo se instala en `/etc/tesis-os/openclaw.env`.
- Los secretos por dominio viven en `/etc/tesis-os/domains/`.
- El estado local vive en `/var/lib/herramientas/openclaw`.
- El cache local vive en `/var/cache/herramientas/openclaw`.
- Los logs operativos viven en `/var/log/openclaw`.
- El intercambio con otros dominios vive solo en `/srv/tesis/intercambio/openclaw`.
- El runtime principal es `Ollama`; la vía `RKLLM`/`RKNN-LLM` se instala como carril experimental secundario.
- La Orange Pi aloja `openclaw` como nodo asistivo local-first; no sustituye al escritorio como superficie principal de investigación documental.
- No usar `OPENCLAW_PROFILE=academico` como habilitación amplia: el comportamiento efectivo depende del dominio de la tarea, secretos disponibles, presupuesto y riesgo.
- Orden operativo por defecto para el asistente científico:
  1. `local`
  2. `ollama_local`
  3. `pc_native_llamacpp` para tareas academicas/profesionales pesadas cuando la PC este disponible
  4. nube academica/profesional solo con `OPENCLAW_CLOUD_ENABLED=1` o permiso explicito por tarea
  5. `rknn_llm_experimental` solo tras benchmark exitoso y decisión explícita
- En la fase local-first actual, `OPENCLAW_CLOUD_ENABLED=0` es el valor esperado.
- `OPENCLAW_DESKTOP_RUNTIME=llamacpp` y `OPENCLAW_DESKTOP_RUNTIME_BASE_URL` activan el backend pesado de la PC.
- El servidor `llama.cpp` vive en la PC en `OPENCLAW_LLAMACPP_BIND_PORT` (por defecto `21435`) y el túnel expone ese servicio en `127.0.0.1:21434` del edge.
- `OPENCLAW_DESKTOP_COMPUTE_BASE_URL` se conserva solo como compatibilidad transitoria; la ruta preferida es `OPENCLAW_DESKTOP_RUNTIME_BASE_URL`.
- `OPENCLAW_DESKTOP_COMPUTE_AUTH_MODE=ssh_tunnel` indica que la barrera de autenticacion v1 es SSH con llave dedicada y listener en localhost.
- `OPENCLAW_NPU_AUTO_PROMOTE=0` debe mantenerse en la instalación inicial; la NPU no se promociona automáticamente aunque el benchmark sea mejor.
- `pasarela preflight` debe pasar antes de habilitar `openclaw-gateway.service`.

## Matrix como canal remoto principal
- `OPENCLAW_MATRIX_ENABLED=1` habilita el bot/adaptador Matrix.
- Variables mínimas:
  - `OPENCLAW_MATRIX_HOMESERVER`
  - `OPENCLAW_MATRIX_ACCESS_TOKEN`
  - `OPENCLAW_MATRIX_USER_ID`
  - `OPENCLAW_MATRIX_ROOM_IDS`
- Comandos operativos:
  - `python runtime/openclaw/bin/openclaw_local.py matrix estado`
  - `python runtime/openclaw/bin/openclaw_local.py matrix polling --once`
  - `python runtime/openclaw/bin/openclaw_local.py matrix procesar --room-id '!room:id' --sender '@user:server' --texto '/estado'`
- El homeserver Matrix se aloja inicialmente en `tesis-edge`; la migración a VPS debe reusar el mismo contrato de bot/configuración.

## Telegram como canal secundario
- `openclaw-telegram-bot.service` se mantiene para compatibilidad, fallback y notificaciones.
- Telegram ya no es el plano principal de control; comparte la misma `session-layer` y persiste sesiones/mensajes igual que Matrix.
- `dispatch_test_notification` y los avisos de readiness describen el canal realmente configurado; no deben usarse como sustituto del estado de Matrix.

## Bot Telegram local-first
- `openclaw-telegram-bot.service` corre separado de `openclaw-gateway.service` y usa polling local de Telegram; no abre puertos públicos.
- Solo `OPENCLAW_TELEGRAM_CHAT_ID` queda autorizado por defecto; mensajes de otros chats se ignoran y se auditan en SQLite.
- Comandos disponibles: `/start`, `/estado`, `/modelos`, `/chat <texto>`, `/investiga <pregunta>`, `/herramienta <accion>` y `/aprobar [id]`.
- Modo seguro: `/herramienta` solo ejecuta consultas read-only; acciones mutantes como reiniciar, editar, instalar, commit o push generan una aprobación pendiente y no se ejecutan desde Telegram.
- Aprobación simplificada: si una propuesta APR reciente es la única pendiente en el chat, `si`, `valido`, `apruebo`, `ejecuta` o `hazlo` aprueban esa APR. Acciones críticas siguen exigiendo validación humana interna no pública explícito.
- La herramienta allowlist de imagen puede ejecutarse tras aprobación simplificada y usa `OPENCLAW_IMAGE_BACKEND=comfyui`, `OPENCLAW_COMFYUI_BASE_URL` y `OPENCLAW_IMAGE_OUTPUT_DIR`. En la Orange Pi el valor operativo esperado es `OPENCLAW_COMFYUI_BASE_URL=http://127.0.0.1:28000`, servido por túnel SSH hacia ComfyUI en la PC. Si ComfyUI no responde o falta `OPENCLAW_COMFYUI_WORKFLOW_JSON`, el bot informa el bloqueo operativo sin crear bucles de APR.
- Chat ligero prefiere modelos Qwen3 visibles (`qwen3:4b` en edge o `qwen3:14b` por PC si la política lo permite); el fallback mínimo y seguro en edge sigue siendo `OPENCLAW_TELEGRAM_FALLBACK_MODEL=qwen3:4b`.
- El router Telegram usa SLA por perfil: simple `OPENCLAW_CHAT_SIMPLE_TIMEOUT=8`, factual `OPENCLAW_CHAT_FACTUAL_TIMEOUT=20`, pesado `OPENCLAW_CHAT_HEAVY_TIMEOUT=90`.
- La concurrencia queda limitada por `OPENCLAW_TELEGRAM_MAX_WORKERS`, `OPENCLAW_EDGE_MAX_CONCURRENT` y `OPENCLAW_DESKTOP_MAX_CONCURRENT`; cada `chat_id` se procesa en serie.
- El arranque del bot precalienta modelos con `OPENCLAW_MODEL_WARMUP_ON_START=1`, `OPENCLAW_WARMUP_MODELS` y `OPENCLAW_DESKTOP_WARMUP_MODELS`; `/api/ps` se consulta antes de priorizar modelos calientes.
- Saludos, factual canónico mínimo y estado/runtime se resuelven por regla local auditada (`deterministic_local`) para no gastar 8-20 s en carga de LLM.
- `qwen2.5:0.5b` permanece solo en evidencia histórica de benchmark; no forma parte de defaults activos ni de fallbacks semánticos.
- Cada turno registra en SQLite `trace_id`, backend, modelo, SLA, tamaño de prompt, errores por candidato y política de fallback.
- Investigación pesada usa `pc_native_llamacpp` por `OPENCLAW_DESKTOP_RUNTIME_BASE_URL=http://127.0.0.1:21434` y modelo `OPENCLAW_DESKTOP_RUNTIME_MODEL`; si falla el túnel, degrada explícitamente a edge.
- El túnel PC -> edge se mantiene con `openclaw-desktop-tunnel.service` en la PC: `127.0.0.1:21434` del edge apunta al `llama.cpp server` de Windows en `172.17.176.1:21435` cuando `OPENCLAW_DESKTOP_TUNNEL_LOCAL_BIND=172.17.176.1:21435`, y `127.0.0.1:28000` del edge apunta a ComfyUI local `127.0.0.1:8000` cuando `OPENCLAW_DESKTOP_TUNNEL_COMFY_ENABLED=1`.
- El hardening SSH del edge debe permitir ambos listeners remotos para `tesisai`: `PermitListen 127.0.0.1:21434 127.0.0.1:28000`.
- Recuperación del túnel PC: ejecutar `systemctl --user restart openclaw-desktop-tunnel.service` en el escritorio y comprobar desde `tesis-edge` con `curl -s http://127.0.0.1:21434/health` y `curl -s http://127.0.0.1:28000/system_stats`.
- Si ComfyUI está instalado en la PC pero su API no escucha en `127.0.0.1:8000`, el edge responderá `comfyui_unreachable`; abrir ComfyUI o ajustar `OPENCLAW_DESKTOP_TUNNEL_COMFY_LOCAL_BIND` a un endpoint alcanzable desde WSL corrige el enlace sin cambiar el bot.

## Runtime pesado en la PC
- Wrapper Windows:
  - `runtime/openclaw/wrappers/openclaw-llamacpp-server.cmd`
  - `runtime/openclaw/wrappers/openclaw-llamacpp-server.ps1`
- Config mínima:
  - `OPENCLAW_DESKTOP_RUNTIME=llamacpp`
  - `OPENCLAW_DESKTOP_RUNTIME_BASE_URL=http://127.0.0.1:21434`
  - `OPENCLAW_DESKTOP_RUNTIME_MODEL=<modelo.gguf o alias operativo>`
  - `OPENCLAW_DESKTOP_NATIVE_HOST=windows`
- `OPENCLAW_LLAMACPP_MODEL_NAME=mistral-nemo:12b` permite derivar el blob actual desde Ollama si no se especifica `OPENCLAW_LLAMACPP_MODEL_PATH`.
- `OPENCLAW_LLAMACPP_BIND_PORT=21435` separa el puerto local del servidor Windows del puerto remoto expuesto en el edge.
- La persistencia host-real vive en la tarea programada Windows `\OpenClawLlamaCppServer`, con `BootTrigger`, usuario `SYSTEM` y `RunLevel=HighestAvailable`; no depende del script Startup de usuario.
- El runtime pesado vive en host nativo de la PC; OpenClaw solo consume su HTTP health/generate y lo trata como `pc_native_llamacpp`.

## Selección local de modelos medida 2026-04-21
- Evidencia PC principal post-WSL: `historial interno no público/openclaw_max_model_bench_pc_post_wsl_20260421.json`.
- Evidencia PC comparativa pre-WSL: `historial interno no público/openclaw_max_model_bench_pc_20260421.json`.
- Evidencia Orange Pi CPU: `historial interno no público/openclaw_max_model_bench_edge_20260421.json`.
- PC `pc_native_llamacpp`: usar `mistral-nemo:12b` como modelo pesado diario; usar `qwen2.5-coder:14b` para tareas de código; tratar `qwen3:14b` y `phi4:14b` como techo experimental/agresivo.
- Orange Pi por Ollama CPU: mantener `qwen3:4b` como fallback mínimo y candidato diario de borde; tratar `qwen2.5-coder:7b` como techo experimental controlado.
- Mantener Qwen 3 en el camino por defecto del borde para alinear el comportamiento con la preferencia operativa actual.
- La medición PC posterior a `wsl --shutdown` aplicó `.wslconfig`: WSL pasó a 11.68 GiB visibles y 16 GiB de swap; la VRAM base bajó a ~1271 MiB usados antes de cargar modelos.
- RKNN/RKLLM sigue en carril experimental: hay `librknnrt.so`, `librkllmrt.so` y `rknn_server`, pero no se observó `/dev/rknpu*` ni demo RKLLM preconvertido listo. No promover NPU hasta tener device/permisos/modelo `.rkllm` y benchmark TTFT/tokens/s/memoria.

## Aislamiento T-030
- `openclaw-gateway.service` corre bajo `openclaw:openclaw`.
- `openclaw` no comparte SQLite, cache ni logs con `sistema_tesis` ni `edge_iot`.
- `openclaw` no expone API interdominio; solo escucha en `localhost`.
- Toda entrega a `sistema_tesis` sale por drafts, spool local o CLI explícita.

## Secretos y presupuesto
- `python runtime/openclaw/bin/openclaw_local.py secretos estado` reporta dominios, proveedores permitidos y faltantes sin exponer valores.
- `python runtime/openclaw/bin/openclaw_local.py presupuesto estado` consolida snapshot global y gasto local de `openclaw`.
- `python runtime/openclaw/bin/openclaw_local.py presupuesto simular --dominio academico --proveedor gemini_api` permite validar degradación antes de ejecutar una tarea.
- Las sesiones `gemini_web_assisted` y `chatgpt_plus_web_assisted` se clasifican como supervisadas por humano y usan costo estimado/manual.
- `academico` y `profesional` son dominios híbridos controlados; `personal`, `edge` y `administrativo` permanecen local/offline.
- Antes de habilitar nube en uso real por SSH, validar baseline local con `doctor`, `proveedor estado`, `pasarela preflight` y `pasarela estado`.
- `OPENCLAW_PROVIDER_POLICY=hybrid_controlled` y `OPENCLAW_PREMIUM_AUTO=1` son los defaults esperados en esta fase.

## Gate humano
- Toda mutación de estado, publicación o cambio de arquitectura exige aprobación humana.
- La salida de `openclaw` se considera propuesta operativa hasta revisión humana.
- La evidencia fuente y el `Step ID` se preservan fuera de la cola automática.

_Última actualización: `2026-04-25`._
