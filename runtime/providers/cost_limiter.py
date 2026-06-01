#!/usr/bin/env python3
"""
Cost Limiter para Gemini - Protección de presupuesto diario
Mantiene tracking de gasto y rechaza solicitudes si se excede presupuesto
"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Tuple


class CostLimiter:
    """Controla gastos diarios de Gemini basado en presupuesto"""
    
    def __init__(
        self,
        daily_budget_usd: float = 114.53,
        log_dir: str = "config/logs"
    ):
        self.daily_budget = daily_budget_usd
        self.spent_today = 0.0
        self.last_reset = date.today()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Token pricing (USD)
        self.costs = {
            "gemini-1.5-flash": {
                "input": 0.01 / 1_000_000,    # $0.01 per 1M input
                "output": 0.04 / 1_000_000,   # $0.04 per 1M output
            },
            "gemini-3-flash": {
                "input": 0.01 / 1_000_000,    # $0.01 per 1M input (estimado v3)
                "output": 0.04 / 1_000_000,   # $0.04 per 1M output (estimado v3)
            },
            "gemini-2.5-pro": {
                "input": 0.075 / 1_000_000,   # $0.075 per 1M input
                "output": 0.3 / 1_000_000,    # $0.30 per 1M output
            }
        }
        
        self._load_daily_state()
    
    def _load_daily_state(self):
        """Carga o resetea el estado diario"""
        state_file = self.log_dir / "daily_state.json"
        
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
                state_date = datetime.fromisoformat(state["date"]).date()
                
                if state_date == date.today():
                    self.spent_today = state["spent"]
                    self.last_reset = state_date
                    return
        
        # Reset o inicializar
        self.spent_today = 0.0
        self.last_reset = date.today()
        self._save_daily_state()
    
    def _save_daily_state(self):
        """Persiste el estado actual"""
        state_file = self.log_dir / "daily_state.json"
        state = {
            "date": datetime.combine(self.last_reset, datetime.min.time()).isoformat(),
            "spent": self.spent_today
        }
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estima costo de una llamada Gemini"""
        if model not in self.costs:
            model = "gemini-1.5-flash"  # Default
        
        c = self.costs[model]
        cost = (input_tokens * c["input"]) + (output_tokens * c["output"])
        return round(cost, 6)
    
    def can_use_gemini(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        enforce: bool = True
    ) -> Tuple[bool, float, str]:
        """
        Decide si se puede usar Gemini basado en presupuesto
        
        Returns:
            (allowed: bool, estimated_cost: float, reason: str)
        """
        today = date.today()
        if today > self.last_reset:
            self.spent_today = 0.0
            self.last_reset = today
            self._save_daily_state()
        
        estimated_cost = self.estimate_cost(model, input_tokens, output_tokens)
        remaining = self.daily_budget - self.spent_today
        
        # Siempre permitir Flash si queda presupuesto
        if model == "gemini-1.5-flash":
            if estimated_cost < remaining:
                return True, estimated_cost, "✅ Presupuesto OK (Flash)"
            else:
                reason = f"❌ Presupuesto insuficiente: ${estimated_cost:.4f} > ${remaining:.4f}"
                return False, estimated_cost, reason
        
        # Pro: solo si queda 30%+ presupuesto
        if model == "gemini-2.5-pro":
            threshold = self.daily_budget * 0.30
            if estimated_cost < threshold and estimated_cost < remaining:
                return True, estimated_cost, "⚠️ Presupuesto OK (Pro, uso moderado)"
            else:
                reason = f"❌ Pro bloqueado: ${estimated_cost:.4f} > ${threshold:.4f} (30% presupuesto)"
                return False, estimated_cost, reason
        
        return False, estimated_cost, "❌ Modelo desconocido"
    
    def log_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        status: str = "success"
    ):
        """Registra una solicitud Gemini en el log"""
        log_file = self.log_dir / f"requests_{date.today().isoformat()}.jsonl"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "status": status
        }
        
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        self.spent_today += cost
        self._save_daily_state()
    
    def get_daily_report(self) -> Dict:
        """Retorna reporte de gasto diario"""
        remaining = self.daily_budget - self.spent_today
        pct_used = (self.spent_today / self.daily_budget) * 100 if self.daily_budget > 0 else 0
        
        return {
            "date": self.last_reset.isoformat(),
            "total_budget": self.daily_budget,
            "spent": round(self.spent_today, 4),
            "remaining": round(remaining, 4),
            "percent_used": round(pct_used, 1),
            "status": "⚠️ CRITICAL" if pct_used > 80 else "✅ OK" if pct_used < 50 else "⏱️ MODERATE"
        }
    
    def print_status(self):
        """Imprime estado actual formateado"""
        report = self.get_daily_report()
        
        print(f"""
╔════════════════════════════════════╗
║ 💰 DAILY BUDGET STATUS             ║
╚════════════════════════════════════╝

Fecha:            {report['date']}
Presupuesto:      ${report['total_budget']:.2f}
Gasto acumulado:  ${report['spent']:.4f}
Saldo restante:   ${report['remaining']:.4f}
Uso:              {report['percent_used']:.1f}%
Estado:           {report['status']}
        """)


# Singleton global para fácil acceso
_limiter: CostLimiter = None

def get_cost_limiter(daily_budget: float = 114.53) -> CostLimiter:
    """Obtiene instancia global del CostLimiter"""
    global _limiter
    if _limiter is None:
        _limiter = CostLimiter(daily_budget_usd=daily_budget)
    return _limiter
