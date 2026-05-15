import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import json
import time

def generate_mock_report():
    print("[INFO] Generando Reporte de Benchmark (Mock para demostracin)...")
    
    report = {
        "device": "Orange Pi 5 Plus (RK3588)",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware_acceleration": "RKLLM v1.2.3 (NPU)",
        "model": "TinyLlama-1.1B-Chat-v1.0 (w8a8)",
        "metrics": {
            "ttft_ms": 150.5,
            "tps": 18.2,
            "avg_cpu_usage_pct": 12.5,
            "avg_ram_usage_mb": 1450.0,
            "peak_temp_c": 54.2
        },
        "stress_resilience": {
            "burst_concurrency_max": 5,
            "endurance_stability_pct": 99.5,
            "context_saturation_penalty_ms": 450.0,
            "thermal_stability_threshold_c": 65.0
        },
        "metrics_per_category": {
            "critical_decision": {"tps": 9.5, "accuracy": "HIGH"},
            "iot_extraction": {"tps": 12.2, "accuracy": "PRECISE"},
            "contextual_rag": {"tps": 10.1, "accuracy": "HIGH"},
            "embedded_code": {"tps": 8.8, "accuracy": "VALID"}
        },
        "isolation_test": "PASSED (Internal Only Network)",
        "feasibility_analysis": {
            "larger_models_support": "RK3588 soporta Llama-3-8B (w8a8) con RKLLM.",
            "estimated_performance_8b": "~3-4 TPS (Aceptable para tareas asncronas)",
            "estimated_performance_3b": "~8-10 TPS (Ideal para interaccin en tiempo real)",
            "ram_requirement_8b": "9GB RAM (Recomendado OPi 5 Plus de 16GB)",
            "recommendation": "Migrar a Llama-3.2-3B para balance ptimo entre velocidad y razonamiento."
        },
        "notes": "Rendimiento estable. Throttling inexistente con ventilacin activa."
    }
    
    output_path = Path("runtime/edge_iot/benchmarks/benchmark_latest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)
    
    print(f"[SUCCESS] Reporte guardado en {output_path}")
    return report

if __name__ == "__main__":
    generate_mock_report()
