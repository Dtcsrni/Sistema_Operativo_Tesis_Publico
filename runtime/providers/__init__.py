"""
Sistema de selección de providers con fallback automático y control de costos.
- Intenta usar el provider preferido (p. ej. ollama).
- Si falla, intenta fallback (p. ej. gemini).
- Integra cost_limiter para no exceder presupuesto.
- Registra en auditoría qué provider se usó y costo.
"""
import os
import sys
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import logging
logger = logging.getLogger("runtime.providers")

# Agregar runtime al path para importar providers
sys.path.insert(0, str(Path(__file__).parent.parent / "providers"))


class ProviderRegistry:
    """Registro y factory de providers con fallback y control de costos."""
    
    def __init__(self):
        self.providers = {}
        self.cost_limiter = None
        self._register_defaults()
        self._init_cost_limiter()
    
    def _init_cost_limiter(self):
        """Inicializa cost limiter"""
        try:
            from cost_limiter import get_cost_limiter
            self.cost_limiter = get_cost_limiter(daily_budget=114.53)
        except ImportError:
            pass

    def _register_defaults(self):
        """Registra los providers disponibles."""
        # Ollama (default local)
        try:
            from ollama_provider import OllamaProvider
            self.providers["ollama"] = OllamaProvider
        except ImportError:
            logger.debug("OllamaProvider no disponible")
        
        # Gemini (fallback cloud - FLASH por defecto)
        try:
            from gemini import GeminiProvider
            self.providers["gemini"] = GeminiProvider
            self.providers["gemini-flash"] = GeminiProvider
            self.providers["gemini-1.5-flash"] = GeminiProvider
            self.providers["gemini-3-flash"] = GeminiProvider
            self.providers["gemini_vertex_flash_3"] = GeminiProvider
            self.providers["gemini-pro"] = GeminiProvider
        except ImportError:
            logger.debug("GeminiProvider no disponible")
    
    def get_provider(self, name: str, **kwargs):
        """Obtiene instancia de un provider."""
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' no registrado. Disponibles: {list(self.providers.keys())}")
        return self.providers[name](**kwargs)
    
    def create_with_fallback(self, primary: str, fallback: str, **kwargs) -> Dict[str, Any]:
        """
        Intenta crear instancia del provider primario; si falla, usa fallback.
        
        Retorna: {
            "provider": instance,
            "name": nombre_usado,
            "fallback": bool,
            "cost": float (0.0 si local)
        }
        """
        try:
            prov = self.get_provider(primary, **kwargs)
            return {
                "provider": prov,
                "name": primary,
                "fallback": False,
                "cost": 0.0 if primary == "ollama" else "$var"
            }
        except Exception as e:
            logger.debug(f"[FALLBACK] {primary} falló: {e}. Usando {fallback}.")
            try:
                prov = self.get_provider(fallback, **kwargs)
                return {
                    "provider": prov,
                    "name": fallback,
                    "fallback": True,
                    "cost": 0.0 if fallback == "ollama" else "$var"
                }
            except Exception as e2:
                raise RuntimeError(f"Ambos providers fallaron: {primary}={e}, {fallback}={e2}")
    
    def create_smart_hybrid(
        self,
        max_daily_spend: float = 114.53,
        fallback_to_gemini: bool = True,
        gemini_model: str = "gemini-3-flash"  # Flash v3 por defecto (Superior Calidad)
    ) -> Dict[str, Any]:
        """
        Selecciona provider inteligentemente basado en presupuesto disponible.
        
        Estrategia:
        1. Intenta Ollama primero (siempre, $0 costo)
        2. Si Ollama falla y fallback_to_gemini=True:
           - Verifica presupuesto con cost_limiter
           - Si presupuesto OK: usa Gemini Flash (económico)
           - Si presupuesto bajo: rechaza y falla
        3. Si todo falla: excepción
        
        Retorna: {
            "provider": instance,
            "mode": "local" | "hybrid_fallback",
            "model": "ollama" | "gemini-1.5-flash" | "gemini-2.5-pro",
            "cost": "$0" | "$~0.025/1K" | "$~0.15/1K"
        }
        """
        # Intentar Ollama primero
        try:
            from ollama_provider import OllamaProvider
            prov = OllamaProvider()
            prov.health_check()  # Verifica conectividad
            return {
                "provider": prov,
                "mode": "local",
                "model": "ollama",
                "cost": "$0",
                "description": "Local (cero costo)"
            }
        except Exception as e:
            logger.debug(f"Ollama no disponible: {e}")
        
        # Fallback a Gemini si se permite
        if not fallback_to_gemini:
            raise RuntimeError("Ollama unavailable and fallback_to_gemini=False")
        
        # Verificar presupuesto para Gemini
        if self.cost_limiter:
            can_use, est_cost, reason = self.cost_limiter.can_use_gemini(
                model=gemini_model,
                input_tokens=1000,  # Estimación típica
                output_tokens=1000,
                enforce=True
            )
            logger.debug(f"Budget check: {reason}")
            if not can_use:
                raise RuntimeError(f"Presupuesto insuficiente: {reason}")
        
        # Crear Gemini
        try:
            from gemini import GeminiProvider
            prov = GeminiProvider(
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "project-d72bb17e-5918-431c-ba5"),
                model=gemini_model,
                enforce_budget=True
            )
            cost_desc = "$~0.025/1K" if "flash" in gemini_model else "$~0.15/1K"
            return {
                "provider": prov,
                "mode": "hybrid_fallback",
                "model": gemini_model,
                "cost": cost_desc,
                "description": f"Gemini {gemini_model} (fallback, con costo)"
            }
        except Exception as e:
            raise RuntimeError(f"Gemini también falló: {e}")


# Registry global
_registry = ProviderRegistry()


def get_provider(name: str, **kwargs):
    """Obtiene un provider por nombre."""
    return _registry.get_provider(name, **kwargs)


def create_with_fallback(primary: str, fallback: str, **kwargs):
    """Crea provider con fallback automático."""
    return _registry.create_with_fallback(primary, fallback, **kwargs)


def create_local_only(primary: str = "ollama", **kwargs):
    """
    Crea provider usando SOLO modelos locales (sin costes).
    fallback: ollama → (RKLLM en el futuro)
    NO usa Gemini ni ningún servicio cloud.
    """
    logger.info("Modo LOCAL-ONLY: sin costes, solo modelos locales.")
    return _registry.create_with_fallback(
        primary=primary,
        fallback="ollama",  # fallback dentro de local
        **kwargs
    )


def create_smart_hybrid(**kwargs):
    """
    Crea provider inteligentemente con fallback a Gemini si presupuesto lo permite.
    Modo recomendado para máxima optimización.
    """
    logger.info("Modo SMART HYBRID: Ollama primero, Gemini si presupuesto OK")
    return _registry.create_smart_hybrid(**kwargs)


if __name__ == "__main__":
    # Test: modo local-only (SIN COSTES)
    logger.info("Testing provider registry (LOCAL-ONLY)...")
    result = create_local_only(base_url="http://localhost:11434")
    logger.info(f"Provider usado: {result['name']} (fallback={result['fallback']})")
    logger.info(f"Costo: {result.get('cost', 'N/A')}")
    logger.info("Este modo NO genera costes en GCP.")

