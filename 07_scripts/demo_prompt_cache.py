import time
import sys
import os
from rkllm_wrapper import RKLLMWrapper, RKLLMParam, LLMResultCallback, LLMCallState

# --- Configuración ---
MODEL_PATH = "/home/ErickV/runtime/models/edge/qwen2.5_1.5b_rkllm_8k.rkllm"
LIB_PATH = "/home/ErickV/SIOT_Benchmark/runtime/drivers/rknn/librkllmrt.so"
CACHE_FILE = "/home/ErickV/runtime/models/edge/pachuca_system.rkllm_cache"

# Prompt de sistema largo para simular carga pesada
SYSTEM_PROMPT = """
Eres el Sistema Operativo de Tesis de Posgrado (SIOT) desarrollado por Erick Vega. 
Tu ubicación es Pachuca de Soto, Hidalgo. 
Tus reglas de soberanía son: 
1. Los datos nunca salen del Edge sin autorización explícita.
2. Priorizas la red LoRa P2P para emergencias.
3. El hardware principal es una Orange Pi 5 Plus con RK3588.
4. Conoces la topografía de la Bella Airosa, desde el Reloj Monumental hasta la Zona Plateada.
[Simulación de más contexto para llenar el buffer...]
"""

class CacheContext:
    def __init__(self):
        self.first_token_time = 0
        self.start_time = 0
        self.done = False

ctx = CacheContext()

@LLMResultCallback
def cache_callback(result_ptr, userdata, state):
    global ctx
    res = result_ptr.contents
    if res.text and ctx.first_token_time == 0:
        ctx.first_token_time = time.perf_counter()
    if state == LLMCallState.RKLLM_RUN_FINISH:
        ctx.done = True
    return 0

def run_test(wrapper, prompt, save_cache=None, use_cache=None):
    global ctx
    ctx = CacheContext()
    print(f"\n[TEST] Prompt: {prompt[:50]}...")
    ctx.start_time = time.perf_counter()
    
    wrapper.run(prompt, save_cache_path=save_cache, use_cache_path=use_cache)
    
    while not ctx.done:
        time.sleep(0.1)
    
    ttft = (ctx.first_token_time - ctx.start_time) * 1000
    print(f"[RESULT] Time to First Token (TTFT): {ttft:.2f} ms")
    return ttft

def main():
    wrapper = RKLLMWrapper(LIB_PATH)
    param = wrapper.create_default_param()
    param.model_path = MODEL_PATH.encode('utf-8')
    param.max_context_len = 8192
    
    print("[INIT] Inicializando modelo...")
    wrapper.init(param, cache_callback)
    
    # 1. Sin Cache (Guardando)
    print("\n--- PASO 1: Ejecución SIN Cache (Generando archivo...) ---")
    ttft_no_cache = run_test(wrapper, SYSTEM_PROMPT + "\nHola, ¿quién eres?", save_cache=CACHE_FILE)
    
    # 2. Con Cache (Cargando)
    print("\n--- PASO 2: Ejecución CON Cache (Carga instantánea) ---")
    ttft_cache = run_test(wrapper, SYSTEM_PROMPT + "\nHola de nuevo, ¿dónde estás?", use_cache=CACHE_FILE)
    
    improvement = ((ttft_no_cache - ttft_cache) / ttft_no_cache) * 100
    print(f"\n[CONCLUSIÓN] Mejora de latencia inicial: {improvement:.2f}%")
    
    wrapper.destroy()

if __name__ == "__main__":
    main()
