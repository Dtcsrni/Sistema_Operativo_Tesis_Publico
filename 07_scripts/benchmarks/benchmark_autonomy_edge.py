import sys
import json
import time
import subprocess
import statistics
import math
from pathlib import Path
from system_sanitizer import SystemSanitizer

# <!-- SISTEMA_TESIS:PROTEGIDO -->

N_ITERATIONS = 3

AUTONOMY_TASKS = [
    {"id": "BATTERY_STRATEGY", "prompt": "SISTEMA: Batería al 12%. ¿Qué servicios apagar para sobrevivir 24h?", "expected_keywords": ["apagar", "ahorro", "energía"]},
    {"id": "RAM_CRUNCH_RECOVERY", "prompt": "SISTEMA: RAM al 96%. ¿Qué proceso sacrificar?", "expected_keywords": ["proceso", "kill", "prioridad"]},
    {"id": "HARDWARE_HEALTH", "prompt": "SISTEMA: Temperatura SoC a 82°C. ¿Estrategia de throttling?", "expected_keywords": ["throttling", "frecuencia", "temperatura"]},
    {"id": "ISOLATION_PLAN", "prompt": "SISTEMA: Sin enlace con PC. ¿Protocolo de sincronización local?", "expected_keywords": ["local", "sincronización", "almacenamiento"]}
]

def calculate_stats(data: list[float]):
    if not data: return {"mean": 0, "std_dev": 0}
    if len(data) < 2: return {"mean": data[0], "std_dev": 0}
    return {"mean": round(statistics.mean(data), 2), "std_dev": round(statistics.stdev(data), 2)}

def run_edge_benchmark():
    print("--- Iniciando Benchmark de Resiliencia con Rigor Estadístico (Edge) ---")
    sanitizer = SystemSanitizer()
    sanitizer.sanitize() # Limpiar procesos no esenciales en el Orange Pi
    
    model_path = "/home/tesisai/Sistema_Operativo_Tesis_Posgrado/runtime/models/edge/qwen2.5_1.5b_rkllm.rkllm"
    ollama_model = "qwen2.5:0.5b"
    
    results = []
    for task in AUTONOMY_TASKS:
        print(f"  [TASK: {task['id']}]")
        latencies = []
        providers = []
        
        for i in range(N_ITERATIONS):
            start_time = time.perf_counter()
            provider = "NPU (RKLLM)"
            
            try:
                # Intentar NPU
                cmd = ["python3", "/home/tesisai/Sistema_Operativo_Tesis_Posgrado/07_scripts/ai_tools/rkllm_inference.py", "--model", model_path, "--prompt", task["prompt"]]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
                if proc.returncode != 0: raise RuntimeError("NPU Fail")
                stdout = proc.stdout
            except Exception:
                # Failover a CPU
                provider = "CPU (Ollama)"
                cmd = ["ollama", "run", ollama_model, task["prompt"]]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                stdout = proc.stdout
            
            duration_ms = (time.perf_counter() - start_time) * 1000
            latencies.append(duration_ms)
            providers.append(provider)
            print(f"    Pass {i+1}: {provider} | {round(duration_ms/1000, 2)}s")

        stats = calculate_stats(latencies)
        results.append({
            "task_id": task["id"],
            "stats": stats,
            "provider_mix": providers,
            "success": any(kw.lower() in stdout.lower() for kw in task["expected_keywords"]),
            "noise_sample": sanitizer.get_background_noise()
        })

    report_path = Path("runtime/edge_iot/benchmarks/autonomy_report_statistical.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[SUCCESS] Benchmark completado. Reporte: {report_path}")

if __name__ == "__main__":
    run_edge_benchmark()
