import ctypes
from ctypes import c_char_p, c_int32, c_float, c_bool, Structure, POINTER, c_void_p, c_int8, c_uint32, c_uint8, c_size_t, CFUNCTYPE

# --- Enumerations ---

class LLMCallState:
    RKLLM_RUN_NORMAL = 0
    RKLLM_RUN_WAITING = 1
    RKLLM_RUN_FINISH = 2
    RKLLM_RUN_ERROR = 3

class RKLLMInputType:
    RKLLM_INPUT_PROMPT = 0
    RKLLM_INPUT_TOKEN = 1
    RKLLM_INPUT_EMBED = 2
    RKLLM_INPUT_MULTIMODAL = 3

# --- Structures ---

class RKLLMExtendParam(Structure):
    _fields_ = [
        ("base_domain_id", c_int32),
        ("embed_flash", c_int8),
        ("enabled_cpus_num", c_int8),
        ("enabled_cpus_mask", c_uint32),
        ("n_batch", c_uint8),
        ("use_cross_attn", c_int8),
        ("reserved", c_uint8 * 104)
    ]

class RKLLMParam(Structure):
    _fields_ = [
        ("model_path", c_char_p),
        ("max_context_len", c_int32),
        ("max_new_tokens", c_int32),
        ("top_k", c_int32),
        ("n_keep", c_int32),
        ("top_p", c_float),
        ("temperature", c_float),
        ("repeat_penalty", c_float),
        ("frequency_penalty", c_float),
        ("presence_penalty", c_float),
        ("mirostat", c_int32),
        ("mirostat_tau", c_float),
        ("mirostat_eta", c_float),
        ("skip_special_token", c_bool),
        ("is_async", c_bool),
        ("img_start", c_char_p),
        ("img_end", c_char_p),
        ("img_content", c_char_p),
        ("extend_param", RKLLMExtendParam)
    ]

class RKLLMPerfStat(Structure):
    _fields_ = [
        ("prefill_time_ms", c_float),
        ("prefill_tokens", c_int32),
        ("generate_time_ms", c_float),
        ("generate_tokens", c_int32),
        ("memory_usage_mb", c_float)
    ]

class RKLLMResultLastHiddenLayer(Structure):
    _fields_ = [
        ("hidden_states", POINTER(c_float)),
        ("embd_size", c_int32),
        ("num_tokens", c_int32)
    ]

class RKLLMResultLogits(Structure):
    _fields_ = [
        ("logits", POINTER(c_float)),
        ("vocab_size", c_int32),
        ("num_tokens", c_int32)
    ]

class RKLLMResult(Structure):
    _fields_ = [
        ("text", c_char_p),
        ("token_id", c_int32),
        ("last_hidden_layer", RKLLMResultLastHiddenLayer),
        ("logits", RKLLMResultLogits),
        ("perf", RKLLMPerfStat)
    ]

# --- Callbacks ---

LLMResultCallback = CFUNCTYPE(c_int32, POINTER(RKLLMResult), c_void_p, c_int32)

# --- Library Wrapper ---

class RKLLMWrapper:
    def __init__(self, lib_path="/usr/lib/librkllmrt.so"):
        try:
            self.lib = ctypes.CDLL(lib_path)
            self._setup_functions()
            self.handle = c_void_p()
        except Exception as e:
            print(f"[ERROR] No se pudo cargar {lib_path}: {e}")
            self.lib = None

    def _setup_functions(self):
        self.lib.rkllm_init.argtypes = [POINTER(c_void_p), POINTER(RKLLMParam), LLMResultCallback]
        self.lib.rkllm_init.restype = c_int32
        
        self.lib.rkllm_destroy.argtypes = [c_void_p]
        self.lib.rkllm_destroy.restype = c_int32
        
        self.lib.rkllm_createDefaultParam.restype = RKLLMParam

    def create_default_param(self):
        return self.lib.rkllm_createDefaultParam()

    def init(self, param, callback):
        return self.lib.rkllm_init(ctypes.byref(self.handle), ctypes.byref(param), callback)

    def destroy(self):
        if self.handle:
            return self.lib.rkllm_destroy(self.handle)
        return 0

if __name__ == "__main__":
    print("[INFO] RKLLM Wrapper Cargado (Prueba de carga de librera)")
    # En desarrollo Windows, esto fallar, pero est diseado para ejecutarse en la OPi 5
    wrapper = RKLLMWrapper("runtime/drivers/rknn/librkllmrt.so")
    if wrapper.lib:
        print("[SUCCESS] Librera RKLLM cargada correctamente.")
    else:
        print("[SKIP] Librera no disponible en este host (Esperado en Windows).")
