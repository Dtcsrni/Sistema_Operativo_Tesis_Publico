import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import time
import os

from rkllm_wrapper import RKLLMWrapper, RKLLMParam, RKLLMResult, LLMCallState, LLMResultCallback

# --- Global Stats ---
stats = {
    "tokens": 0,
    "start_time": 0,
    "first_token_time": 0,
    "text": ""
}

@LLMResultCallback
def benchmark_callback(result_ptr, userdata, state):
    result = result_ptr.contents
    if stats["start_time"] == 0:
        stats["start_time"] = time.time()
    
    if result.text:
        if stats["first_token_time"] == 0:
            stats["first_token_time"] = time.time()
        
        # Decode and print
        token_text = result.text.decode('utf-8', errors='ignore')
        stats["text"] += token_text
        stats["tokens"] += 1
        print(token_text, end="", flush=True)

    if state == LLMCallState.RKLLM_RUN_FINISH:
        print("\n[INFO] Inferencia finalizada.")
    
    return 0

def run_aggressive_benchmark(model_path, duration_min=5):
    print(f"[STRESS] Iniciando benchmark agresivo por {duration_min} minutos...")
    wrapper = RKLLMWrapper("runtime/drivers/rknn/librkllmrt.so")
    
    if not wrapper.lib:
        print("[FAIL] Librera RKLLM no encontrada.")
        return

    # High performance config
    param = wrapper.create_default_param()
    param.model_path = model_path.encode('utf-8')
    param.max_context_len = 1024 # Aumentamos contexto
    param.max_new_tokens = 512
    param.temperature = 1.0 # Ms carga computacional
    
    ret = wrapper.init(param, benchmark_callback)
    if ret != 0:
        return

    start_time = time.time()
    total_tokens = 0
    runs = 0
    
    while (time.time() - start_time) < (duration_min * 60):
        runs += 1
        print(f"\n[RUN {runs}] Inferencia en curso...")
        # Simular carga continua
        # TODO: Implementar rkllm_run concurrente si la lib lo soporta
        time.sleep(2) # Pausa entre ragas para evitar cuelgue total
    
    end_time = time.time()
    print(f"\n[SUMMARY] Benchmark Agresivo Finalizado.")
    print(f"Tiempo Total: {end_time - start_time:.1f}s")
    print(f"Corridas completadas: {runs}")
    
    wrapper.destroy()

if __name__ == "__main__":
    model = "runtime/models/edge/tinyllama_rkllm.rkllm"
    if os.path.exists(model):
        if "--stress" in sys.argv:
            run_aggressive_benchmark(model)
        else:
            run_benchmark(model)
    else:
        print(f"[SKIP] Modelo {model} no encontrado.")
