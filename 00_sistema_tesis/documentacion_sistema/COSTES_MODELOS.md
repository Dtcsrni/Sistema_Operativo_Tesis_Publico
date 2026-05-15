# Costes de Modelos: Guía Rápida

## SIN COSTES (Local, en tu máquina)

| Provider | Modelo | Costo | Dónde |
|----------|--------|-------|-------|
| Ollama | `deepseek-r1:7b`, `qwen2.5:7b`, etc. | $0 | `http://ollama-pc:11434` |
| RKLLM (Edge) | `qwen2.5_3b.rkllm` | $0 | Orange Pi 5 Plus (NPU) |
| Hermes | (si está configurado) | $0 | Local GPU |

**Recomendación:** usa estos por defecto. **NUNCA generan costes.**

---

## CON COSTES (Google Cloud - Vertex AI)

| Provider | Modelo | Costo | Límites |
|----------|--------|-------|---------|
| Gemini 2.5 Pro | `gemini-2.5-pro` | ~$0.075/1K tokens generados | Rate: 10 req/min (free tier) |
| Gemini Flash | `gemini-1.5-flash` | ~$0.01/1K tokens | Rate: 10 req/min (free tier) |

**Importante:** Cada token generado cuesta dinero. Los "límites" son de rate, no de costo.

---

## Cómo Evitar Costes

### Opción 1: Usar LOCAL-ONLY (recomendado)
```python
from runtime.providers import create_local_only

# Nunca usa Gemini, solo Ollama/local
result = create_local_only(base_url="http://ollama-pc:11434")
prov = result["provider"]
resp = prov.send("Tu prompt")  # $0 costo
```

### Opción 2: Modo Hybrid (local primero)
```python
from runtime.providers import create_with_fallback

# Intenta Ollama; solo si FALLA completamente, usa Gemini (con confirmación manual)
result = create_with_fallback(
    primary="ollama",
    fallback="gemini",
    base_url="http://ollama-pc:11434",
    project="project-d72bb17e-5918-431c-ba5"
)
```

### Opción 3: Desactivar Gemini Completamente
```python
# En docker-compose.pc.yml, QUITAR o comentar:
# - GOOGLE_GENAI_USE_VERTEXAI=true
# - GOOGLE_APPLICATION_CREDENTIALS=/secrets/adc.json
```

---

## Límites de Cuota (No Son Costos)

Tu proyecto GCP tiene cuotas **gratuitas**:
- **10 requests/minuto** para Gemini en free tier.
- **100 requests/día** (aproximadamente).
- Cuando se alcanza la cuota, las llamadas **fallan** pero **no generan cargo**.

Para aumentar cuotas: GCP Console → Vertex AI → Quotas & Limits → Request.

---

## Monitoreo de Costes

1. Ve a **GCP Console** → **Billing** → **Reports**.
2. Verifica "Vertex AI" como categoría de servicio.
3. Si ves costes, fueron por llamadas a Gemini.
4. Configura **Budgets & Alerts** en Billing para recibir notificaciones.

---

## Recomendación Final para Ti

✅ **Usa `create_local_only()` por defecto.**
- Ollama en PC: sin costes, instantáneo.
- RKLLM en Edge: sin costes, 24/7.
- Si necesitas máxima calidad: usa modo Hybrid pero **revisa costes primero**.

❌ **No uses Gemini directo sin revisar billing.**

_Última actualización: `2026-05-15`._
