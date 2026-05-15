# Política de Eficiencia de Tokens — OpenClaw

<!-- SISTEMA_TESIS:PROTEGIDO -->

**Versión:** 1.0  
**Vigente desde:** 2026-04-29  
**Aplica a:** Todos los agentes IA y pipelines de inferencia que interactúen con el proyecto

---

## Propósito

Reducir el consumo de tokens en todos los agentes sin sacrificar calidad, factualidad ni trazabilidad. Esta política es complementaria a `domain-separation-policy.md` y actúa como guardrail de eficiencia.

---

## Reglas obligatorias

### R1 — Límites de contexto por tipo de solicitud

| Tipo | `num_predict` máx | `num_ctx` máx | Síntesis habilitada |
|------|------------------|--------------|---------------------|
| simple / saludo | 96 | 1024 | No |
| factual corto | 256 | 1024 | Opcional (modelo ligero) |
| conocimiento / razonamiento | 900 | 2048 | Sí (mejor modelo) |
| investigación / síntesis | 900 | 2048 | Sí (2 fases) |
| código | 900 | 2048 | Sí (modelo coder) |

### R2 — Política de caché de respuestas

- Las respuestas a consultas repetidas o semánticamente equivalentes **deben cachearse** con TTL según tipo (ver `response_cache.py`).
- **Nunca se cachean** consultas con marcadores de volatilidad: `ahora`, `hoy`, `precio`, `actual`, `noticias`, `temperatura`, `estado del sistema`.
- El hit de caché debe marcarse explícitamente en el log de telemetría (`cache_hit=True`).

### R3 — Compresión de memoria de chat

- Inyectar máximo **4 turnos recientes completos** en el prompt de contexto.
- Si hay más de 4 turnos: incluir un `rolling_summary` de máximo 200 chars que resuma los anteriores.
- El resumen rolling se actualiza en background cada 8 turnos con el modelo edge.

### R4 — Instrucciones de sistema no duplicadas

- Los prompts de generación e instrucciones de sistema **deben construirse desde `persona.py`**.
- Prohibido copiar bloques de instrucciones entre funciones. Si es necesario reutilizar, extraer a función compartida.

### R5 — Estimación de tokens antes de inferencia

- Para solicitudes con `complexity=high` y proveedor cloud, ejecutar `simulate_budget_request` antes de la llamada.
- Si `remaining_tokens < 20%` del budget diario → activar modo **economy**: solo edge, sin síntesis, con notificación al usuario.

### R6 — Determinismo computacional

- Cálculos determinísticos (conversión de unidades, aritmética, fechas, estadísticas básicas) **no deben usar LLM**.
- Estos se delegan a scripts Python del sistema operativo edge/PC según la disponibilidad del nodo.
- El bot identifica este patrón y llama directamente al script apropiado sin pasar por el modelo.

### R7 — Prompts de síntesis optimizados

- El prompt de síntesis no debe incluir el análisis interno completo si supera 2500 chars: truncar preservando el inicio (más informativo).
- Las instrucciones de sistema del prompt de síntesis son más breves que las del prompt de análisis: el modelo ya tiene el contexto.

---

## Modo Economy

Se activa automáticamente cuando:
- `global_daily_tokens_used / global_daily_budget_tokens >= 0.80`
- O cuando `domain_daily` supera el 80% del budget asignado

En modo economy:
- Solo se usa el modelo edge (qwen3:4b o equivalente local)
- No se ejecuta el paso de síntesis
- El caché TTL se extiende ×2
- Se notifica al usuario: *"⚠️ Modo de ahorro activo — respuestas optimizadas para conservar presupuesto de tokens"*

---

## Agentes externos (Antigravity / VS Code / proveedor de IA no publicado)

- **Antes de abrir archivos del repositorio**, usar la skill `openclaw_context` para obtener el mapa compacto de arquitectura.
- **Antes de editar `telegram_bot.py`**, consultar la skill `vscode_openclaw` para verificar convenciones de prompts.
- Los agentes externos **no deben generar instrucciones de sistema ad-hoc**: usar siempre `persona.build_system_block()`.

---

## Métricas de referencia

| Indicador | Línea base | Meta con esta política |
|-----------|-----------|----------------------|
| Tokens por sesión de agente IA | ~8000 | <4000 (-50%) |
| Hit rate de caché | 0% | >30% |
| Prompts >1500 chars sin caché | Frecuente | <20% de llamadas |
| Latencia P90 respuesta knowledge | ~45s | <60s con síntesis |

_Última actualización: `2026-05-15`._
