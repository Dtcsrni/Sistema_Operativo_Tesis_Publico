<!-- DISEÑO ARQUITECTÓNICO: OPENCLAW MAESTRO MOE INTEGRADO -->

# Arquitectura Maestro MoE Integrado para SIOT OpenClaw 2026

**Fecha:** 2026-05-05  
**Estado:** Implementado como feature flag, pendiente de validación humana  
**Superficie:** `runtime/openclaw/openclaw_local/maestro_router.py`

## Resumen

Maestro deja de ser un conjunto de subagentes HTTP aislados y pasa a ser un router MoE integrado dentro de OpenClaw. Reutiliza `session_layer`, `adaptive_router`, `engine`, `OpenClawStore` y la evidencia PEV-02 existente.

El diseño conserva el control humano directo: Maestro propone y registra decisiones de ruteo, pero no valida resultados ni ejecuta acciones mutantes sin los mecanismos APR/Step ID ya existentes.

## Contrato de Decisión

Cada decisión produce un objeto estable:

```json
{
  "route_id": "ROUTE-...",
  "session_id": "SES-...",
  "intent": "chat_fast|coding|ops|research_synthesis|fallback",
  "risk_level": "low|medium|high",
  "selected_provider": "ollama_local|local",
  "selected_model": "qwen3:4b|hermes3:8b|mistral-nemo:12b|...",
  "node": "pc|edge|pc_or_edge_local|local",
  "confidence": 0.82,
  "evidence_refs": ["runtime/pc_control/benchmarks/index.json"],
  "fallback_chain": ["ollama_local:mistral-nemo:12b"],
  "telemetry_required": true,
  "decision_reason": "..."
}
```

## Política MoE

| Intención | Ruta principal | Fallback | Regla |
|---|---|---|---|
| `chat_fast` | `qwen3:4b` | `qwen2.5:1.5b` | Prioriza latencia baja. |
| `coding` | `hermes3:8b` | `mistral-nemo:12b`, `qwen3:4b` | Evita 14B en tiempo real. |
| `ops` | `qwen3:4b` | `qwen2.5:1.5b`, local | Edge opera como secundario operativo. |
| `research_synthesis` | `mistral-nemo:12b` | `hermes3:8b`, `qwen3:4b` | Prioriza precisión y telemetría. |
| `fallback` | `qwen3:4b` | `qwen2.5:0.5b`, local | Degradación explícita. |

Los modelos `qwen3:14b`, `phi4:14b` y `qwen2.5-coder:14b` quedan fuera del ruteo en tiempo real por DEC-0035, salvo carril experimental explícito.

## Evidencia y Guardas

- PC: `runtime/pc_control/benchmarks/index.json` y reportes MoE bajo `runtime/pc_control/benchmarks/reports/`.
- Edge: `runtime/edge_iot/benchmarks/index.json`; si permanece `invalid_for_scientific_claim`, NPU no se promueve.
- Tareas con SLO mayor a 30 s o síntesis pesada activan telemetría requerida por DEC-0037.
- La persistencia se realiza en `maestro_route_decisions` dentro de OpenClawStore.

## Activación

El default operativo es conservador:

```ini
OPENCLAW_MAESTRO_ENABLED=0
```

Se habilita solo después de ejecutar la batería `maestro_moe_benchmark`, pruebas enfocadas y auditoría completa.

_Última actualización: `2026-05-15`._
