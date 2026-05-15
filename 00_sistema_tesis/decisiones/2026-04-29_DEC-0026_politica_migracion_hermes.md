<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0026 | 2026-04-29 | v1.0 | APROBADO -->

---
# Política de Migración Hermes 3 (hermes3:8b)
# DEC-0026 | 2026-04-29
# Tesista: Erick Renato Vega Ceron
# Estado: PROPUESTA EXPERIMENTAL — pendiente de benchmark (D2=A)
---

# Política de Coexistencia OpenClaw + Hermes 3

## Principio rector

**OpenClaw es la capa de infraestructura. Hermes 3 es un motor de inferencia.**
No son alternativas: coexisten con roles distintos.

```
Usuario Telegram
      |
  telegram_bot.py  (OpenClaw: trazabilidad, routing, soberania)
      |
  adaptive_router.py  (selecciona modelo segun benchmark y contexto)
      |
  ┌───────────────────────────────┐
  │  Edge (Ollama CPU)            │  <- comandos rapidos, rolling summary
  │  qwen2.5:0.5b | qwen3:4b     │
  └───────────────────────────────┘
  ┌───────────────────────────────┐
  │  PC (Ollama CUDA)             │  <- sintesis heavy, research academico
  │  hermes3:8b [si D2=A]         │
  │  mistral-nemo:12b [fallback]  │
  └───────────────────────────────┘
```

## Condición de activación (D2=A)

Hermes 3 se activa como modelo principal de síntesis solo si:

1. `python 07_scripts/run_pc_benchmark_hermes.py` retorna `activate_recommended: true`
   (Hermes supera al baseline en >= 2/3 de categorias de evaluacion)
2. La variable de entorno `OPENCLAW_HERMES_ENABLED=1` está definida.

Sin ambas condiciones, el router continúa usando el modelo base actual.

## Asignación de flujos por hardware

| Tarea | Hardware | Modelo | Criterio |
|-------|---------|--------|---------|
| Rolling summary | Edge CPU | `qwen2.5:0.5b` | ~15 TPS, 397MB |
| Chat rápido / comandos | Edge CPU | `qwen3:4b` | ~5.4 TPS, 2.5GB |
| Síntesis académica | PC CUDA | `hermes3:8b` (si D2=A) | 8GB VRAM |
| Código técnico | PC CUDA | `qwen2.5-coder:7b` o `hermes3:8b` | 8GB VRAM |
| Fallback síntesis | PC CPU | `qwen3:4b` | Lento pero disponible |
| Det_scripts / caché | Edge CPU | Sin LLM | 0ms latencia |

## Formato ChatML de Hermes 3

Hermes 3 está entrenado nativamente con ChatML. El campo `system` del payload
Ollama se inyecta entre `<|im_start|>system` y `<|im_end|>`.

```python
# Uso correcto en telegram_bot.py / engine.py:
from openclaw_local.persona import build_hermes_system_block

system_prompt = build_hermes_system_block("research", "high")
payload = {
    "model": "hermes3:8b",
    "system": system_prompt,       # <-- campo separado, no en el prompt
    "prompt": user_message,
    "stream": False,
    "options": {"num_predict": 400, "num_ctx": 4096, "temperature": 0.1},
}
```

## Reflective Phase (D6=B — experimental)

El sistema puede proponer nuevas skills basándose en patrones de uso repetitivos.
Las propuestas se guardan en `_agents/skills/proposed/` para revisión humana.

**Flujo:**
1. `reflective_phase.py` analiza los últimos N turnos del bot
2. Detecta patrones: comandos frecuentes, temas recurrentes, errores repetidos
3. Genera un borrador de skill en `_agents/skills/proposed/<nombre>/SKILL.md`
4. El tesista revisa y aprueba manualmente antes de mover a `_agents/skills/`

**Activación:** Comando `/skills_pendientes` en Telegram muestra las propuestas.

## Variables de entorno relevantes

```
OPENCLAW_HERMES_ENABLED=1           # Activa hermes3:8b si benchmark OK
OPENCLAW_HERMES_FALLBACK_MODEL=qwen3:4b  # Fallback si hermes no disponible
OPENCLAW_ADAPTIVE_ROUTING_ENABLED=1      # Habilita routing inteligente
OPENCLAW_NPU_AUTO_PROMOTE=0              # NPU: desactivado hasta benchmark nativo
OPENCLAW_SUMMARY_MODELS=qwen2.5:0.5b    # Modelo de rolling summary
```

## Roadmap de activacion

```
[x] Fase 0: Fix rolling_summary (import circular)
[x] Fase 1: Test suite 42/42
[x] Fase 2: Benchmark edge Ollama (5.37 TPS promedio)
[x] Fase 3: run_pc_benchmark_hermes.py creado
[x] Fase 4: adaptive_router.py con candidato Hermes condicional
[x] Fase 4: persona.py con build_hermes_system_block (ChatML)
[ ] Fase 3 EXEC: ollama pull hermes3:8b → run_pc_benchmark_hermes.py
[ ] Fase 4 EXEC: si D2=A → OPENCLAW_HERMES_ENABLED=1
[ ] Fase 2b: setup_edge_rkllm.sh en edge → benchmark NPU nativo
[ ] Fase 5: reflective_phase.py + /skills_pendientes en bot
```

## Gobernanza (AGENTS.md)

- Hermes Agent Framework NO se adopta — perdería gobernanza académica acumulada
- OpenClaw permanece como orquestador soberano en todos los escenarios
- Toda activación de Hermes requiere Step ID de validacion humana (DEC-0014)
- Este documento es EXPERIMENTAL hasta que el benchmark confirme D2=A

[LID]:  ruta local no pública 
[GOV]:  ruta local no pública 
[AUD]:  ruta local no pública

_Última actualización: `2026-05-15`._
