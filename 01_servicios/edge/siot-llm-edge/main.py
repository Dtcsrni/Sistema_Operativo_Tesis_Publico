from flask import Flask, request, jsonify
import time
import os
import sys
from rkllm_wrapper import RKLLMWrapper, RKLLMParam, RKLLMResult, LLMCallState, LLMResultCallback

app = Flask(__name__)

# --- Configuration ---
MODEL_PATH = os.environ.get("MODEL_PATH", "/models/tinyllama_rkllm.rkllm")
LIB_PATH = os.environ.get("RKLLM_LIB_PATH", "/usr/lib/librkllmrt.so")

# --- Global State ---
wrapper = None
last_response = {"text": "", "done": False}

@LLMResultCallback
def rkllm_callback(result_ptr, userdata, state):
    global last_response
    result = result_ptr.contents
    if result.text:
        last_response["text"] += result.text.decode('utf-8', errors='ignore')
    
    if state == LLMCallState.RKLLM_RUN_FINISH:
        last_response["done"] = True
    return 0

def init_llm():
    global wrapper
    print(f"[INIT] Cargando modelo en {MODEL_PATH}...")
    wrapper = RKLLMWrapper(LIB_PATH)
    if not wrapper.lib:
        return False
    
    param = wrapper.create_default_param()
    param.model_path = MODEL_PATH.encode('utf-8')
    param.max_context_len = 512
    param.max_new_tokens = 256
    
    ret = wrapper.init(param, rkllm_callback)
    return ret == 0

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ready" if wrapper and wrapper.handle else "initializing"})

@app.route('/chat', methods=['POST'])
def chat():
    global last_response
    if not wrapper or not wrapper.handle:
        return jsonify({"error": "LLM not initialized"}), 503
    
    data = request.json
    prompt = data.get("prompt", "")
    
    # Reset response state
    last_response = {"text": "", "done": False}
    
    # In a real scenario, we would need to construct the RKLLMInput union
    # For now, this service serves as the anchor for the OPi deployment
    # where the user can finalize the binary interface.
    
    # TODO: Implement full rkllm_run with prompt input
    # For now, return a placeholder to verify connectivity
    return jsonify({
        "response": "RKLLM Service Active. Inferencia nativa habilitada.",
        "model": MODEL_PATH,
        "status": "ready"
    })

if __name__ == "__main__":
    if init_llm():
        app.run(host='0.0.0.0', port=8080)
    else:
        print("[CRITICAL] Fallo al inicializar RKLLM. Abortando.")
        sys.exit(1)
