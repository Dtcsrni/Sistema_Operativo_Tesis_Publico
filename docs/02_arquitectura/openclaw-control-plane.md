# OpenClaw Control Plane PC-first

## Propósito
`openclaw` opera como plano de control asistivo de `tesis-os`. No sustituye el canon ni los scripts oficiales del sistema de tesis.

## Subsistemas
- `control-plane`: CLI local, API del workspace y panel web.
- `session-layer`: sesiones agénticas, identidad de origen, política de proveedor y trazas por turno.
- `channel-adapters`: `web_local`, `cli`, `matrix` y `telegram`.
- `policy-engine`: ruteo por dominio, riesgo, sensibilidad y costo.
- `evidence-engine`: persistencia local auditable con hashes SHA-256.
- `provider-gateway`: adaptadores para local, web asistida y APIs formales.
- `node-executors`: `pc_native`, `edge_local` y `cloud_provider`.
- `hardware-broker`: lectura controlada del host y de las capacidades de Orange Pi.

## Límites duros
- `openclaw` no valida por sí mismo decisiones ni validación humana interna no pública.
- `openclaw` no publica directamente a superficies públicas.
- `edge` y `administrativo` quedan local-first y sin nube por defecto.
- La nube queda deshabilitada por defecto para todos los dominios; solo se usa con `OPENCLAW_CLOUD_ENABLED=1` o permiso explícito por tarea.
- El fallo de `openclaw` no detiene `tesis-os`.

## Persistencia
- Estado operativo local: SQLite.
- Fuente de verdad canónica: archivos versionados del repositorio.
- Evidencia: registros locales hashables y exportables para integración posterior al ledger en modo draft.
- Namespace operativo Orange Pi: `/var/lib/herramientas/openclaw`, `/var/cache/herramientas/openclaw`, `/var/log/openclaw`.
- Entorno efectivo de despliegue: `/etc/tesis-os/openclaw.env`.
- Secretos por dominio: `/etc/tesis-os/domains/<dominio>.env`.

## Interfaz inicial
- CLI: `doctor`, `tarea nueva`, `tarea enrutar`, `ejecutar --simulacion`, `aprobar`, `auditar`, `sesion cerrar`, `proveedor estado`.
- Web local: tablero de tareas, aprobaciones, costos, trazabilidad y estado del host.
- API local de sesiones:
  - `POST /sessions`
  - `POST /sessions/{id}/messages`
  - `GET /sessions/{id}`
  - `GET /nodes`
  - `GET /providers`
  - `POST /sessions/{id}/approve`
  - `GET /traces/{id}`
- CLI académica: `academico estado-del-arte`, `academico metodologia`, `academico redaccion`, `academico exportar-propuesta`.
- CLI de despliegue local: `proveedor medir`, `pasarela preflight`, `pasarela estado`.
- CLI de secretos y presupuesto: `secretos estado`, `presupuesto estado`, `presupuesto simular`.
- CLI de canales remotos: `matrix estado`, `matrix procesar`, `matrix polling`, `telegram estado`, `telegram procesar`.

## Proveedores v1
- Línea 1: `local` y `ollama_local`.
- Línea 2 local pesada: `pc_native_llamacpp` como runtime principal en la PC con `llama.cpp server`.
- Compatibilidad transitoria: `desktop_compute` permanece como alias operativo mientras las rutas antiguas terminan de migrar.
- Línea 3 experimental edge: `rknn_llm_experimental`.
- Nube API formal opcional: `groq_api`, `gemini_api`, `openai_api`.
- Web asistida supervisada opcional: `gemini_web_assisted`, `chatgpt_plus_web_assisted`.
- Las sesiones web asistidas se clasifican como `human_supervised_web_session` y no como automatización ciega.

## Ruteo PC pesado / Orange Pi edge
- `edge`, `administrativo` y `personal`: permanecen en `local`.
- `academico` de alta complejidad, con citas, estado del arte, metodologia, redaccion, RAG, sintesis larga o comparacion de literatura: prefiere `pc_native_llamacpp`.
- `profesional` de alta complejidad o riesgo alto: prefiere `pc_native_llamacpp`.
- Resumenes cortos y tareas ligeras: `local` u `ollama_local`.
- `rknn_llm_experimental`: solo entra si la tarea solicita NPU o existe aprobacion/benchmark explicito.
- Si la PC pesada no esta disponible, la cadena de degradacion vuelve a `ollama_local`, `local`, `offline` y `manual` antes de bloquear el sistema base.

