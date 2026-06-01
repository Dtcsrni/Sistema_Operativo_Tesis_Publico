# 🚀 Guía Rápida de Uso - Sistema Optimizado de Costos

## 1️⃣ Verificar Presupuesto Diario

```bash
python 07_scripts/monitor_costs.py
```

**Salida esperada:**
```
╔══════════════════════════════════════════════════════════╗
║          💰 GOOGLE CLOUD BILLING MONITOR               ║
╚══════════════════════════════════════════════════════════╝

💸 HOY (2026-05-08):
   Gasto acumulado:           $    0.0050
   % del presupuesto diario:     0.0%
   Estado:                    ✅ OK
```

---

## 2️⃣ Usar en Código Python

### Opción A: LOCAL-ONLY (Recomendado - GRATIS)
```python
from runtime.providers import create_local_only

# Obtener provider (automáticamente Ollama si está disponible)
result = create_local_only()
provider = result["provider"]

# Usar
response = provider.send(
    "Dame un resumen de sistemas operativos",
    max_tokens=500
)

print(response["text"])
# COSTO: $0
```

### Opción B: SMART HYBRID (Recomendado - Automático)
```python
from runtime.providers import create_smart_hybrid

# Decide automáticamente: Ollama primero, Gemini Flash si presupuesto OK
result = create_smart_hybrid()
provider = result["provider"]
mode = result["mode"]  # "local" o "hybrid_fallback"
cost = result["cost"]  # "$0" o "$~0.025/1K"

print(f"Modo: {mode} | Costo: {cost}")

response = provider.send("Analiza este código", max_tokens=2000)
print(response["text"])
# COSTO: $0 si Ollama, ~$0.05 si Gemini Flash
```

### Opción C: Gemini Directo (SOLO para análisis críticos)
```python
from runtime.providers import get_provider

# Flash (económico)
provider = get_provider("gemini", 
    project="project-d72bb17e-5918-431c-ba5",
    model="gemini-1.5-flash"
)

# Pro (premium, úsalo raramente)
provider = get_provider("gemini",
    project="project-d72bb17e-5918-431c-ba5",
    model="gemini-2.5-pro"
)

response = provider.send("Analiza tesis completa", max_tokens=4000)
if response.get("budget_ok"):
    print(f"Costo: ${response['cost']:.4f}")
else:
    print(f"Presupuesto insuficiente: {response.get('error')}")
```

---

## 3️⃣ Estructura de Archivos Nueva

```
runtime/providers/
├── __init__.py           ← Factory mejorada con create_smart_hybrid()
├── ollama_provider.py    ← Provider local (sin cambios)
├── gemini.py             ← MEJORADO: Flash por defecto + cost_limiter
└── cost_limiter.py       ← NUEVO: Control de presupuesto diario

07_scripts/
├── monitor_costs.py      ← NUEVO: Monitor de costos
└── test_provider_fallback.py (sin cambios)

config/logs/              ← NUEVO (se crea automático)
├── daily_state.json      ← Estado presupuesto diario
└── requests_2026-05-08.jsonl  ← Log de solicitudes
```

---

## 4️⃣ Matriz de Decisión Rápida

| Caso de Uso | Proveedor | Costo | Comando |
|---|---|---|---|
| Desarrollo/pruebas | Ollama | $0 | `create_local_only()` |
| Síntesis <2K tokens | Flash | ~$0.05 | `create_smart_hybrid()` |
| Análisis moderado 2-5K | Flash | ~$0.15 | `create_smart_hybrid()` |
| Investigación crítica >5K | Flash | ~$0.30 | `create_smart_hybrid()` |
| Análisis tesis COMPLETA | Pro | ~$1.50 | `get_provider("gemini", model="gemini-2.5-pro")` |

---

## 5️⃣ Presupuesto Estimado

Con $5,153.54 disponibles:

| Modelo | Tokens por $1 | Duración a $50/día | Duración a $100/día |
|--------|---|---|---|
| **Ollama** | ∞ (gratis) | ∞ | ∞ |
| **Gemini Flash** | ~40,000 | 206 días | 103 días |
| **Gemini Pro** | ~6,600 | 34 días | 17 días |

**Recomendación:** 
- Días 1-30: $50/día máx (experimental)
- Días 31-45: $100/día máx (productivo)
- Total: Gasta ≤$4,600, guarda $500 de reserva

---

## 6️⃣ Activar/Desactivar Gemini

### Activar Gemini en Docker:

**Archivo:** `docker-compose.pc.yml`

```yaml
opencode-executor:
  environment:
    # Descomenta estas líneas:
    - GOOGLE_GENAI_USE_VERTEXAI=true
    - GOOGLE_CLOUD_PROJECT=project-d72bb17e-5918-431c-ba5
    - GOOGLE_APPLICATION_CREDENTIALS=/secrets/adc.json
  volumes:
    # Descomenta esta línea:
    - ${APPDATA}/gcloud/application_default_credentials.json:/secrets/adc.json:ro
```

Luego:
```bash
docker compose up -d opencode-executor
```

### Desactivar Gemini (default):
Deja comentadas las líneas anteriores y ejecuta:
```bash
docker compose up -d opencode-executor
```

---

## 7️⃣ Alertas de Presupuesto

**Se activa automáticamente si:**
- Gasto diario > $114.53
- Gasto acumulado > $4,122 (80%)
- Gasto acumulado > $4,896 (95%)

**Acción automática:**
- Rechaza nuevas solicitudes Gemini
- Fuerza fallback a Ollama
- Registra en log para auditoría

---

## 8️⃣ Debugging

### Ver logs detallados:
```bash
cat config/logs/daily_state.json      # Estado presupuesto
tail config/logs/requests_*.jsonl     # Todas las solicitudes
```

### Resetear presupuesto (testing):
```bash
rm config/logs/daily_state.json
```

### Verificar conectividad Gemini:
```python
from runtime.providers.gemini import GeminiProvider

prov = GeminiProvider(project="project-d72bb17e-5918-431c-ba5")
resp = prov.send("Hola, ¿funciono?", max_tokens=100)
print(f"OK: {resp['budget_ok']}, Costo: ${resp['cost']:.6f}")
```

---

## 9️⃣ Checklist de Deployment

- [ ] Instalado `google-genai` en Docker: `pip install google-genai`
- [ ] ADC credentials en `~\AppData\Roaming\gcloud\application_default_credentials.json`
- [ ] Vertex AI API habilitada en GCP
- [ ] `cost_limiter.py` en `runtime/providers/`
- [ ] `gemini.py` actualizado a v2 (Flash por defecto)
- [ ] `__init__.py` con `create_smart_hybrid()`
- [ ] `monitor_costs.py` ejecutable
- [ ] Directorio `config/logs/` creado (se crea automático)

---

## 🔟 Contacto / Soporte

| Problema | Solución |
|---|---|
| Ollama no responde | `docker ps \| grep ollama` → reiniciar con `docker restart ollama-pc` |
| Gemini retorna "Budget exceeded" | Espera hasta mañana o revisa `python 07_scripts/monitor_costs.py` |
| ADC credentials expiradas | `gcloud auth application-default login` |
| Cost limiter no funciona | Revisa `config/logs/daily_state.json` existe |

---

**Última actualización:** 8 de mayo de 2026  
**Sistema:** Gemini 1.5 Flash (defecto) + Ollama Local + Cost Limiter
