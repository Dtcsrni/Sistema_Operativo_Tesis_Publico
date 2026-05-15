#!/usr/bin/env python3
"""
Monitor de Costos Diarios - Google Cloud Billing
Ejecuta diariamente para verificar presupuesto Gemini

Uso:
    python 07_scripts/monitor_costs.py          # Reporte completo
    python 07_scripts/monitor_costs.py --json   # Salida JSON
"""

import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict

# Configuración
TOTAL_CREDIT = 5153.54
EXPIRY_DATE = datetime(2026, 6, 22)
PROJECT_ID = "project-d72bb17e-5918-431c-ba5"
BILLING_ACCOUNT = "012C2C-78915B-616A47"


def calculate_budget_metrics() -> Dict:
    """Calcula métricas de presupuesto"""
    now = datetime.now()
    days_left = (EXPIRY_DATE - now).days
    daily_budget = TOTAL_CREDIT / max(days_left, 1)
    
    return {
        "total_credit": TOTAL_CREDIT,
        "expiry_date": EXPIRY_DATE.strftime("%Y-%m-%d"),
        "days_left": max(days_left, 0),
        "daily_budget": round(daily_budget, 2),
        "warning_threshold": round(TOTAL_CREDIT * 0.80, 2),  # Alerta si 80%
        "critical_threshold": round(TOTAL_CREDIT * 0.95, 2),  # Crítico si 95%
    }


def get_cost_limiter_state() -> Dict:
    """Lee estado del cost limiter"""
    try:
        state_file = Path("config/logs/daily_state.json")
        if state_file.exists():
            with open(state_file) as f:
                return json.load(f)
    except:
        pass
    
    return {
        "date": date.today().isoformat(),
        "spent": 0.0,
        "note": "No state file found or cost_limiter not used"
    }


def get_daily_requests() -> list:
    """Lee último log de solicitudes diarias"""
    try:
        log_file = Path(f"config/logs/requests_{date.today().isoformat()}.jsonl")
        if log_file.exists():
            requests = []
            with open(log_file) as f:
                for line in f:
                    requests.append(json.loads(line))
            return requests
    except:
        pass
    
    return []


def analyze_daily_logs(requests: list) -> Dict:
    """Analiza logs de solicitudes"""
    if not requests:
        return {
            "total_requests": 0,
            "total_cost": 0.0,
            "by_model": {},
            "success_rate": 0.0
        }
    
    by_model = {}
    total_cost = 0.0
    successes = 0
    
    for req in requests:
        model = req.get("model", "unknown")
        cost = req.get("cost_usd", 0.0)
        status = req.get("status", "unknown")
        
        if model not in by_model:
            by_model[model] = {"count": 0, "total_cost": 0.0, "tokens": 0}
        
        by_model[model]["count"] += 1
        by_model[model]["total_cost"] += cost
        by_model[model]["tokens"] += req.get("input_tokens", 0) + req.get("output_tokens", 0)
        
        total_cost += cost
        if status == "success":
            successes += 1
    
    return {
        "total_requests": len(requests),
        "total_cost": round(total_cost, 4),
        "by_model": by_model,
        "success_rate": round((successes / len(requests)) * 100, 1) if requests else 0.0
    }


