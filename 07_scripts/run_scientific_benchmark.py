import json
import time
from standardized_benchmark_runner import StandardizedRunner

CATEGORIES = [
    {"id": "iot_critical_control", "name": "Control Crítico IoT", "prompt": "ANOMALÍA: Sobrepresión en caldera B-01 (120 PSI). Válvula de alivio no responde. ¿Protocolo de parada de emergencia en 3 pasos?"},
    {"id": "iot_telemetry_extraction", "name": "Extracción de Telemetría", "prompt": "RAW_DATA: [ID:045, T:85.5C, P:1013hPa, H:45%, STATUS:ALARM]. Extrae los valores numéricos en un JSON estructurado."},
    {"id": "iot_edge_rag", "name": "RAG de Normativa IoT", "prompt": "Según el estándar ISO/IEC 30141, define brevemente la responsabilidad del 'Trustworthiness' en un Edge Gateway."},
    {"id": "iot_embedded_logic", "name": "Lógica Embebida IoT", "prompt": "Escribe una función en C++ para Arduino que lea un sensor analógico en A0 y active un relay en D7 si el valor supera 800."},
    {"id": "iot_sovereignty_reasoning", "name": "Razonamiento de Soberanía", "prompt": "Analiza las ventajas de procesar datos de salud (IoT Wearables) localmente en el Edge vs enviarlos a una nube pública bajo GDPR."},
]

def run_master_benchmark():
    print("====================================================")
    print("   SIOT MASTER SCIENTIFIC BENCHMARK (PEV-01)        ")
    print("====================================================\n")
    
    results = []
    
    for cat in CATEGORIES:
        runner = StandardizedRunner(cat["name"], cat["prompt"], cat["id"])
        result = runner.execute()
        results.append(result)
        print("\n" + "-"*50 + "\n", flush=True)
        # Cool down entre categorías para estabilidad térmica
        time.sleep(2)
        
    final_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware": "Orange Pi 5 Plus (RK3588)",
        "model": "Llama-3.2-3B-Instruct",
        "results": results
    }
    
    with open("runtime/edge_iot/benchmarks/scientific_report_v2_hardened.json", "w") as f:
        json.dump(final_report, f, indent=4)
        
    print("\n[FIN] Master Benchmark Científico (V2-Hardened) completado.")
    print("Reporte de alta precisión generado en: runtime/edge_iot/benchmarks/scientific_report_v2_hardened.json")

if __name__ == "__main__":
    run_master_benchmark()
