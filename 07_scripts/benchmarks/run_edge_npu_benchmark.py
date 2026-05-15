from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import argparse
import hashlib
import json
import os
import time

# Agregar rutas necesarias
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from rkllm_wrapper import RKLLMWrapper, RKLLMParam, LLMCallState, LLMResultCallback
from benchmark_science import (
    append_hashed_record,
    build_run_header,
    utc_now,
    write_summary,
    run_log_path,
    update_index
)
from rknpu_detect import rknpu_summary

# --- Configuration ---
DEFAULT_MODEL = str(ROOT / "runtime/models/edge/qwen2.5_3b_rkllm.rkllm")
DEFAULT_LIB = str(ROOT / "runtime/drivers/rknn/librkllmrt.so")

CATEGORIES_CONFIG = {
    "iot_urban_pachuca": {
        "name": "Conectividad Urbana Pachuca",
        "prompt": "Actúa como un coordinador de red IoT en Pachuca de Soto. Un activo móvil (Toltecayotl Track) se desplaza del Centro Histórico hacia la periferia (Zona Plateada). El RSSI de LoRa cae a -125dBm y el SNR es de -15dB. ¿Debería el nodo conmutar de MQTT directo a un relay P2P? Justifica brevemente considerando la topografía de Pachuca."
    },
    "hybrid_lora_logic": {
        "name": "Lógica Híbrida P2P-MQTT",
        "prompt": "Diseña un algoritmo de decisión en pseudo-código para un nodo Heltec WSL V3 que opera en una arquitectura híbrida LoRa P2P-MQTT. El criterio debe priorizar el ahorro de energía y la integridad de los datos (PDR) al monitorear una flota ligera."
    },
    "toltecayotl_fleet_agent": {
        "name": "Agente de Gestión de Flotas Toltecayotl",
        "prompt": "Eres un agente de IA embebido en una Orange Pi 5 Plus. Recibes telemetría de 50 nodos Toltecayotl Track en tiempo real. Un nodo reporta una caída súbita de voltaje (3.2V) y coordenadas GPS estáticas en una zona de alta delincuencia. Genera un reporte de incidente y una acción correctiva inmediata."
    },
    "iot_sovereignty_pachuca": {
        "name": "Soberanía de Datos Urbanos",
        "prompt": "Analiza las implicaciones éticas y de soberanía de procesar datos de movilidad urbana de Pachuca en el Edge (Orange Pi) vs enviarlos a una nube comercial externa. Cita brevemente la importancia de la privacidad en sistemas operativos de tesis posgrado."
    },
    "embedded_cpp_toltecayotl": {
        "name": "Lógica Embebida C++ (WSL V3)",
        "prompt": "Escribe una función C++ optimizada para un ESP32 (Heltec WSL V3) que implemente un buffer circular para almacenar temporalmente 10 tramas de telemetría GPS/RSSI cuando la conexión con el Gateway se pierde en un entorno urbano denso."
    }
}

CATEGORIES = [{"id": k, **v} for k, v in CATEGORIES_CONFIG.items()]

# --- Global State for Callback ---
class BenchmarkContext:
    def __init__(self):
        self.response_text = ""
        self.tokens_count = 0
        self.start_time = 0.0
        self.first_token_time = 0.0
        self.done = False
        self.error = False

current_ctx = BenchmarkContext()

@LLMResultCallback
def benchmark_callback(result_ptr, userdata, state):
    global current_ctx
    result = result_ptr.contents
    
    if current_ctx.start_time == 0:
        current_ctx.start_time = time.perf_counter()
        
    if result.text:
        if current_ctx.first_token_time == 0:
            current_ctx.first_token_time = time.perf_counter()
        
        chunk = result.text.decode('utf-8', errors='ignore')
        current_ctx.response_text += chunk
        # Nota: RKLLM no siempre devuelve tokens 1:1 con llamadas de callback,
        # pero para el benchmark usaremos el conteo de callbacks con texto como proxy o 
        # aproximación si la lib no provee el conteo real en esta versión.
        current_ctx.tokens_count += 1 

    if state == LLMCallState.RKLLM_RUN_FINISH:
        current_ctx.done = True
    elif state == LLMCallState.RKLLM_RUN_ERROR:
        current_ctx.error = True
        current_ctx.done = True
    return 0

