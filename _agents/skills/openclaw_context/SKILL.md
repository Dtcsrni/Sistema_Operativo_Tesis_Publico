---
name: openclaw_context
description: >
  Contexto compacto de arquitectura OpenClaw para trabajo agéntico eficiente.
  Úsala antes de abrir archivos del repo para obtener el mapa de módulos,
  convenciones de prompts y variables de entorno clave.
  Ahorra ~50-60% de tokens frente a explorar el repo desde cero.
version: "1.1"
applies_to:
  - openai_agents
  - vscode_agents
  - antigravity
---

# Skill: openclaw_context

## Cuándo usar esta skill

Antes de:
- Editar cualquier archivo en `runtime/openclaw/openclaw_local/`
- Agregar nuevas funciones al bot de Telegram
- Modificar routing, políticas o presupuesto de tokens
- Debuggear comportamientos de inferencia o rutas de fallback

## Mapa de módulos clave

```
runtime/openclaw/openclaw_local/
├── telegram_bot.py      # Bot principal (~4100 líneas). Punto de entrada de todo.
│                        # Funciones clave: handle_update, dispatch_command,
│                        #   _chat_response, _research_response, _format_research_reply
├── engine.py            # Router de tareas. route_task() → ProviderDecision
├── adaptive_router.py   # Routing adaptativo basado en benchmarks históricos
├── budgeting.py         # Presupuesto de tokens. simulate_budget_request()
├── policies.py          # Carga manifests YAML: dominios, proveedores, presupuesto
├── persona.py           # [NUEVO] Tono adaptativo. build_system_block(kind, complexity)
├── response_cache.py    # [NUEVO] Caché TTL. ResponseCache(store).get/put()
├── sources.py           # Gestión de referencias APA, DOI, Crossref
├── storage.py           # OpenClawStore: SQLite + caché de contexto
├── session_layer.py     # Canales externos (Matrix, canal)
├── runtime_status.py    # Estado del sistema, modelos disponibles
├── audio_engine.py      # TTS/STT para mensajes de voz
└── contracts.py         # Dataclasses: TaskEnvelope, ProviderDecision, etc.

manifests/               # Configuración declarativa (YAML)
├── domain_boundaries.yaml
├── backend_routing_policy.yaml
├── openclaw_provider_registry.yaml
└── openclaw_budget_policy.yaml

runtime/openclaw/policies/  # Políticas Markdown de dominio
_agents/skills/             # Skills de agente (esta carpeta)
```

## Convenciones de prompts (NO duplicar en código)

- **System block**: siempre desde `persona.build_system_block(request_kind, complexity)`
- **Síntesis**: siempre desde `persona.build_synthesis_system_block()`
- **Razonamiento avanzado**: `persona.reasoning_instructions(request_kind, complexity)`
- Nunca copiar bloques de instrucciones entre funciones

## Flujo de una respuesta /chat

```
mensaje → _chat_request_profile() → request_kind, complexity
        → ResponseCache.get() → [HIT] devuelve directamente
        → [MISS] _safe_prompt() via persona.build_system_block()
        → ollama_generate() con modelo seleccionado por _select_chat_model()
        → [complexity=medium/high] _select_best_synthesis_model() → ollama_generate()
        → _format_chat_reply() → send_message()
        → ResponseCache.put()
```

## Flujo de una respuesta /investiga

```
query → send_message(estado) × 3
      → web_search() → resultados
      → _research_prompt() → ollama_generate() [análisis estructurado, 180s]
      → _select_best_synthesis_model() → _build_synthesis_prompt()
      → ollama_generate() [síntesis prose, 120s]
      → _format_research_reply(is_synthesized=True) → send_message()
```

## Variables de entorno críticas

| Variable | Descripción | Default |
|----------|-------------|---------|
| `OPENCLAW_DESKTOP_COMPUTE_ENABLED` | Habilitar PC como nodo de inferencia | `true` |
| `OPENCLAW_DESKTOP_COMPUTE_BASE_URL` | URL del modelo desktop | `http://PC:11434` |
| `OPENCLAW_DESKTOP_RUNTIME_MODEL` | Modelo principal en desktop | `mistral-nemo:12b` |
| `OPENCLAW_EDGE_OLLAMA_BASE_URL` | URL Ollama edge | `http://127.0.0.1:11434` |
| `OPENCLAW_TELEGRAM_EDGE_MODEL` | Modelo edge por defecto | `qwen3:4b` |
| `OPENCLAW_CHAT_SYNTHESIS_ENABLED` | Síntesis universal en /chat | `1` |
| `OPENCLAW_RESEARCH_SYNTHESIS_TIMEOUT` | Timeout síntesis investigación | `120` |
| `OPENCLAW_ECONOMY_MODE` | Forzar modo economía | `0` |
| `OPENCLAW_CHAT_HEAVY_MAX_TOKENS` | Tokens máx para heavy chat | `900` |

## Patrones establecidos que NO cambiar

1. `TypingHeartbeat` envía `typing` cada 4.5s durante inferencia larga
2. `_elapsed_ms(t0)` calcula latencia en ms desde `time.perf_counter()`
3. `_env_int(name, default, minimum, maximum)` lee env vars numéricas con validación
4. `_env_flag(name, default)` lee env vars booleanas
5. Todo texto HTML de Telegram escapa `&`, `<`, `>` antes de enviar
6. Las respuestas de investigación siempre terminan con el aviso de validación académica

## Archivos protegidos

Archivos con `<!-- SISTEMA_TESIS:PROTEGIDO -->` requieren backup `.bak` antes de editar
y registro en el ledger (`log_sesiones_trabajo_registradas.md`).

## Patrón de verificación post-edición

```powershell
python -m py_compile runtime/openclaw/openclaw_local/telegram_bot.py
python 07_scripts/build_all.py
```

_Última actualización: `2026-04-29`._
