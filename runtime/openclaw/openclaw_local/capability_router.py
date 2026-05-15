import os
import json
import hashlib
from enum import Enum
from pathlib import Path
from typing import Any, Optional

class HardwareIntent(Enum):
    SYSTEM_1 = "npu_low_latency"  # Edge, fast, low power
    SYSTEM_2 = "gpu_high_compute" # PC, slow, complex reasoning
    HYBRID = "dynamic_escalation" # Start in S1, escalate to S2 if needed

class CapabilityRouter:
    """
    Capability Router (Phase III - ISSUE-0046).
    Orquestador de hardware basado en la filosofía Sistema 1 / Sistema 2.
    """
    
    def __init__(self, repo_root: Path):
        self.root = repo_root
        self.pc_index_path = self.root / "runtime/pc_control/benchmarks/index.json"
        self.edge_index_path = self.root / "runtime/edge_iot/benchmarks/index.json"

    def determine_intent(self, task_complexity: str, domain: str, request_kind: str) -> HardwareIntent:
        """Determina la intención de hardware basada en la naturaleza de la tarea."""
        
        # Tareas pesadas o críticas van a Sistema 2 (PC)
        if task_complexity in ["high", "critical"] or domain == "academico":
            return HardwareIntent.SYSTEM_2
            
        # Tareas de gestión, IoT o charlas rápidas van a Sistema 1 (Edge)
        if domain in ["edge", "iot"] or request_kind in ["fast_command", "status"]:
            return HardwareIntent.SYSTEM_1
            
        # Por defecto, escalación dinámica
        return HardwareIntent.HYBRID

    def route_task(self, task_data: dict) -> dict:
        """
        Calcula la ruta óptima para una tarea.
        Incluye integridad matemática mediante hash de decisión.
        """
        complexity = task_data.get("complexity", "medium")
        domain = task_data.get("domain", "general")
        kind = task_data.get("request_kind", "general")
        
        intent = self.determine_intent(complexity, domain, kind)
        
        # Leer benchmarks (simplificado para este script)
        pc_online = os.getenv("OPENCLAW_PC_ONLINE", "1") == "1"
        edge_online = os.getenv("OPENCLAW_EDGE_ONLINE", "1") == "1"
        
        decision = {
            "intent": intent.value,
            "target_node": "pc" if intent == HardwareIntent.SYSTEM_2 or not edge_online else "edge",
            "fallback_node": "pc" if intent == HardwareIntent.SYSTEM_1 else "cloud",
            "timestamp": str(os.times().elapsed),
        }
        
        # Integridad matemática: Hash de la decisión
        decision_str = json.dumps(decision, sort_keys=True)
        decision["integrity_hash"] = hashlib.sha256(decision_str.encode()).hexdigest()
        
        return decision

if __name__ == "__main__":
    # Test
    router = CapabilityRouter(Path("."))
    test_task = {"complexity": "high", "domain": "academico", "request_kind": "research"}
    print(json.dumps(router.route_task(test_task), indent=2))
