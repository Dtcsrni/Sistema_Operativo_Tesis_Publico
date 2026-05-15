import time
import psutil
import os
import json
from pathlib import Path
import sys

# Asegurar que los módulos del sistema son cargables
from toltecayotl.ingestor_toltecayotl import IngestorToltecayotl

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # MB

def run_benchmark(file_path: str):
    path = Path(file_path)
    if not path.exists():
        print(f"[ERROR] Archivo no encontrado: {file_path}")
        return

    print(f"--- Inicia Benchmark de Ingesta Toltecayotl ---")
    print(f"Archivo: {path.name}")
    print(f"Tamaño: {path.stat().st_size / 1024:.2f} KB")

    start_mem = get_memory_usage()
    start_time = time.time()

    ingestor = IngestorToltecayotl(path)
    fragmentos = ingestor.ejecutar_ingesta()

    end_time = time.time()
    end_mem = get_memory_usage()

    duration = end_time - start_time
    mem_diff = end_mem - start_mem

    print(f"--- Resultados ---")
    print(f"Tiempo Total: {duration:.4f} segundos")
    print(f"Fragmentos Generados: {len(fragmentos)}")
    print(f"Memoria Utilizada (Peak Delta): {mem_diff:.2f} MB")
    
    # Validar integridad de los fragmentos
    validos = 0
    for f in fragmentos:
        if len(f.get("id_del_fragmento", "")) == 64:
            validos += 1
    
    print(f"Integridad de Fragments: {validos}/{len(fragmentos)} OK")
    
    # Guardar resultados
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file": path.name,
        "metrics": {
            "duration_sec": duration,
            "fragment_count": len(fragmentos),
            "memory_mb": mem_diff
        }
    }
    
    report_path = Path("00_sistema_tesis/05_registros_de_ingestion/benchmarks/")
    report_path.mkdir(parents=True, exist_ok=True)
    report_file = report_path / f"BENCH_{path.stem}_{int(time.time())}.json"
    
    with open(report_file, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Reporte JSON guardado en: {report_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python benchmark_ingesta.py <ruta_archivo>")
    else:
        run_benchmark(sys.argv[1])
