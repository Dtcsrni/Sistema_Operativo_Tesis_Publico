import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import time
import requests
import threading
import json
import os

# --- Configuration ---
INFERENCE_URL = "http://localhost:8080/chat"

class RigorousStressTester:
    def __init__(self):
        self.results = {}

    def test_context_saturation(self):
        print("[STRESS] Test A: Saturación de Contexto (Long Context)...")
        # Generamos un prompt largo (~800 tokens)
        long_context = "Repite esta frase mil veces: 'Resiliencia IoT'. " * 100
        prompt = f"{long_context} Ahora, resume la importancia de la resiliencia en 5 palabras."
        
        start = time.time()
        try:
            resp = requests.post(INFERENCE_URL, json={"prompt": prompt}, timeout=30)
            elapsed = time.time() - start
            print(f"[PASS] Latencia con contexto saturado: {elapsed:.1f}s")
            return elapsed
        except:
            print("[FAIL] Timeout o error en contexto largo.")
            return None

    def test_burst_load(self, concurrent_reqs=5):
        print(f"[STRESS] Test B: Ráfaga de Carga ({concurrent_reqs} concurrentes)...")
        threads = []
        errors = 0
        
        def send_req():
            nonlocal errors
            try:
                requests.post(INFERENCE_URL, json={"prompt": "Hola"}, timeout=10)
            except:
                errors += 1

        for _ in range(concurrent_reqs):
            t = threading.Thread(target=send_req)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
            
        print(f"[RESULT] Ráfaga finalizada con {errors} errores.")
        return errors

    def test_endurance(self, iterations=20):
        print(f"[STRESS] Test C: Resistencia (Endurance - {iterations} loops)...")
        latencies = []
        for i in range(iterations):
            start = time.time()
            try:
                requests.post(INFERENCE_URL, json={"prompt": "Test loop"}, timeout=10)
                latencies.append(time.time() - start)
            except:
                print(f"[FAIL] Error en loop {i}")
        
        avg = sum(latencies)/len(latencies) if latencies else 0
        print(f"[PASS] Latencia media en resistencia: {avg:.2f}s")
        return avg

    def run_all(self):
        print("=== INICIANDO STRESS TEST RIGUROSO (RK3588) ===")
        self.results["context_latency"] = self.test_context_saturation()
        self.results["burst_errors"] = self.test_burst_load()
        self.results["endurance_avg"] = self.test_endurance()
        
        output_path = "runtime/edge_iot/benchmarks/stress_results.json"
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=4)
        print(f"=== FIN. Resultados en {output_path} ===")

if __name__ == "__main__":
    tester = RigorousStressTester()
    tester.run_all()
