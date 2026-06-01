import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import csv
import math
import json
import os

RAW_DATA_FILE = "runtime/edge_iot/benchmarks/raw_performance_data.csv"
REPORT_JSON = "runtime/edge_iot/benchmarks/statistical_analysis.json"

def calculate_percentile(data, percentile):
    size = len(data)
    return sorted(data)[int(math.ceil((size * percentile) / 100)) - 1]

def perform_statistical_analysis():
    print("[ANALYSIS] Realizando análisis estadístico (Standard Libs)...")
    
    if not os.path.exists(RAW_DATA_FILE):
        return

    data_map = {}
    with open(RAW_DATA_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            test = row['test_name']
            if test not in data_map:
                data_map[test] = {"latencies": [], "tps": []}
            data_map[test]["latencies"].append(float(row['latency_ms']))
            data_map[test]["tps"].append(float(row['tps']))

    analysis = {}
    for test, metrics in data_map.items():
        lats = metrics["latencies"]
        tps = metrics["tps"]
        
        mean_lat = sum(lats) / len(lats)
        mean_tps = sum(tps) / len(tps)
        
        # Variance
        var_lat = sum((x - mean_lat)**2 for x in lats) / len(lats)
        std_lat = math.sqrt(var_lat)
        
        analysis[test] = {
            "mean_latency_ms": round(mean_lat, 2),
            "std_dev_latency": round(std_lat, 2),
            "p95_latency": round(calculate_percentile(lats, 95), 2),
            "p99_latency": round(calculate_percentile(lats, 99), 2),
            "mean_tps": round(mean_tps, 2),
            "sample_size": len(lats)
        }
        
    with open(REPORT_JSON, "w") as f:
        json.dump(analysis, f, indent=4)
    
    print(f"[SUCCESS] Análisis guardado en {REPORT_JSON}")

if __name__ == "__main__":
    perform_statistical_analysis()
