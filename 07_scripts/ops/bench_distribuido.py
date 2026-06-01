import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Setup paths
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

def run_command(cmd, desc):
    print(f"\n>>> {desc}...")
    print(f"Comando: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[FAIL] {desc}")
        print(result.stderr)
        return None
    print(f"[OK] {desc}")
    return result.stdout

def get_latest_benchmark_result(node):
    if node == "pc":
        index_path = ROOT / "runtime" / "pc_control" / "benchmarks" / "index.json"
    else:
        index_path = ROOT / "runtime" / "edge_iot" / "benchmarks" / "index.json"
    
    if not index_path.exists():
        return None
    
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data

def main():
    print("=== SIOT: Benchmark Distribuido (PC vs Edge) ===")
    
    # 1. Ejecutar PC Benchmark (Muestra reducida para velocidad)
    run_command(
        [sys.executable, "07_scripts/benchmarks/run_pc_benchmark.py", "--iterations", "3", "--warmups", "1", "--step-id", "VAL-STEP-753"],
        "Ejecutando Benchmark en PC (GPU/CPU)"
    )
    
    # 2. Ejecutar Edge Benchmark (Ollama CPU via SSH)
    run_command(
        [sys.executable, "07_scripts/benchmarks/trigger_edge_npu_benchmark.py", "--model", "qwen:0.5b", "--step-id", "VAL-STEP-753"],
        "Ejecutando Benchmark en Edge (Orange Pi CPU)"
    )
    
    # 3. Recolectar Resultados
    pc_data = get_latest_benchmark_result("pc")
    edge_data = get_latest_benchmark_result("edge")
    
    if not pc_data or not edge_data:
        print("[ERROR] No se pudieron recolectar todos los resultados.")
        return 1
    
    # 4. Mostrar Comparativa
    print("\n" + "="*50)
    print("  COMPARATIVA DE RENDIMIENTO DISTRIBUIDO")
    print("="*50)
    
    pc_stats = pc_data.get("statistics", {})
    # Edge data structure varies, we check benchmark_latest.json too
    edge_latest_path = ROOT / "runtime" / "edge_iot" / "benchmarks" / "benchmark_latest.json"
    if edge_latest_path.exists():
        with open(edge_latest_path, "r", encoding="utf-8") as f:
            edge_full = json.load(f)
            edge_stats = edge_full.get("ollama_cpu_benchmark", {}).get("summary", {})
    else:
        edge_stats = {}

    print(f"{'Métrica':<25} | {'PC (Primary)':<15} | {'Edge (Ollama)':<15}")
    print("-" * 60)
    print(f"{'Tokens/sec (Avg)':<25} | {pc_stats.get('mean_tokens_per_second', 'N/A'):<15} | {edge_stats.get('avg_tps', 'N/A'):<15}")
    print(f"{'Latencia (Avg ms)':<25} | {pc_stats.get('mean_latency_ms', 'N/A'):<15} | {edge_stats.get('avg_latency_ms', 'N/A'):<15}")
    print(f"{'Modelo':<25} | {pc_data.get('primary_pc_model', 'N/A'):<15} | {edge_full.get('ollama_cpu_benchmark', {}).get('model', 'N/A'):<15}")
    print("="*50)

    # 5. Recomendación de Enrutamiento
    print("\n[ROUTING] Recomendación basada en datos:")
    pc_tps = pc_stats.get('mean_tokens_per_second', 0)
    edge_tps = edge_stats.get('avg_tps', 0)
    
    if pc_tps > edge_tps * 2:
        print("  -> Tareas de Alta Complejidad: PC (GPU)")
    else:
        print("  -> Tareas de Alta Complejidad: PC (GPU) [Revisar cuello de botella]")
        
    print("  -> Tareas de Baja Latencia / Edge: NPU (Pendiente Promoción)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
