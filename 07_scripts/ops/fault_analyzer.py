import subprocess
import re
from pathlib import Path

class FaultAnalyzer:
    """Motor de diagnóstico para la detección y clasificación de fallos en el pipeline."""
    
    @staticmethod
    def check_oom() -> bool:
        """Busca evidencias de Out Of Memory en el kernel del host (WSL)."""
        try:
            # Escaneamos dmesg buscando patrones de OOM-Killer
            output = subprocess.check_output(
                ["wsl", "dmesg"], stderr=subprocess.DEVNULL, timeout=10
            ).decode(errors="replace")
            return "Out of memory" in output or "oom_reaper" in output
        except subprocess.CalledProcessError:
            return False
        except FileNotFoundError:
            # WSL no disponible en este entorno
            return False
        except Exception:
            return False

    @staticmethod
    def analyze_python_error(stderr_text: str) -> str:
        """Clasifica errores basados en tracebacks de Python."""
        if "MemoryError" in stderr_text:
            return "OOM_PYTHON"
        if "CUDA out of memory" in stderr_text or "out of memory" in stderr_text.lower():
            return "OOM_CUDA"
        if "Segmentation fault" in stderr_text or "SIGSEGV" in stderr_text:
            return "SEGFAULT"
        if "ConnectionError" in stderr_text or "Connection reset by peer" in stderr_text:
            return "NETWORK_ERROR"
        if "No space left on device" in stderr_text:
            return "DISK_FULL"
        if "unexpected keyword argument" in stderr_text:
            return "API_MISMATCH"
        return "UNKNOWN_FAILURE"

    @staticmethod
    def get_recovery_strategy(error_type: str, current_phase: int) -> dict:
        """Determina la mejor acción correctiva según el tipo de error y fase del pipeline.

        Fase 1 = Sanitización | Fase 2 = Conversión | Fase 3 = Sincronización Edge
        """
        # Estrategias base (independientes de fase)
        base_strategies = {
            "OOM_PYTHON": {
                "action": "PIVOT_TO_GGUF",
                "reason": "La RAM física no soporta el formato FP16/HuggingFace."
            },
            "OOM_CUDA": {
                "action": "REDUCE_BATCH_SIZE",
                "reason": "VRAM insuficiente; reducir batch_size o usar offload a CPU."
            },
            "SEGFAULT": {
                "action": "PIVOT_TO_GGUF",
                "reason": "Posible corrupción de pesos o incompatibilidad rkllm-toolkit."
            },
            "NETWORK_ERROR": {
                "action": "RETRY_WITH_BACKOFF",
                "reason": "Interrupción temporal de la conexión."
            },
            "DISK_FULL": {
                "action": "CLEAN_WORKSPACE",
                "reason": "Saturación de almacenamiento en /mnt/v/."
            },
            "API_MISMATCH": {
                "action": "CODE_PATCH_REQUIRED",
                "reason": "Incompatibilidad entre scripts y rkllm-toolkit."
            },
        }

        # Overrides específicos por (error_type, fase) — mayor precisión diagnóstica
        phase_overrides: dict[tuple, dict] = {
            ("NETWORK_ERROR", 3): {
                "action": "RETRY_SYNC_SSH",
                "reason": "Fallo de conectividad SSH durante sincronización al nodo Edge (OPi5)."
            },
            ("DISK_FULL", 2): {
                "action": "PURGE_GGUF_CACHE",
                "reason": "Disco lleno durante conversión; eliminar GGUF temporal antes de reintentar."
            },
            ("SEGFAULT", 2): {
                "action": "DOWNGRADE_RKLLM_TOOLKIT",
                "reason": "Segfault en conversión; posible bug en versión actual de rkllm-toolkit."
            },
        }

        override = phase_overrides.get((error_type, current_phase))
        if override:
            return override
        return base_strategies.get(error_type, {"action": "STOP", "reason": "Fallo no clasificado."})
