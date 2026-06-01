import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import time
import os
import json
import math

from standardized_benchmark_runner import StandardizedRunner
import standardized_benchmark_runner

def test_timer_precision():
    print("[META-TEST] Validando resolución del reloj (perf_counter)...")
    start = time.perf_counter()
    time.sleep(0.01)
    end = time.perf_counter()
    diff = (end - start) * 1000
    print(f"  -> Delta medido para 10ms: {diff:.4f}ms")
    # Si la resolución es menor a 0.1ms, se considera excelente para este benchmark
    assert 9.0 < diff < 15.0, "Falla en precisión de temporización básica"
    print("[OK] Temporización validada.")

def test_math_sanity():
    print("[META-TEST] Validando motor estadístico (Media/StdDev/Confianza)...")
    original_identity = standardized_benchmark_runner.benchmark_identity.get_full_identity
    standardized_benchmark_runner.benchmark_identity.get_full_identity = lambda runtime, model: {
        "node_name": "meta-test",
        "os": "meta-test",
        "arch": "meta-test",
        "cpu": "meta-test",
        "gpu": "meta-test",
        "npu": "meta-test",
        "python": sys.version.split()[0],
        "model": {"requested": model, "actual": model, "status": "verified"},
    }
    runner = StandardizedRunner("Test", "Prompt", "test")
    standardized_benchmark_runner.benchmark_identity.get_full_identity = original_identity
    # Feed known samples
    runner.samples = [
        {"latency_ms": 100, "tps": 10, "status": "REAL"},
        {"latency_ms": 110, "tps": 10, "status": "REAL"},
        {"latency_ms": 90, "tps": 10, "status": "REAL"},
        {"latency_ms": 105, "tps": 10, "status": "REAL"},
        {"latency_ms": 95, "tps": 10, "status": "REAL"}
    ]
    res = runner.analyze()
    
    # Media esperada: 100
    assert res["mean_latency_ms"] == 100.0, f"Error en media: {res['mean_latency_ms']}"
    # StdDev esperada: sqrt(((0)^2 + (10)^2 + (-10)^2 + (5)^2 + (-5)^2) / 5) = sqrt(250/5) = sqrt(50) ~= 7.07
    assert 7.0 < res["std_dev_lat"] < 7.1, f"Error en StdDev: {res['std_dev_lat']}"
    print("[OK] Cálculos estadísticos validados.")

def test_atomic_persistence():
    print("[META-TEST] Validando integridad de escritura atómica...")
    test_log = "runtime/edge_iot/benchmarks/test_integrity.jsonl"
    if os.path.exists(test_log): os.remove(test_log)
    
    # Importar y modificar OUTPUT_LOG para el test
    original_log = standardized_benchmark_runner.OUTPUT_LOG
    original_post = standardized_benchmark_runner.requests.post
    original_update_index = standardized_benchmark_runner.update_index
    original_run_log_path = standardized_benchmark_runner.run_log_path
    original_identity = standardized_benchmark_runner.benchmark_identity.get_full_identity
    test_scientific_log = "runtime/edge_iot/benchmarks/test_scientific_integrity.jsonl"
    standardized_benchmark_runner.OUTPUT_LOG = test_log
    standardized_benchmark_runner.ITERATIONS = 1
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"tps": 10.0}

    standardized_benchmark_runner.requests.post = lambda *args, **kwargs: FakeResponse()
    standardized_benchmark_runner.update_index = lambda *args, **kwargs: None
    standardized_benchmark_runner.run_log_path = lambda node, run_id: Path(test_scientific_log)
    standardized_benchmark_runner.benchmark_identity.get_full_identity = lambda runtime, model: {
        "node_name": "meta-test",
        "os": "meta-test",
        "arch": "meta-test",
        "cpu": "meta-test",
        "gpu": "meta-test",
        "npu": "meta-test",
        "python": sys.version.split()[0],
        "model": {"requested": model, "actual": model, "status": "verified"},
    }
    try:
        runner = StandardizedRunner("Integrity Test", "Prompt", "test")
        res = runner.execute()

        assert os.path.exists(test_log), "El archivo no fue creado."
        with open(test_log, "r") as f:
            line = f.readline()
            data = json.loads(line)
            assert "integrity_hash" in data, "Falta hash de integridad."
            assert data["mean_latency_ms"] == res["mean_latency_ms"], "Datos en archivo no coinciden con resultado de ejecución."
    finally:
        standardized_benchmark_runner.OUTPUT_LOG = original_log
        standardized_benchmark_runner.requests.post = original_post
        standardized_benchmark_runner.update_index = original_update_index
        standardized_benchmark_runner.run_log_path = original_run_log_path
        standardized_benchmark_runner.benchmark_identity.get_full_identity = original_identity
        if os.path.exists(test_log):
            os.remove(test_log)
        if os.path.exists(test_scientific_log):
            os.remove(test_scientific_log)
    print("[OK] Persistencia atómica validada.")

if __name__ == "__main__":
    print("====================================================")
    print("   SIOT SCIENTIFIC VALIDATION SUITE (META-TESTS)    ")
    print("====================================================\n")
    try:
        test_timer_precision()
        test_math_sanity()
        test_atomic_persistence()
        print("\n[ÉXITO] Todas las garantías científicas han pasado la auditoría.")
    except Exception as e:
        print(f"\n[FALLO] Violación de rigor científico detectada: {e}")
        sys.exit(1)