## Capas de acceso y sesiones
- Los adaptadores de canal no deciden modelos ni proveedores; solo autentican, normalizan comandos y delegan en la `session-layer`.
- `SessionEnvelope` preserva `session_id`, `channel`, `operator_id`, `target_node`, `provider_policy`, `premium_auto`, `current_provider` y `current_model`.
- `SessionMessage` conserva cada turno de entrada/salida con `trace_id`, rol, contenido resumido y metadatos de fallback.
- `telegram_bot.py` deja de concentrar el ruteo; `matrix_bot.py`, CLI y web consumen el mismo contrato de sesión.

## Canales remotos
- Superficie principal remota: `Matrix` soberano con salas privadas y bot dedicado.
- Despliegue inicial: homeserver y bot Matrix en `tesis-edge`.
- Ruta futura: migración del homeserver Matrix a VPS sin rehacer OpenClaw; la identidad y configuración deben ser portables.
- `Telegram` queda como canal secundario de notificación, compatibilidad y fallback operativo.

## Politica de proveedor
- `local_only`: fuerza ejecución en `pc_native` o `edge_local`, sin nube.
- `hybrid_controlled`: default del sistema; prioriza local y solo habilita nube si la política de dominio lo permite.
- `cloud_allowed`: la sesión puede usar `openai_api`, `gemini_api` o `groq_api`.
- `premium_auto=true`: la nube entra automáticamente solo en tareas premium o cuando el operador lo permite explícitamente.
- `chatgpt_plus_web_assisted` y `gemini_web_assisted` siguen siendo carriles supervisados por humano, nunca default silencioso.

## Secretos por dominio
- `personal`: solo local, sin nube.
- `profesional`: `pc_native_llamacpp` sin secreto; `groq_api` y `openai_api` solo si se habilita nube.
- `academico`: `pc_native_llamacpp` sin secreto; `groq_api`, `gemini_api`, `openai_api` y carriles web asistidos solo si se habilita nube.
- `edge` y `administrativo`: sin nube por default.
- El `secret-resolver` solo busca rutas conocidas y nunca imprime valores.

## Presupuesto y degradación
- El presupuesto global sigue en `00_sistema_tesis/config/token_budget.json`.
- `openclaw` agrega política por dominio y ledger local complementario por proveedor.
- Si se agota el dominio, la nube se degrada a local/offline/manual aunque exista remanente global.
- Si se agota el global, toda nube queda bloqueada.

## Despliegue Orange Pi 5 Plus
- Baseline objetivo: Orange Pi 5 Plus `8 GB` con Debian 12 oficial.
- Identidad de servicio: `tesis:tesis`.
- Runtime principal local: `Ollama`.
- Canal remoto principal: `Matrix`.
- Ruta NPU secundaria: `RKLLM`/`RKNN-LLM` instalada desde bootstrap pero marcada como experimental.
- `openclaw` no reemplaza el sistema base; si el gateway, Ollama o la vía NPU fallan, `tesis-os` debe seguir operando.

## Despliegue PC principal
- Runtime pesado principal: `llama.cpp server` en host nativo de la PC.
- El endpoint operativo se publica como `OPENCLAW_DESKTOP_RUNTIME_BASE_URL`.
- `OPENCLAW_DESKTOP_RUNTIME=llamacpp` selecciona `pc_native_llamacpp` como proveedor pesado preferido.
- La sesión de desarrollo actual puede seguir en WSL o tooling local, pero el cómputo pesado vive fuera de ese runtime cuando la GPU/latencia lo requieran.

## Casos de uso académicos v1
- `estado_del_arte`: triage de literatura, matriz de literatura, matriz de afirmaciones y nota crítica de contraste.
- `metodologia`: ficha de estudio, matriz de exploración, nota metodológica y propuesta de decisión o pendiente.
- `redaccion_tesis`: borrador Markdown trazable y fragmento LaTeX derivado desde la misma estructura de párrafos.

## Contratos académicos
- `AcademicWorkPacket`: paquete común con `mode`, `question`, `scope`, `sources`, `claims`, `outputs` y `traceability_links`.
- `LiteratureRecord`: contrato alineado a la matriz de literatura del repositorio.
- `ClaimRecord`: afirmación clasificada con verificación, fuentes e impacto sobre la tesis.
- `WritingDraft`: borrador paralelo Markdown/LaTeX para secciones de tesis.

## Promoción a validación humana
- `openclaw` puede exportar `openclaw_proposal` al canon.
- `openclaw` puede preparar un paquete técnico de validación con pregunta crítica, `session_id`, `step_id` sugerido y comandos canónicos.
- La promoción final a validación humana interna no pública ocurre únicamente mediante:
  - evidencia fuente registrada (`conversation_source_registered`),
  - coincidencia exacta entre `quoted_text` y `confirmation_text`,
  - ejecución explícita de `tesis.py proposal finalize-openclaw`.

_Última actualización: `2026-04-25`._
