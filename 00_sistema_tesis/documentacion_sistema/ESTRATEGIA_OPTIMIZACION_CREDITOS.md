# 🎯 Estrategia de Optimización de Créditos - $5,153.54 (45 días)

**Crédito Disponible:** $5,153.54  
**Vencimiento:** 22 de junio de 2026 (45 días)  
**Meta:** Gastar 0% extra, maximizar Gemini cuando sea beneficioso

---

## 📊 Presupuesto Diario Recomendado

```
$5,153.54 ÷ 45 días = ~$114.53/día (límite blando)
```

**Estrategia de gasto:**
- **Días 1-30:** $50/día máx (Fase experimental, bajo riesgo)
- **Días 31-45:** $100/día máx (Fase productiva, total control)
- **Reserva:** $500 (siempre no gastar)

---

## 🔄 Arquitectura de Decisión (3 Capas)

### Capa 1: LOCAL-ONLY (GRATIS) - 90% del tiempo
**Cuándo usarla:**
- Prototipado rápido
- Tests unitarios
- Síntesis simples (<500 tokens)
- Consultas de contexto
- Desarrollo inicial

**Proveedores:**
- ✅ Ollama (http://ollama-pc:11434)
  - deepseek-r1:7b → Razonamiento + coding
  - qwen2.5-coder:7b → Programación pura
- ✅ RKLLM Edge (NPU Orange Pi, 0 costo)
  - qwen2.5_3b.rkllm → Inferencia offline

**Costo:** $0

---

### Capa 2: GEMINI FLASH (ECONÓMICO) - 8% del tiempo
**Cuándo usarla:**
- Síntesis académica mediana (1-2K tokens)
- Traducciones ES→EN
- Validación de lógica complex
- Análisis de datos moderado

**Config:**
```python
model="gemini-1.5-flash"
max_tokens=2000
```

**Costos estimados:**
- Input: $0.01 / 1M tokens
- Output: $0.04 / 1M tokens
- **Promedio:** ~$0.025 por 1K tokens

**Presupuesto asignado:** $1,500 (60,000 requests medianos)

---

### Capa 3: GEMINI PRO (PREMIUM) - 2% del tiempo
**Cuándo usarla:**
- Análisis de tesis completa (>5K tokens)
- Síntesis multi-documento
- Redacción académica final
- Investigación conceptual profunda

**Config:**
```python
model="gemini-2.5-pro"
max_tokens=4000
```

**Costos:**
- Input: $0.075 / 1M tokens
- Output: $0.3 / 1M tokens
- **Promedio:** ~$0.15 por 1K tokens (6X más caro que Flash)

**Presupuesto asignado:** $500 (casos críticos solamente)

---

## 💻 Implementación Técnica

### 1. Configurar Runtime para Flash por Defecto

**Archivo:** `runtime/providers/gemini.py`

```python
class GeminiProvider:
    def __init__(
        self,
        project: str,
        location: str = "us-central1",
        model: str = "gemini-1.5-flash",  # ← CAMBIO: Flash por defecto
        use_cache: bool = True
    ):
        self.model = model
        # ...
```

**Uso explícito de Pro:**
```python
# Solo cuando sea CRÍTICO
provider = GeminiProvider(
    project="project-d72bb17e-5918-431c-ba5",
    model="gemini-2.5-pro"  # Sobrescribe solo si es necesario
)
```

### 2. Rate Limiting por Tipo de Solicitud

**Archivo:** `07_scripts/cost_limiter.py` (NUEVO)

```python
import time
from datetime import datetime

class CostLimiter:
    def __init__(self, daily_budget_usd=114.53):
        self.daily_budget = daily_budget_usd
        self.spent_today = 0.0
        self.last_reset = datetime.now().date()
    
    def can_use_gemini(self, request_type: str, est_cost: float) -> bool:
        """Decide si usar Gemini basado en presupuesto diario"""
        today = datetime.now().date()
        
        # Reset diario
        if today > self.last_reset:
            self.spent_today = 0.0
            self.last_reset = today
        
        remaining = self.daily_budget - self.spent_today
        
        if request_type == "flash" and est_cost < (remaining * 0.7):
            return True  # OK, aún hay presupuesto
        elif request_type == "pro" and est_cost < (remaining * 0.1):
            return True  # Solo si quedan fondos y es crítico
        else:
            print(f"⚠️ BUDGET LIMIT: ${est_cost} > ${remaining} remaining")
            return False  # Usar Ollama instead
    
    def log_cost(self, tokens: int, model: str, cost: float):
        """Registra gasto actual"""
        self.spent_today += cost
        with open("/logs/daily_costs.log", "a") as f:
            f.write(f"{datetime.now().isoformat()} | {model} | {tokens} tokens | ${cost}\n")
```

### 3. Provider Factory con Decisión Automática

**Archivo:** `runtime/providers/__init__.py` (MODIFICAR)

```python
def create_hybrid_smart(
    primary="ollama",
    fallback_to_gemini=True,
    max_daily_spend=114.53,
    force_local=False
):
    """
    Selecciona proveedor inteligentemente basado en:
    - Presupuesto diario
    - Complejidad de tarea
    - Disponibilidad de Ollama
    
    force_local=True → Fuerza Ollama, rechaza Gemini
    """
    from runtime.providers.cost_limiter import CostLimiter
    
    limiter = CostLimiter(daily_budget_usd=max_daily_spend)
    
    # Intentar Ollama primero (siempre)
    try:
        ollama = OllamaProvider(model="deepseek-r1:7b")
        ollama.health_check()
        return {"provider": ollama, "mode": "local", "cost": "$0"}
    except:
        if force_local:
            raise RuntimeError("Ollama unavailable and force_local=True")
    
    # Fallback a Gemini solo si presupuesto permite
    if fallback_to_gemini and limiter.can_use_gemini("flash", 0.025):
        return {
            "provider": GeminiProvider(
                project="project-d72bb17e-5918-431c-ba5",
                model="gemini-1.5-flash"
            ),
            "mode": "hybrid_fallback",
            "cost": "$~0.025/1K tokens"
        }
    
    # Rechazo total
    raise RuntimeError("All providers exhausted (budget limit reached)")
```

---

## 📈 Monitoreo de Costos (Dashboard)

### Script: `07_scripts/monitor_costs.py`

```python
#!/usr/bin/env python3
"""Monitor de costos en tiempo real - Ejecutar diariamente"""

import json
from datetime import datetime, timedelta
from pathlib import Path

COSTS = {
    "gemini-1.5-flash": {
        "input": 0.01 / 1_000_000,  # $0.01 per 1M input
        "output": 0.04 / 1_000_000, # $0.04 per 1M output
    },
    "gemini-2.5-pro": {
        "input": 0.075 / 1_000_000,
        "output": 0.3 / 1_000_000,
    }
}

def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estima costo de una llamada Gemini"""
    c = COSTS.get(model, COSTS["gemini-1.5-flash"])
    return (input_tokens * c["input"]) + (output_tokens * c["output"])

def read_billing_report():
    """Lee GCP Billing Report desde consola exportado como CSV"""
    report_path = Path("00_sistema_tesis/config/gcp_billing_export.csv")
    
    if not report_path.exists():
        print("❌ No billing export found at", report_path)
        print("📍 Descargar desde: GCP Console → Billing → Reports → Exportar CSV")
        return None
    
    # Parse CSV and aggregate Vertex AI costs
    total_cost = 0.0
    with open(report_path) as f:
        for line in f:
            if "Vertex AI" in line and "Generative AI" in line:
                cost_col = line.strip().split(",")[-1]
                try:
                    total_cost += float(cost_col)
                except:
                    pass
    
    return total_cost

def main():
    # Budget
    TOTAL_CREDIT = 5153.54
    EXPIRY = datetime(2026, 6, 22)
    DAYS_LEFT = (EXPIRY - datetime.now()).days
    DAILY_BUDGET = TOTAL_CREDIT / DAYS_LEFT
    
    # Current spend
    current_spend = read_billing_report() or 0.0
    remaining = TOTAL_CREDIT - current_spend
    
    # Report
    print(f"""
╔═══════════════════════════════════════╗
║ 💰 GOOGLE CLOUD CREDIT MONITOR       ║
╚═══════════════════════════════════════╝

📊 ESTADO ACTUAL:
   Total asignado:    ${TOTAL_CREDIT:,.2f}
   Gasto acumulado:   ${current_spend:,.2f}
   Saldo restante:    ${remaining:,.2f}
   Porcentaje usado:  {(current_spend/TOTAL_CREDIT)*100:.1f}%

📅 TIEMPO:
   Días restantes:    {DAYS_LEFT} (Vencimiento: {EXPIRY.strftime('%d/%m/%Y')})
   Presupuesto diario: ${DAILY_BUDGET:,.2f}
   
⚠️  PROYECCIÓN:
   Si gastas $50/día:  {remaining / 50:.0f} días más (seguro)
   Si gastas $100/día: {remaining / 100:.0f} días más (moderado)
   Si gastas $200/día: {remaining / 200:.0f} días más (RIESGO)

✅ RECOMENDACIÓN:
   Mantén gasto < ${DAILY_BUDGET:.2f}/día
   Prioriza Ollama (local, $0)
   Usa Gemini Flash para síntesis mediana
    """)

if __name__ == "__main__":
    main()
```

**Ejecutar:**
```bash
python 07_scripts/monitor_costs.py
```

---

## 📋 Matriz de Decisión

| Tarea | Tokens Est. | Modelo | Costo | Decisión |
|-------|------------|--------|-------|----------|
| Tests rápidos | <500 | Ollama | $0 | ✅ Siempre |
| Síntesis simple | 500-2K | Ollama | $0 | ✅ Siempre |
| Análisis moderado | 2-5K | Gemini Flash | ~$0.075 | ✅ 90% confianza |
| Redacción tesis | >5K | Gemini Flash | ~$0.15 | ⚠️ Si presupuesto |
| Investigación pesada | >10K | Gemini Pro | ~$1.50 | ❌ Solo CRÍTICO |

---

## 🚨 Límites de Seguridad (Docker)

**Archivo:** `docker-compose.pc.yml`

```yaml
environment:
  # Gemini (comentado por defecto)
  # - GOOGLE_GENAI_USE_VERTEXAI=true
  # - GOOGLE_CLOUD_PROJECT=project-d72bb17e-5918-431c-ba5
  
  # Rate limiting
  - GEMINI_MAX_REQUESTS_PER_DAY=500
  - GEMINI_MAX_COST_PER_DAY=100
  - GEMINI_FALLBACK_TO_OLLAMA=true
```

---

## 📊 Casos de Uso Recomendados

### ✅ **Usar Ollama (100% recomendado)**
```
- Debugging de código
- Unit tests
- Consultas de contexto
- Prototipado rápido
- Generación de SQL/queries
- Análisis lexical de textos
```

### ⚠️ **Usar Gemini Flash (8-10 casos/día)**
```
- Síntesis de papers académicos (2-3K tokens)
- Traducciones técnicas
- Validación de lógica compleja
- Reformulación de párrafos
- Q&A sobre capítulos tesis
```

### ❌ **EVITAR Pro, solo Flash**
```
- Nunca usar gemini-2.5-pro a menos que:
  - Análisis de tesis COMPLETA (>20K tokens)
  - Decisiones académicas críticas
  - Síntesis multi-fuente final
- Máximo: 2 llamadas Pro / semana
```

---

## 💡 Tips para Maximizar

1. **Agrupación de solicitudes**: Envía N consultas en 1 llamada Flash en lugar de N llamadas
2. **Caché de respuestas**: Ollama responde en 2-3s; cachea si repetición
3. **Truncamiento inteligente**: Si análisis es de 500 páginas, resume primero con Ollama
4. **Horarios de bajo costo**: Gemini pricing es fijo, pero tus solicitudes = mejor agruparlas
5. **Modo offline**: RKLLM Edge (NPU) = $0 incluso si internet cae

---

## 📞 Acciones Inmediatas

- [ ] Cambiar `gemini.py` → Flash por defecto
- [ ] Implementar `cost_limiter.py`
- [ ] Exportar CSV de GCP Billing
- [ ] Ejecutar `monitor_costs.py` diariamente
- [ ] Establecer alarma en móvil: "Revisar presupuesto Gemini"

---

**Última actualización:** 8 de mayo de 2026  
**Vigencia:** Hasta 22 de junio de 2026
