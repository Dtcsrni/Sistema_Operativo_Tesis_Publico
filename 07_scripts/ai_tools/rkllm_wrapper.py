import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



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

class RKLLMEmbedInput(Structure):
    _fields_ = [
        ("embed", POINTER(c_float)),
        ("n_tokens", c_size_t)
    ]

class RKLLMTokenInput(Structure):
    _fields_ = [
        ("input_ids", POINTER(c_int32)),
        ("n_tokens", c_size_t)
    ]

class RKLLMMultiModalInput(Structure):
    _fields_ = [
        ("prompt", c_char_p),
        ("image_embed", POINTER(c_float)),
        ("n_image_tokens", c_size_t),
        ("n_image", c_size_t),
        ("image_width", c_size_t),
        ("image_height", c_size_t)
    ]

class RKLLMInputUnion(ctypes.Union):
    _fields_ = [
        ("prompt_input", c_char_p),
        ("embed_input", RKLLMEmbedInput),
        ("token_input", RKLLMTokenInput),
        ("multimodal_input", RKLLMMultiModalInput)
    ]

class RKLLMInput(Structure):
    _fields_ = [
        ("role", c_char_p),
        ("enable_thinking", c_bool),
        ("input_type", c_int32), # RKLLMInputType
        ("union", RKLLMInputUnion)
    ]

class RKLLMLoraParam(Structure):
    _fields_ = [
        ("lora_adapter_name", c_char_p)
    ]

class RKLLMPromptCacheParam(Structure):
    _fields_ = [
        ("save_prompt_cache", c_int32),
        ("prompt_cache_path", c_char_p)
    ]

class RKLLMInferParam(Structure):
    _fields_ = [
        ("mode", c_int32), # RKLLMInferMode
        ("lora_params", POINTER(RKLLMLoraParam)),
        ("prompt_cache_params", POINTER(RKLLMPromptCacheParam)),
        ("keep_history", c_int32)
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

        # int rkllm_run(void* handle, RKLLMInput* input, RKLLMInferParam* infer_params, void* userdata);
        self.lib.rkllm_run.argtypes = [c_void_p, POINTER(RKLLMInput), POINTER(RKLLMInferParam), c_void_p]
        self.lib.rkllm_run.restype = c_int32
        
        # int rkllm_load_prompt_cache(LLMHandle handle, const char* prompt_cache_path);
        try:
            self.lib.rkllm_load_prompt_cache.argtypes = [c_void_p, c_char_p]
            self.lib.rkllm_load_prompt_cache.restype = c_int32
            
            self.lib.rkllm_release_prompt_cache.argtypes = [c_void_p]
            self.lib.rkllm_release_prompt_cache.restype = c_int32
        except:
            print("[WARN] Librería RKLLM no soporta load_prompt_cache directamente (versión antigua?)")

    def create_default_param(self):
        return self.lib.rkllm_createDefaultParam()

    def init(self, param, callback):
        return self.lib.rkllm_init(ctypes.byref(self.handle), ctypes.byref(param), callback)

    def load_prompt_cache(self, cache_path):
        if not self.handle: return -1
        return self.lib.rkllm_load_prompt_cache(self.handle, cache_path.encode('utf-8'))

    def run(self, prompt, userdata=None, save_cache_path=None, use_cache_path=None):
        if not self.handle:
            return -1
            
        # Prepare Input
        input_data = RKLLMInput()
        input_data.role = b"user"
        input_data.enable_thinking = False
        input_data.input_type = 0 # RKLLM_INPUT_PROMPT
        input_data.union.prompt_input = prompt.encode('utf-8')
        
        # Prepare Infer Params
        infer_params = RKLLMInferParam()
        infer_params.mode = 0 # RKLLM_INFER_GENERATE
        infer_params.lora_params = None
        infer_params.keep_history = 0
        
        # Cache handling
        cache_param = None
        if save_cache_path or use_cache_path:
            cache_param = RKLLMPromptCacheParam()
            cache_param.save_prompt_cache = 1 if save_cache_path else 0
            path = save_cache_path if save_cache_path else use_cache_path
            cache_param.prompt_cache_path = path.encode('utf-8')
            infer_params.prompt_cache_params = ctypes.pointer(cache_param)
        else:
            infer_params.prompt_cache_params = None
        
        return self.lib.rkllm_run(self.handle, ctypes.byref(input_data), ctypes.byref(infer_params), userdata)

    def destroy(self):
        if self.handle:
            return self.lib.rkllm_destroy(self.handle)
        return 0

if __name__ == "__main__":
    print("[INFO] RKLLM Wrapper Cargado (Prueba de carga de librería)")
    wrapper = RKLLMWrapper("runtime/drivers/rknn/librkllmrt.so")
    if wrapper.lib:
        print("[SUCCESS] Librería RKLLM cargada correctamente.")
    else:
        print("[SKIP] Librería no disponible en este host.")
