import time
import requests
import json
import os
import math
import platform
import hashlib
import sys
from datetime import datetime
from pathlib import Path

from benchmark_science import (
    append_hashed_record,
    build_run_header,
    build_sample_record,
    promptset_hash,
    run_log_path,
    update_index,
    write_summary,
)
import benchmark_identity

# --- Configuration ---
INFERENCE_URL = "http://localhost:8080/chat"
ITERATIONS = 50
WARMUP_ITERATIONS = 2
COOL_DOWN_SECONDS = 30
DEFAULT_OUTPUT_LOG = "runtime/edge_iot/benchmarks/standardized_run_hardened.jsonl"
OUTPUT_LOG = DEFAULT_OUTPUT_LOG
DEFAULT_NODE_TYPE = "edge"

def get_environment_metadata():
    """Captura metadatos del entorno para garantizar reproducibilidad según estándares."""
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": sys.version,
        "processor": platform.processor(),
        "timestamp_start": datetime.now().isoformat()
    }

def get_system_telemetry():
    """Captura telemetría de hardware de forma portable."""
    telemetry = {"timestamp": datetime.now().isoformat()}
    try:
        if platform.system() == "Windows":
            # Fallback a WMIC si psutil no está
            try:
                load = subprocess.check_output("wmic cpu get loadpercentage", shell=True).decode().splitlines()[2].strip()
                telemetry["cpu_usage_pct"] = float(load)
            except:
                telemetry["cpu_usage_pct"] = None
        else:
            # Linux: Leer loadavg
            with open("/proc/loadavg", "r") as f:
                telemetry["load_avg"] = f.read().split()[0]
            # Temperatura en OPi
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    telemetry["temp_c"] = int(f.read().strip()) / 1000.0
            except:
                pass
    except:
        pass
    return telemetry

def compute_record_hash(record):
    """Calcula un hash SHA-256 del registro para garantizar integridad post-experimento."""
    data = json.dumps(record, sort_keys=True)
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

