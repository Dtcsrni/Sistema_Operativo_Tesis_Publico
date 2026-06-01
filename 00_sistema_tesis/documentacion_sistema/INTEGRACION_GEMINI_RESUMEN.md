# Integración Gemini + Modelos Locales — Resumen v2

**Fecha:** 8 de mayo de 2026  
**Estado:** ✅ Completado + Optimizado para Máxima Eficiencia  
**Crédito Disponible:** $5,153.54 (Vencimiento: 22 de junio de 2026)

---

## 🎯 CAMBIOS EN v2 (OPTIMIZACIÓN)

### ✅ NUEVO: Cost Limiter
- Archivo: `runtime/providers/cost_limiter.py`
- Funcionalidad: Tracking automático de presupuesto diario ($114.53/día)
- Acción: Rechaza solicitudes Gemini si se excede presupuesto
- Logs: `config/logs/daily_state.json`, `config/logs/requests_*.jsonl`

### ✅ MEJORADO: Gemini Provider (v2)
- **Cambio principal:** Usa **Gemini 1.5 Flash por defecto** (no Pro)
- Razón: Flash es ~6X más barato que Pro ($0.01/input vs $0.075/input)
- Integración: Incluye `cost_limiter` automáticamente
- Respuesta: Retorna `{"text": ..., "cost": float, "budget_ok": bool}`

### ✅ MEJORADO: Factory (__init__.py)
- Nueva función: `create_smart_hybrid()` — Selecciona proveedor automáticamente
- Estrategia: Ollama primero (siempre), Gemini Flash si presupuesto OK
- Fallback: Si Ollama falla y presupuesto insuficiente, rechaza

### ✅ NUEVO: Monitor de Costos
- Archivo: `07_scripts/monitor_costs.py`
- Uso: `python 07_scripts/monitor_costs.py` (ejecutar diariamente)
- Salida: Reporte detallado de gasto + proyecciones

---

## ¿Qué Está Hecho? (Original)

### ✅ Autenticación (ADC)
- Instalé `gcloud` SDK en tu host Windows.
- Creé credenciales ADC: ` ruta local no pública `
- Habilitada API Vertex AI en tu proyecto GCP (`project-d72bb17e-5918-431c-ba5`).

### ✅ Contenedor opencode-executor
- Añadido `google-genai` al Dockerfile.
- Montaje ADC **comentado** en `docker-compose.pc.yml` → **desactiva Gemini por defecto**.
- Imagen reconstruida: `docker compose build opencode-executor`.

### ✅ Sistema de Providers (MEJORADO)
- `runtime/providers/gemini.py` — **v2: Flash defecto + cost_limiter**
- `runtime/providers/ollama_provider.py` — sin cambios
- `runtime/providers/__init__.py` — **+create_smart_hybrid()**
- `runtime/providers/cost_limiter.py` — **NUEVO**

### ✅ Tests y Documentación
- `07_scripts/test_provider_fallback.py` — 3 modos: local-only, hybrid, gemini
- `00_sistema_tesis/documentacion_sistema/COSTES_MODELOS.md` — costes comparativos
- `00_sistema_tesis/documentacion_sistema/ESTRATEGIA_OPTIMIZACION_CREDITOS.md` — **NUEVO**
- `00_sistema_tesis/documentacion_sistema/GUIA_USO_RAPIDA.md` — **NUEVO**

---

## 🎯 MODO POR DEFECTO: LOCAL-ONLY (SIN COSTES)

Tu stack usa **solo Ollama local**. Gemini está instalado pero **desactivado**.

```bash
# ✅ GRATIS - Uso local
python 07_scripts/test_provider_fallback.py --mode local-only
```

---

## 💡 NUEVO: USO INTELIGENTE (SMART HYBRID)

```python
from runtime.providers import create_smart_hybrid

# Selecciona automáticamente
result = create_smart_hybrid()
provider = result["provider"]
mode = result["mode"]  # "local" o "hybrid_fallback"
cost = result["cost"]  # "$0" o "$~0.025/1K"

# Usar
response = provider.send("Analiza esto", max_tokens=2000)
if response.get("budget_ok"):
    print(f"✅ Éxito. Costo: ${response['cost']:.4f}")
else:
    print(f"❌ Presupuesto insuficiente")
```

**Decisión automática:**
1. Intenta Ollama (siempre, $0)
2. Si Ollama falla + presupuesto OK → Gemini Flash (~$0.025/1K tokens)
3. Si presupuesto insuficiente → Rechaza

---

## ⚠️ CÓMO ACTIVAR GEMINI (CON COSTES)

### Opción A: Activar para Prueba Puntual

```bash
docker compose -f docker-compose.pc.yml exec opencode-executor python -c \
  "from runtime.providers import get_provider; \
   p = get_provider('gemini', project='project-d72bb17e-5918-431c-ba5', model='gemini-1.5-flash'); \
   r = p.send('Prueba rápida', max_tokens=500); \
   print(f'Respuesta: {r[\"text\"][:100]}...'); \
   print(f'Costo: ${r[\"cost\"]:.6f}')"
```

### Opción B: Activar Permanentemente en Docker

**Archivo:** `docker-compose.pc.yml` - Descomenta:

