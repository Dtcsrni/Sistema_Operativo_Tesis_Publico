---
name: vscode_openclaw
description: >
  Guia de trabajo agentico en VS Code para el proyecto OpenClaw.
  Cubre convenciones de edicion, atajos de verificacion y workflows
  para editar telegram_bot.py y modulos relacionados sin romper el sistema.
  Incluye referencias al build_runner modular y flujo Hermes.
version: "2.0"
applies_to:
  - vscode_agents
  - antigravity
agnostic: true
---

# Skill: vscode_openclaw

## Estructura de workspace

El workspace VS Code esta en ` ruta local no pública `.
Configuracion MCP en `.vscode/mcp.json` — verificar disponibilidad de Serena antes de usar filesystem raw.

## Modulos OpenClaw (runtime/openclaw/openclaw_local/)

| Modulo | Proposito | Cuando editar |
|--------|----------|---------------|
| `telegram_bot.py` | Bot principal (~4400 lineas) | Comandos, dispatch, flujo Telegram |
| `persona.py` | Tono adaptativo + ChatML Hermes | Ajustar instrucciones de sistema |
| `adaptive_router.py` | Router de modelos/nodos | Cambiar prioridad de modelos |
| `det_scripts.py` | Calculo deterministico OS-side | Añadir conversiones/estadisticas |
| `rolling_summary.py` | Compresion de memoria background | Ajustar trigger y modelos |
| `reflective_phase.py` | Propuesta de skills automatica | Umbral de deteccion de patrones |
| `response_cache.py` | Cache TTL por tipo de consulta | Politica de cacheo |
| `engine.py` | Motor de inferencia y routing | Flujo de inferencia |
| `policies.py` | Politicas de dominio y provider | Politicas de calidad |

## Convenciones de edicion en telegram_bot.py

El archivo tiene ~4400 lineas. Antes de editar:

1. **Leer `openclaw_context` skill** para el mapa de modulos
2. Buscar la funcion objetivo con `Select-String` para obtener linea exacta:
   ```powershell
   Select-String -Path runtime/openclaw/openclaw_local/telegram_bot.py -Pattern "dispatch_command" | Select-Object LineNumber, Line
   ```
3. Usar edicion quirurgica (`multi_replace_file_content`) — NUNCA reemplazar el archivo completo
4. Verificar sintaxis despues de CADA edicion:
   ```powershell
   python -m py_compile runtime/openclaw/openclaw_local/telegram_bot.py
   ```

## Imports del bot (lineas 26-35)

Los modulos nuevos se importan en el bloque de imports relativos:
```python
from . import reflective_phase as _reflective_mod
from . import rolling_summary as _rolling_summary_mod
from .persona import build_system_block, build_hermes_system_block, get_tone
from .response_cache import ResponseCache, cache_hit_tag, is_volatile
```

## Puntos de extension documentados

| Extension | Donde insertar | Funcion de referencia |
|-----------|---------------|----------------------|
| Nuevo comando Telegram | `dispatch_command()` L1768 | Buscar `elif command ==` |
| Nueva respuesta de sistema | `_tool_response()` | Buscar `READ_ONLY_TOOLS` |
| Nuevo tipo de routing | `adaptive_router.py` | Buscar `_preferred_provider_order` |
| Nueva politica de calidad | `policies.py` | Buscar `load_domain_policies` |
| Nueva skill de agente | `_agents/skills/<nombre>/SKILL.md` | Ver build_runner SKILL |
| Nuevo calculo deterministico | `det_scripts.py::dispatch()` | Buscar `def dispatch` |

## Sistema de Build (build_runner)

Ver skill `build_runner` para documentacion completa. Comandos clave:

```powershell
# Post-edicion de OpenClaw (rapido, solo pasos relevantes)
python 07_scripts/build_all.py --group openclaw

# Post-edicion de ledger/bitacora
python 07_scripts/build_all.py --tag ledger --tag audit

# Build completo (antes de cerrar sesion)
python 07_scripts/build_all.py

# Ver que se ejecutaria
python 07_scripts/build_all.py --dry-run --group openclaw
```

## Flujo Hermes 3 (D2=A, condicional)

```powershell
# 1. Descargar modelos
.\07_scripts\pull_hermes_models.ps1

# 2. Ejecutar benchmark comparativo
python 07_scripts/run_pc_benchmark_hermes.py --baseline qwen3:4b

# 3. Si benchmark es positivo, activar
$env:OPENCLAW_HERMES_ENABLED = "1"

# 4. Verificar router actualizado
python 07_scripts/build_all.py --group openclaw
```

Ver `00_sistema_tesis/decisiones/2026-04-29_DEC-0026_politica_migracion_hermes.md`.

## Patrones prohibidos en telegram_bot.py

- No copiar bloques de instrucciones de sistema — usar `persona.build_system_block()`
- No hardcodear nombres de modelos — usar `os.getenv("OPENCLAW_...")`
- No enviar respuestas sin escapar HTML — verificar `<`, `>`, `&`
- No marcar tareas como validadas sin Step ID — ver AGENTS.md
- No editar archivos `<!-- SISTEMA_TESIS:PROTEGIDO -->` sin backup `.bak`
- No importar `telegram_bot` desde modulos de soporte (import circular)

## Workflow de verificacion post-edicion

```powershell
# 1. Sintaxis
python -m py_compile runtime/openclaw/openclaw_local/telegram_bot.py

# 2. Test suite (rapido, ~8s)
python 07_scripts/test_openclaw_suite.py

# 3. Build parcial grupo openclaw
python 07_scripts/build_all.py --group openclaw

# 4. Build completo (antes de cierre de sesion)
python 07_scripts/build_all.py
```

## Variables de entorno para desarrollo local

```
OPENCLAW_DESKTOP_COMPUTE_ENABLED=true
OPENCLAW_DESKTOP_COMPUTE_BASE_URL=http://localhost:11434
OPENCLAW_TELEGRAM_EDGE_MODEL=qwen3:4b
OPENCLAW_CHAT_SYNTHESIS_ENABLED=1
OPENCLAW_ECONOMY_MODE=0
OPENCLAW_HERMES_ENABLED=0          # Cambiar a 1 solo tras benchmark exitoso
OPENCLAW_ADAPTIVE_ROUTING_ENABLED=1
OPENCLAW_SUMMARY_MODELS=qwen2.5:0.5b
```

## Comandos Telegram disponibles

| Comando | Descripcion |
|---------|-------------|
| `/ayuda` | Lista todos los comandos |
| `/chat <texto>` | Chat normal adaptativo |
| `/investiga <tema>` | Research con busqueda web |
| `/herramienta <accion>` | Estado, modelos, presupuesto |
| `/memoria` | Contexto de sesion actual |
| `/aprobar <id>` | Aprobar accion pendiente |
| `/skills_pendientes` | Skills propuestas por reflective_phase |
| `/hora` | Hora actual (deterministico) |

## Agnosticismo de proveedor

Esta skill funciona con cualquier agente compatible con el formato SKILL.md:
- proveedor de IA no publicado Agents SDK (tool use)
- VS Code Copilot (con MCP)
- Antigravity / Gemini (filesystem tools)

No asumas herramientas especificas de un proveedor. Usa siempre las APIs
declaradas en `contracts.py` y los modulos de `openclaw_local/`.

_Última actualización: `2026-05-15`._
