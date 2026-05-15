"""
Adaptador optimizado para Google Gemini (Vertex AI) con control de costos.
Interfaz mínima:
- class GeminiProvider(project, location, model)
- send(prompt, max_tokens=512) -> dict {"text": str, "raw": obj}

CAMBIOS v2:
- Defecto: Flash (económico) en lugar de Pro
- Integración: cost_limiter para tracking presupuestario
- Seguridad: rechaza solicitudes si se excede presupuesto diario
"""
from typing import Any, Dict, Optional
import os
from pathlib import Path

try:
    from google import genai
except Exception as e:
    raise ImportError("google-genai no está instalado. Instala google-genai para usar Gemini: pip install google-genai")

try:
    from .cost_limiter import get_cost_limiter
except ImportError:
    # Si cost_limiter no está disponible, usar dummy
    def get_cost_limiter(*args, **kwargs):
        class DummyLimiter:
            def can_use_gemini(self, *args, **kwargs):
                return True, 0.0, "No limiter"
            def log_request(self, *args, **kwargs):
                pass
        return DummyLimiter()


class GeminiProvider:
    """
    Proveedor Gemini con control de costos.
    
    Uso básico:
        prov = GeminiProvider(project="...")
        resp = prov.send("Mi prompt", max_tokens=2000)
    
    Uso con Pro (crítico):
        prov = GeminiProvider(project="...", model="gemini-2.5-pro")
        resp = prov.send("Análisis crítico")
    """
    
    def __init__(
        self,
        project: str,
        location: str = "us-central1",
        model: str = "gemini-3-flash",  # ← CAMBIO: Flash v3 por defecto
        enforce_budget: bool = True
    ):
        self.project = project
        self.location = location
        self.model = model
        self.enforce_budget = enforce_budget
        self.limiter = get_cost_limiter(daily_budget_usd=114.53)
        
        # Cliente reutilizable
        self.client = genai.Client(vertexai=True, project=self.project, location=self.location)
    
    def send(self, prompt: str, max_tokens: int = 512, **kwargs) -> Dict[str, Any]:
        """
        Envía un prompt a Gemini con validación de presupuesto.
        
        Args:
            prompt: Texto del prompt
            max_tokens: Máximo de tokens output
            **kwargs: Parámetros adicionales (ignorados)
        
        Returns:
            {"text": str, "raw": obj, "cost": float, "budget_ok": bool}
        """
        
        # Estimación conservadora: ~4 chars = 1 token
        input_tokens = len(prompt) // 4
        output_tokens = max_tokens
        
        # Verificar presupuesto
        can_proceed, estimated_cost, reason = self.limiter.can_use_gemini(
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            enforce=self.enforce_budget
        )
        
        if not can_proceed and self.enforce_budget:
            return {
                "text": "",
                "raw": f"Budget exceeded: {reason}",
                "cost": 0.0,
                "budget_ok": False,
                "error": reason
            }
        
        # Ejecutar llamada
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            text = getattr(response, "text", None)
            if text is None:
                if hasattr(response, "candidates") and len(response.candidates) > 0:
                    text = response.candidates[0].content
                else:
                    text = str(response)
            
            # Calcular costo real (aproximado)
            actual_output_tokens = len(text) // 4 if text else 0
            actual_cost = self.limiter.estimate_cost(
                self.model,
                input_tokens,
                actual_output_tokens
            )
            
            # Registrar
            self.limiter.log_request(
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=actual_output_tokens,
                cost=actual_cost,
                status="success"
            )
            
            return {
                "text": text,
                "raw": response,
                "cost": actual_cost,
                "budget_ok": True
            }
        except Exception as e:
            self.limiter.log_request(
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=0,
                cost=0.0,
                status="error"
            )
            return {
                "text": "",
                "raw": e,
                "cost": 0.0,
                "budget_ok": False,
                "error": str(e)
            }


if __name__ == "__main__":
    # Pequeña prueba local (requiere ADC configurado)
    prov = GeminiProvider(project="project-d72bb17e-5918-431c-ba5")
    r = prov.send("Prueba desde providers/gemini.py: dame un saludo corto en español")
    print(r["text"])