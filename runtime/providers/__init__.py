"""
Sistema de selección de providers local-first.
- Intenta usar el provider preferido (p. ej. ollama).
- No registra Gemini ni proveedores cloud pagados como fallback automático.
- Registra en auditoría qué provider local se usó.
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
        self._register_defaults()

    def _register_defaults(self):
        """Registra los providers disponibles."""
        # Ollama (default local)
        try:
            from ollama_provider import OllamaProvider
            self.providers["ollama"] = OllamaProvider
        except ImportError:
            logger.debug("OllamaProvider no disponible")
        
        logger.debug("Providers cloud pagados deshabilitados por política local-first")
    
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
        fallback_to_gemini: bool = False,
        gemini_model: str = ""
    ) -> Dict[str, Any]:
        """
        Selecciona provider local. Mantiene la firma histórica por compatibilidad,
        pero no ejecuta Gemini ni ningún fallback cloud pagado.
        
        Estrategia:
        1. Intenta Ollama primero (siempre, $0 costo).
        2. Si Ollama falla, lanza excepción para evitar gasto cloud accidental.
        
        Retorna: {
            "provider": instance,
            "mode": "local",
            "model": "ollama",
            "cost": "$0"
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
        
        raise RuntimeError("Ollama unavailable; cloud paid fallbacks disabled by local-first policy")


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
    Crea provider local-only. Nombre histórico conservado por compatibilidad.
    """
    logger.info("Modo LOCAL-FIRST: Ollama primero, sin Gemini ni cloud pagado")
    return _registry.create_smart_hybrid(**kwargs)


if __name__ == "__main__":
    # Test: modo local-only (SIN COSTES)
    logger.info("Testing provider registry (LOCAL-ONLY)...")
    result = create_local_only(base_url="http://localhost:11434")
    logger.info(f"Provider usado: {result['name']} (fallback={result['fallback']})")
    logger.info(f"Costo: {result.get('cost', 'N/A')}")
    logger.info("Este modo NO genera costes en GCP.")

