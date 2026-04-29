---
name: token_budget_ops
description: >
  Operaciones de presupuesto de tokens para el proyecto OpenClaw.
  Úsala antes de ejecutar pipelines de inferencia costosos o cuando
  necesites verificar el estado del presupuesto diario/semanal.
version: "1.0"
applies_to:
  - openai_agents
  - vscode_agents
  - antigravity
---

# Skill: token_budget_ops

## Cuándo usar esta skill

- Antes de ejecutar inferencia con proveedores cloud (proveedor de IA no publicado API, Groq API)
- Cuando el usuario pregunte por el presupuesto de tokens
- Cuando `simulate_budget_request` bloquee una solicitud
- Para diagnosticar por qué el bot degradó a modo local

## Archivos clave de presupuesto

```
00_sistema_tesis/config/token_budget.json        # Límites globales y por dominio
00_sistema_tesis/config/token_usage_snapshot.json # Snapshot acumulado externo
manifests/openclaw_budget_policy.yaml             # Política por dominio/proveedor
runtime/openclaw/openclaw_local/budgeting.py      # Lógica: simulate, classify, build
```

## Estructura de token_budget.json

```json
{
  "daily": { "tokens": 40000, "usd": 8.0 },
  "weekly": { "tokens": 240000, "usd": 48.0 },
  "alerts": { "warning_ratio": 0.75, "critical_ratio": 0.90 },
  "domains": {
    "academico": { "daily_ratio": 0.50, "weekly_ratio": 0.50 },
    "profesional": { "daily_ratio": 0.30, "weekly_ratio": 0.30 }
  }
}
```

## Estados de presupuesto

| Estado | Ratio | Acción del sistema |
|--------|-------|--------------------|
| `ok` | <75% | Permitir |
| `warning` | 75-90% | Degradar a local + notificar |
| `critical` | 90-100% | Solo edge local |
| `exhausted` | ≥100% | Bloquear cloud completamente |

## Modo Economy (auto-activado)

Se activa en `telegram_bot.py` cuando el budget global diario ≥ 80%:
- Solo modelo edge (qwen3:4b)
- Sin paso de síntesis
- TTL de caché ×2
- Env flag de override: `OPENCLAW_ECONOMY_MODE=1` (fuerza siempre)

## API de budgeting.py

```python
from .budgeting import simulate_budget_request, build_budget_snapshot, classify_budget_status

# Verificar antes de llamada cloud
result = simulate_budget_request(
    store=store, repo_root=repo_root, budget_policy=budget_policy,
    domain="academico", provider="openai_api",
    estimated_cost_usd=0.005, estimated_tokens=2000,
)
# result["allowed"] → bool
# result["resulting_action"] → "permitido" | "degradar_local_offline_manual"

# Snapshot completo
snapshot = build_budget_snapshot(store=store, repo_root=repo_root, budget_policy=budget_policy)
# snapshot.payload["global"]["daily"]["remaining_tokens"]
```

## Estimación de tokens por tipo de llamada

| Operación | Tokens estimados (prompt+respuesta) |
|-----------|-------------------------------------|
| `/chat` simple (local) | 200-400 |
| `/chat` knowledge (local+web) | 600-1200 |
| `/investiga` análisis | 1500-2500 |
| `/investiga` síntesis | 800-1200 |
| Síntesis chat medium | 400-800 |

## Diagnóstico de bloqueos

Si `simulate_budget_request` bloquea:
1. Verificar `token_usage_snapshot.json` — puede estar desactualizado
2. Verificar que `token_budget.json` tiene ratios correctos para el dominio
3. Verificar que el store SQLite (`OpenClawStore`) tiene registros de billing precisos
4. Si el snapshot externo está inflado, resetear con el script de actualización manual

## Comandos útiles

```bash
# Ver presupuesto actual desde el bot
/herramienta presupuesto

# Ver estado de modelos
/herramienta modelos

# Ver métricas del sistema
/herramienta estado
```

_Última actualización: `2026-04-29`._