def main():
    parser = argparse.ArgumentParser(description="Benchmark NPU (RKLLM) para Orange Pi 5 Plus.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--lib", default=DEFAULT_LIB)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--step-id", default="VAL-STEP-PENDING")
    parser.add_argument("--profile-id", default="edge_npu_llama3_2_3b_extensive")
    args = parser.parse_args()

    header = build_run_header(
        profile_id=args.profile_id,
        node="edge_iot",
        runtime="rkllm_native",
        model=Path(args.model).name,
        step_id=args.step_id,
        command="python3 07_scripts/run_edge_npu_benchmark.py",
        promptset=CATEGORIES,
        mode="real",
        repo_root=ROOT
    )
    log_path = run_log_path(node=header["node"], run_id=header["run_id"])
    append_hashed_record(log_path, header)

    def fail_before_samples(reason: str, extra: dict | None = None) -> int:
        summary = write_summary(
            path=log_path,
            header=header,
            samples=[],
            status="failed",
            extra={"reason": reason, **(extra or {})},
        )
        update_index(node=header["node"], summary=summary, log_path=log_path)
        print(f"[DONE] Benchmark NPU fallido con evidencia en {log_path}")
        return 1

    npu = rknpu_summary()
    if not npu["ready"]:
        print("[ERROR] No se detectó NPU RK3588 por /dev/rknpu, /dev/rknn ni DRM render RKNPU.")
        return fail_before_samples("npu_device_not_detected")
    print(f"[INIT] NPU detectada: {', '.join(npu['devices'])}")

    print(f"[INIT] Cargando Wrapper RKLLM con {args.lib}...")
    wrapper = RKLLMWrapper(args.lib)
    if not wrapper.lib:
        print("[ERROR] No se pudo cargar la librería RKLLM.")
        return fail_before_samples("rkllm_library_load_failed", {"lib": args.lib})

    print(f"[INIT] Inicializando modelo {args.model} en NPU...")
    param = wrapper.create_default_param()
    param.model_path = args.model.encode('utf-8')
    param.max_context_len = 8192
    param.max_new_tokens = 512
    param.use_gpu = True # Forzar NPU

    res = wrapper.init(param, benchmark_callback)
    if res != 0:
        print(f"[ERROR] Fallo en rkllm_init: {res}")
        return fail_before_samples("rkllm_init_failed", {"rkllm_init_returncode": res, "npu_devices": npu["devices"]})

    print(f"[START] Iniciando {len(CATEGORIES)} categorías x {args.iterations} iteraciones.")
    
    samples = []
    status = "ok"

    try:
        for category in CATEGORIES:
            for i in range(args.iterations):
                print(f"[RUN] {category['id']} {i+1}/{args.iterations}...", end="", flush=True)
                
                # Reset context
                global current_ctx
                current_ctx = BenchmarkContext()
                
                start_wall = time.perf_counter()
                res = wrapper.run(category['prompt'])
                
                if res != 0:
                    print(f" ERROR({res})")
                    status = "partial_failure"
                    continue
                
                # Wait for finish (callback driven)
                while not current_ctx.done:
                    time.sleep(0.01)
                    if time.perf_counter() - start_wall > 120: # Timeout 2 mins
                        current_ctx.error = True
                        break
                
                end_wall = time.perf_counter()
                latency_ms = (end_wall - start_wall) * 1000.0
                ttft_ms = (current_ctx.first_token_time - start_wall) * 1000.0 if current_ctx.first_token_time > 0 else None
                
                # TPS Estimado
                tps = (current_ctx.tokens_count / ((end_wall - current_ctx.first_token_time))) if current_ctx.tokens_count > 0 and current_ctx.first_token_time > 0 else 0

                sample_res = {
                    "status": "ok" if not current_ctx.error else "failed",
                    "latency_ms": round(latency_ms, 2),
                    "ttft_ms": round(ttft_ms, 2) if ttft_ms else None,
                    "tokens_per_second": round(tps, 2),
                    "response": current_ctx.response_text
                }
                
                # Build record (simulando build_sample_record de benchmark_science)
                sample_record = {
                    "record_type": "sample",
                    "sample_index": len(samples),
                    "category": category["id"],
                    "timestamp_utc": utc_now(),
                    "status": sample_res["status"],
                    "latency_ms": sample_res["latency_ms"],
                    "ttft_ms": sample_res["ttft_ms"],
                    "tokens_per_second": sample_res["tokens_per_second"],
                    "output_preview": sample_res["response"][:200],
                    "input_hash": hashlib.sha256(category["prompt"].encode()).hexdigest(),
                    "output_hash": hashlib.sha256(sample_res["response"].encode()).hexdigest()
                }
                
                append_hashed_record(log_path, sample_record)
                samples.append({"latency_ms": latency_ms, "tokens_per_second": tps})
                print(f" OK ({latency_ms:.0f}ms, {tps:.1f} tps)")

    finally:
        wrapper.destroy()

    summary = write_summary(path=log_path, header=header, samples=samples, status=status, extra={})
    update_index(node=header["node"], summary=summary, log_path=log_path)
    print(f"[DONE] Benchmark NPU finalizado. Reporte en {log_path}")

if __name__ == "__main__":
    raise SystemExit(main())
