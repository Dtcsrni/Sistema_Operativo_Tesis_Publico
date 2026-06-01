import os
import json
import time
import requests
import statistics
import math
from datetime import datetime
from system_sanitizer import SystemSanitizer

# <!-- SISTEMA_TESIS:PROTEGIDO -->

# Configuración de Rigor Estadístico
N_ITERATIONS = 3  # Número de pasadas por tarea para estabilizar la varianza
CONFIDENCE_LEVEL = 0.95

TASKS = [
    {"id": "IOT_PARSING", "category": "Functional Suitability / Accuracy", "prompt": "Analiza este log de LoRaWAN y extrae el JSON con GPS y RSSI: 'GW:01, RSSI:-105, DATA:40.7128,-74.0060'", "expected_keywords": ["40.7128", "-74.006", "-105"], "iso_25059_characteristic": "Functional Suitability"},
    {"id": "EMBEDDED_CODE", "category": "Maintainability / Modularity", "prompt": "Genera una función setup() en C++ para un ESP32 con RadioLib y SX1262 usando SPI pins: SCK:5, MISO:19, MOSI:27, SS:18.", "expected_keywords": ["void setup", "SPI.begin", "RadioLib", "SX1262"], "iso_25059_characteristic": "Maintainability"},
    {"id": "ACADEMIC_SYNTHESIS", "category": "Functional Suitability / Completeness", "prompt": "Resume el impacto de la IA en el borde (Edge AI) para dispositivos IoT en un párrafo académico siguiendo normas APA 7.", "expected_keywords": ["latencia", "privacidad", "borde", "IoT"], "iso_25059_characteristic": "Functional Suitability"},
    {"id": "LOGISTICS_REASONING", "category": "Reliability / Robustness", "prompt": "Planea una ruta óptima desde Reloj Monumental de Pachuca a Zona Plateada evitando el Boulevard Colosio.", "expected_keywords": ["Pachuca", "ruta", "tráfico"], "iso_25059_characteristic": "Reliability"},
    {"id": "PRIVACY_AUDIT", "category": "Sovereignty / Privacy", "prompt": "Audita este log en busca de PII o secretos: 'User erick_vega (phone: 55-1234-5678) logged in from 192.168.1.5'", "expected_keywords": ["PII", "teléfono", "privacidad"], "iso_25059_characteristic": "Privacy"}
]

def calculate_stats(data: list[float]):
    if len(data) < 2:
        return {"mean": data[0] if data else 0, "std_dev": 0, "ci_low": 0, "ci_high": 0}
    
    mean = statistics.mean(data)
    std_dev = statistics.stdev(data)
    # t-value aproximado para N=3-5
    t_val = 2.776 if len(data) == 3 else 2.132
    margin_error = t_val * (std_dev / math.sqrt(len(data)))
    
    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "ci_low": round(mean - margin_error, 2),
        "ci_high": round(mean + margin_error, 2)
    }

def run_task(task, sanitizer: SystemSanitizer):
    url = "http://127.0.0.1:11434/api/generate"
    latencies = []
    tps_values = []
    responses = []
    
    print(f"\n  [TASK: {task['id']}]")
    
    for i in range(N_ITERATIONS):
        # Capturar ruido de fondo antes de cada iteración
        noise_before = sanitizer.get_background_noise()
        
        payload = {
            "model": "qwen2.5:7b-instruct",
            "prompt": task["prompt"],
            "stream": False
        }
        
        start_time = time.perf_counter()
        try:
            response = requests.post(url, json=payload, timeout=120)
        except requests.exceptions.Timeout:
            print(f"    Pass {i+1}: TIMEOUT")
            continue
        end_time = time.perf_counter()
        
        latency = (end_time - start_time) * 1000
        latencies.append(latency)
        
        if response.status_code == 200:
            res_json = response.json()
            full_text = res_json.get("response", "")
            eval_count = res_json.get("eval_count", 0)
            eval_duration = res_json.get("eval_duration", 1) / 1e9 # ns to s
            tps = eval_count / eval_duration
            tps_values.append(tps)
            responses.append(full_text)
            print(f"    Pass {i+1}: {round(tps, 2)} TPS | {round(latency, 2)}ms")
        else:
            print(f"    Pass {i+1}: FAILED (HTTP {response.status_code})")

    # Análisis estadístico
    latency_stats = calculate_stats(latencies)
    tps_stats = calculate_stats(tps_values)
    
    # Verificación de precisión (Accuracy)
    last_response = responses[-1] if responses else ""
    is_accurate = any(kw.lower() in last_response.lower() for kw in task["expected_keywords"])
    
    return {
        "task_id": task["id"],
        "latency": latency_stats,
        "tps": tps_stats,
        "accuracy": "ok" if is_accurate else "failed_accuracy",
        "noise_sample": noise_before
    }

def main():
    print("--- Iniciando Benchmark ISO/IEC 25059 con Rigor Estadístico ---")
    sanitizer = SystemSanitizer()
    sanitizer.sanitize() # Limpiar procesos no esenciales
    
    run_id = f"RUN-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    results = []
    
    for task in TASKS:
        res = run_task(task, sanitizer)
        results.append(res)
        
    # Guardar resultados
    report_path = f"v:/Sistema_Operativo_Tesis_Posgrado/runtime/pc_control/benchmarks/runs/{run_id}_statistical.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    report = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "iterations": N_ITERATIONS,
        "confidence_level": CONFIDENCE_LEVEL,
        "results": results
    }
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
        
    print(f"\n[SUCCESS] Benchmark completado. Reporte guardado en: {report_path}")

if __name__ == "__main__":
    main()