```yaml
environment:
  - GOOGLE_GENAI_USE_VERTEXAI=true
  - GOOGLE_CLOUD_PROJECT=project-d72bb17e-5918-431c-ba5
  - GOOGLE_APPLICATION_CREDENTIALS=/secrets/adc.json
  
volumes:
  - ${APPDATA}/gcloud/application_default_credentials.json:/secrets/adc.json:ro
```

Luego:
```bash
docker compose -f docker-compose.pc.yml up -d opencode-executor
```

---

## 📊 MONITOREO DIARIO (IMPORTANTE)

```bash
# Ver presupuesto y gasto hoy
python 07_scripts/monitor_costs.py

# Salida esperada:
# ╔══════════════════════════════════════════════════════════╗
# ║          💰 GOOGLE CLOUD BILLING MONITOR               ║
# ╚══════════════════════════════════════════════════════════╝
# 
# 💸 HOY (2026-05-08):
#    Gasto acumulado:           $      0.0050
#    % del presupuesto diario:       0.0%
#    Estado:                    ✅ OK
```

---

## 🔐 LÍMITES DE SEGURIDAD AUTOMÁTICOS

Estos se activan **sin intervención manual:**

| Condición | Acción |
|-----------|--------|
| Gasto > $114.53/día | ❌ Rechaza Gemini, fuerza Ollama |
| Gasto acumulado > 80% | ⚠️ Alerta + logs |
| Gasto acumulado > 95% | 🚨 Crítico, solo emergencias |
| Presupuesto insuficiente | ❌ Rechaza solicitud automáticamente |

**No hay riesgo de sorpresas en GCP Billing.**

---

## 📈 PRESUPUESTO ESTIMADO

Con $5,153.54 disponibles y 45 días:

| Escenario | Presupuesto/día | Duración |
|-----------|---|---|
| Conservative | $50 | 103 días (+ sobra) |
| Moderate | $100 | 51 días |
| Aggressive | $200 | 26 días |

**Recomendación:**
- Días 1-30: Gasta $50/día máx (experimental)
- Días 31-45: Gasta $100/día máx (productivo)
- Total: ≤$4,600, guarda $500 reserva

---

## 🚀 COMANDOS RÁPIDOS

```bash
# Verificar presupuesto
python 07_scripts/monitor_costs.py

# Probar local-only (sin costes)
python 07_scripts/test_provider_fallback.py --mode local-only

# Probar Gemini Flash (con costes)
python 07_scripts/test_provider_fallback.py --mode hybrid

# Ver logs de solicitudes hoy
tail config/logs/requests_*.jsonl

# Resetear presupuesto diario (testing)
rm config/logs/daily_state.json
```

---

## 📚 DOCUMENTACIÓN RELACIONADA

- **Estrategia Completa:** `00_sistema_tesis/documentacion_sistema/ESTRATEGIA_OPTIMIZACION_CREDITOS.md`
- **Guía Rápida:** `00_sistema_tesis/documentacion_sistema/GUIA_USO_RAPIDA.md`
- **Costes Comparativos:** `00_sistema_tesis/documentacion_sistema/COSTES_MODELOS.md`

---

**Última actualización:** 8 de mayo de 2026, 18:30 UTC  
**Sistema:** Gemini 1.5 Flash (default) + Ollama Local + Smart Hybrid + Cost Limiter  
**Estado:** ✅ Listo para máxima optimización

# Ve a GCP Console → Billing → Reports
# Busca costes bajo "Vertex AI"
```

---

## 📊 Costes Reales

| Modelo | Costo | Cuándo |
|--------|-------|--------|
| Ollama (`deepseek-r1:7b`) | $0 | Siempre (es local) |
| Gemini 2.5 Pro | ~$0.075 per 1K tokens | Si desactivas Ollama y usas Gemini |
| Gemini Flash | ~$0.01 per 1K tokens | Alternativa más barata |

---

## 🔍 Monitoreo

### GCP Billing
1. Ve a **GCP Console** → **Billing** → **Reports**
2. Filtra por "Vertex AI"
3. Verás costes si usaste Gemini

### Presupuesto (recomendado)
1. GCP Console → **Billing** → **Budgets & alerts**
2. Crea presupuesto de $5/mes
3. Recibirás alertas si se acerca

---

## 📝 Próximos Pasos (Opcionales)

1. **Más modelos locales:** agregar RKLLM (Edge) como fallback.
2. **Optimización:** cachear respuestas para reducir llamadas a Gemini.
3. **RAG híbrido:** usar embeddings locales + textos con Gemini solo si es complejo.
4. **Dashboard:** visualizar qué provider se usó en cada tarea.

---

## 🚀 Quick Commands

```bash
# Test: modo local-only (SIN COSTES)
python 07_scripts/test_provider_fallback.py --mode local-only

# Test: modo hybrid (Ollama primero, Gemini si falla)
python 07_scripts/test_provider_fallback.py --mode hybrid

# Test: modo Gemini directo (GENERA COSTES)
python 07_scripts/test_provider_fallback.py --mode gemini

# Levantar stack con configuración actual (local-only)
docker compose -f docker-compose.pc.yml up -d

# Ver logs
docker compose -f docker-compose.pc.yml logs -f opencode-executor
```

---

**Conclusión:** Puedes usar Gemini si lo necesitas, pero por defecto está desactivado. Usa Ollama local (sin costes) y activa Gemini solo cuando requieras máxima calidad y estés dispuesto a pagar.