class StandardizedRunner:
    def __init__(self, task_name, prompt, category="general", node_type=DEFAULT_NODE_TYPE, output_log=None, model="mistral-nemo:12b", runtime="ollama_local", profile_id="edge_npu", step_id="VAL-STEP-PENDING", mode="real"):
        self.task_name = task_name
        self.prompt = prompt
        self.category = category
        self.node_type = node_type
        self.output_log = output_log or OUTPUT_LOG
        self.model = model
        self.runtime = runtime
        self.profile_id = profile_id
        self.step_id = step_id
        self.mode = mode
        self.samples = []
        self.identity = benchmark_identity.get_full_identity(runtime, model)
        if self.identity["model"]["status"] != "verified" and mode == "real":
             print(f"!!! CRITICAL ERROR: Model identity mismatch !!!")
             print(json.dumps(self.identity["model"], indent=2))
             sys.exit(1)

        self.metadata = self.identity
        self.promptset = [{"category": category, "name": task_name, "prompt": prompt}]
        self.header = build_run_header(
            profile_id=profile_id,
            node="pc_control" if node_type.startswith("pc") else "edge_iot",
            runtime=runtime,
            model=model,
            step_id=step_id,
            command=f"StandardizedRunner:{task_name}",
            promptset=self.promptset,
            mode=mode,
            repo_root=Path(__file__).resolve().parents[1]
        )
        self.run_id = self.header["run_id"]
        self.scientific_log = run_log_path(node=self.header["node"], run_id=self.run_id)

    def run_warmup(self):
        print(f"[{self.node_type}:{self.category}] [1/4] Fase de Calentamiento ({WARMUP_ITERATIONS} iteraciones)...")
        for index in range(WARMUP_ITERATIONS):
            try:
                # Usamos un timeout mínimo para estabilizar caché
                requests.post(INFERENCE_URL, json={"prompt": "warmup"}, timeout=0.1)
                status = "ok"
            except Exception:
                status = "unavailable"
            append_hashed_record(
                self.scientific_log,
                build_sample_record(
                    run_id=self.run_id,
                    step_id=self.step_id,
                    sample_index=index + 1,
                    phase="warmup",
                    category=self.category,
                    prompt_hash=promptset_hash([{"prompt": "warmup"}]),
                    latency_ms=None,
                    ttft_ms=None,
                    tokens_per_second=None,
                    status=status,
                    mode=self.mode,
                ),
            )
        time.sleep(2)

    def run_measurement(self):
        print(f"[{self.node_type}:{self.category}] [2/4] Fase de Medición ({ITERATIONS} muestras) para '{self.task_name}'...")
        for i in range(ITERATIONS):
            telemetry_before = get_system_telemetry()
            
            # USO DE PERF_COUNTER PARA PRECISIÓN DE NANOSEGUNDOS
            start = time.perf_counter()
            
            try:
                # Intento de petición real
                resp = requests.post(INFERENCE_URL, json={"prompt": self.prompt}, timeout=0.5)
                end = time.perf_counter()
                
                latency = (end - start) * 1000 # Convertir a ms
                data = resp.json() if resp.status_code == 200 else {}
                tps = data.get("tps", 0.0)
                status = "REAL"
            except Exception:
                # No synthetic fallback: benchmark must reflect physical execution only.
                end = time.perf_counter()
                latency = (end - start) * 1000
                tps = None
                status = "failed"
            
            sample = {
                "iteration": i + 1,
                "latency_ms": round(latency, 4), # 4 decimales de precisión
                "tps": round(tps, 2) if isinstance(tps, (int, float)) else None,
                "telemetry": telemetry_before,
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "scientific_validity": "valid_candidate" if status == "REAL" else "invalid_for_scientific_claim",
            }
            self.samples.append(sample)
            append_hashed_record(
                self.scientific_log,
                build_sample_record(
                    run_id=self.run_id,
                    step_id=self.step_id,
                    sample_index=i + 1,
                    phase="measurement",
                    category=self.category,
                    prompt_hash=promptset_hash(self.promptset),
                    latency_ms=round(latency, 4),
                    ttft_ms=None,
                    tokens_per_second=round(tps, 2) if isinstance(tps, (int, float)) else None,
                    status=status,
                    mode=self.mode,
                ),
            )
            
            # Intervalo entre muestras para evitar saturación de bus (PEV-01)
            time.sleep(0.1) 

    def analyze(self):
        print(f"[{self.node_type}:{self.category}] [3/4] Análisis Estadístico Riguroso...")
        valid_samples = [
            s for s in self.samples
            if s.get("status") == "REAL"
            and isinstance(s.get("latency_ms"), (int, float))
            and isinstance(s.get("tps"), (int, float))
        ]

        if not valid_samples:
            return None

        lats = [s["latency_ms"] for s in valid_samples]
        tps_list = [s["tps"] for s in valid_samples]

        n = len(lats)
        mean_lat = sum(lats) / n
        std_lat = math.sqrt(sum((x - mean_lat) ** 2 for x in lats) / n)
        mean_tps = sum(tps_list) / n

        # Margen de Error (95% confianza, Z=1.96)
        moe_lat = 1.96 * (std_lat / math.sqrt(n))

        # Ordenar para percentiles
        lats_sorted = sorted(lats)
        p95 = lats_sorted[max(0, int(0.95 * n) - 1)]
        p99 = lats_sorted[max(0, int(0.99 * n) - 1)]

        result = {
            "run_id": self.run_id,
            "profile_id": self.profile_id,
            "category": self.category,
            "task": self.task_name,
            "mean_latency_ms": round(mean_lat, 2),
            "std_dev_lat": round(std_lat, 2),
            "moe_lat": round(moe_lat, 2),
            "p95_latency": round(p95, 2),
            "p99_latency": round(p99, 2),
            "mean_tps": round(mean_tps, 2),
            "sample_size": n,
            "env": self.metadata,
            "protocol": self.header["protocol"],
            "model": self.model,
            "runtime": self.runtime,
            "scientific_validity": "valid_scientific_evidence",
            "primary_jsonl": str(self.scientific_log),
            "integrity_hash": ""
        }

        # Sello de Integridad
        result["integrity_hash"] = compute_record_hash(result)
        return result

    def execute(self):
        append_hashed_record(self.scientific_log, self.header)
        self.run_warmup()
        self.run_measurement()
        result = self.analyze()

        if not result:
            # Si no hubo muestras reales válidas, no conservar artefacto parcial.
            print(f"[{self.node_type}:{self.category}] [4/4] Sin muestras REAL válidas. Artefacto descartado.", flush=True)
            if self.scientific_log.exists():
                self.scientific_log.unlink()
            return None

        print(f"[{self.node_type}:{self.category}] [4/4] Resultado: Mean={result['mean_latency_ms']}ms +/- {result['moe_lat']}ms (Error 95%)", flush=True)

        # ESCRITURA ATÓMICA Y SEGURA
        if not os.path.exists(os.path.dirname(self.output_log)):
            os.makedirs(os.path.dirname(self.output_log), exist_ok=True)

        with open(self.output_log, "a", encoding='utf-8') as f:
            f.write(json.dumps(result) + "\n")
            f.flush()
            os.fsync(f.fileno()) # Forzar escritura a disco
        summary = write_summary(
            path=self.scientific_log,
            header=self.header,
            samples=[
                {
                    "latency_ms": sample["latency_ms"],
                    "tokens_per_second": sample["tps"],
                }
                for sample in self.samples
                if sample.get("status") == "REAL"
            ],
            status="ok" if all(sample.get("status") == "REAL" for sample in self.samples) else "partial_failure",
            extra={"legacy_output_log": self.output_log, "legacy_integrity_hash": result["integrity_hash"]},
        )
        update_index(node=self.header["node"], summary=summary, log_path=self.scientific_log)

        return result

if __name__ == "__main__":
    runner = StandardizedRunner("Inferencia de Decisión Crítica", "¿Protocolo de inundación?", "decision")
    runner.execute()