def generate_report_text(metrics: Dict, cost_state: Dict, daily_analysis: Dict) -> str:
    """Genera reporte en formato texto"""
    
    spent_today = cost_state.get("spent", 0.0)
    status = "✅ OK"
    
    if spent_today > metrics["warning_threshold"]:
        status = "🚨 CRITICAL"
    elif spent_today > metrics["warning_threshold"]:
        status = "⚠️ WARNING"
    
    daily_budget = metrics["daily_budget"]
    pct_of_daily = (spent_today / daily_budget * 100) if daily_budget > 0 else 0
    
    report = f"""
╔══════════════════════════════════════════════════════════╗
║          💰 GOOGLE CLOUD BILLING MONITOR               ║
║          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                         ║
╚══════════════════════════════════════════════════════════╝

📊 PRESUPUESTO GLOBAL:
   Total crédito asignado:    ${metrics['total_credit']:>10,.2f}
   Vencimiento:               {metrics['expiry_date']}
   Días restantes:            {metrics['days_left']:>10} días
   Presupuesto diario:        ${metrics['daily_budget']:>10,.2f}

💸 HOY ({date.today().isoformat()}):
   Gasto acumulado:           ${spent_today:>10,.4f}
   % del presupuesto diario:  {pct_of_daily:>10.1f}%
   Estado:                    {status}

📈 ANÁLISIS DE SOLICITUDES HOY:
   Total solicitudes:         {daily_analysis['total_requests']:>10}
   Costo total:               ${daily_analysis['total_cost']:>10,.4f}
   Tasa de éxito:             {daily_analysis['success_rate']:>10.1f}%

📋 DESGLOSE POR MODELO:
"""
    
    for model, stats in daily_analysis.get("by_model", {}).items():
        report += f"""
   {model}:
      - Solicitudes:          {stats['count']}
      - Costo:                ${stats['total_cost']:.4f}
      - Tokens procesados:    {stats['tokens']:,}
"""
    
    report += f"""
⏰ PROYECCIONES:
   Si mantienes ${metrics['daily_budget']:.2f}/día:
      - Duración total:        ~{int(TOTAL_CREDIT / metrics['daily_budget'])} días
      - Agotamiento:           {(EXPIRY_DATE - timedelta(days=int(TOTAL_CREDIT / metrics['daily_budget']))).strftime('%Y-%m-%d')}
   
   Si gastas $50/día:
      - Días de duración:      {int(TOTAL_CREDIT / 50)} días
      - Saldo el vencimiento:  ${TOTAL_CREDIT - (50 * metrics['days_left']):.2f}

🎯 RECOMENDACIONES:
"""
    
    if spent_today > metrics["daily_budget"]:
        report += """
   ⚠️ ALERTA: Ya has excedido el presupuesto diario
   → Limita solicitudes Gemini hasta mañana
   → Prioriza Ollama (local, $0)
"""
    elif spent_today > (metrics["daily_budget"] * 0.7):
        report += """
   ⚠️ PRECAUCIÓN: Vas por el 70% del presupuesto diario
   → Sigue usando, pero con cuidado
   → Ten Ollama como fallback
"""
    else:
        report += """
   ✅ DENTRO DE PRESUPUESTO
   → Puedes usar Gemini normalmente
   → Prioriza Flash sobre Pro
"""
    
    report += f"""

🔗 REFERENCIAS:
   - Consola de facturación: https://console.cloud.google.com/billing/overview
   - Proyecto: {PROJECT_ID}
   - Cuenta: {BILLING_ACCOUNT}

╚══════════════════════════════════════════════════════════╝
"""
    
    return report


def generate_report_json(metrics: Dict, cost_state: Dict, daily_analysis: Dict) -> Dict:
    """Genera reporte en formato JSON"""
    return {
        "timestamp": datetime.now().isoformat(),
        "budget": metrics,
        "today": {
            "date": date.today().isoformat(),
            "spent": cost_state.get("spent", 0.0),
            "analysis": daily_analysis
        },
        "project": PROJECT_ID,
        "billing_account": BILLING_ACCOUNT
    }


def main():
    """Punto de entrada principal"""
    import_json = "--json" in sys.argv
    
    # Calcular
    metrics = calculate_budget_metrics()
    cost_state = get_cost_limiter_state()
    requests = get_daily_requests()
    daily_analysis = analyze_daily_logs(requests)
    
    # Mostrar
    if import_json:
        print(json.dumps(generate_report_json(metrics, cost_state, daily_analysis), indent=2))
    else:
        print(generate_report_text(metrics, cost_state, daily_analysis))


if __name__ == "__main__":
    main()
