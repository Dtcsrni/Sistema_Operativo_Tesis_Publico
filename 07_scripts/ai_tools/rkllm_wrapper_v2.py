import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import ctypes
from ctypes import c_char_p, c_int32, c_float, c_bool, Structure, POINTER, c_void_p, CFUNCTYPE

# --- Enumerations ---

class LLMCallState:
    RKLLM_RUN_NORMAL = 0
    RKLLM_RUN_FINISH = 1
    RKLLM_RUN_ERROR = 2

# --- Structures ---

class Token(Structure):
    _fields_ = [
        ("logprob", c_float),
        ("id", c_int32)
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
        ("logprobs", c_bool),
        ("top_logprobs", c_int32),
        ("use_gpu", c_bool)
    ]

class RKLLMResult(Structure):
    _fields_ = [
        ("text", c_char_p),
        ("tokens", POINTER(Token)),
        ("num", c_int32)
    ]

# --- Callbacks ---

# Callback signature: void(*LLMResultCallback)(RKLLMResult* result, void* userdata, LLMCallState state)
LLMResultCallback = CFUNCTYPE(None, POINTER(RKLLMResult), c_void_p, c_int32)

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
        # int rkllm_init(LLMHandle* handle, RKLLMParam param, LLMResultCallback callback);
        # Note: In the header, RKLLMParam is passed by value.
        self.lib.rkllm_init.argtypes = [POINTER(c_void_p), RKLLMParam, LLMResultCallback]
        self.lib.rkllm_init.restype = c_int32
        
        # int rkllm_destroy(LLMHandle handle);
        self.lib.rkllm_destroy.argtypes = [c_void_p]
        self.lib.rkllm_destroy.restype = c_int32
        
        # RKLLMParam rkllm_createDefaultParam();
        self.lib.rkllm_createDefaultParam.restype = RKLLMParam

        # int rkllm_run(LLMHandle handle, const char* prompt, void* userdata);
        self.lib.rkllm_run.argtypes = [c_void_p, c_char_p, c_void_p]
        self.lib.rkllm_run.restype = c_int32

    def create_default_param(self):
        return self.lib.rkllm_createDefaultParam()

    def init(self, param, callback):
        return self.lib.rkllm_init(ctypes.byref(self.handle), param, callback)

    def run(self, prompt, userdata=None):
        if not self.handle:
            return -1
        return self.lib.rkllm_run(self.handle, prompt.encode('utf-8'), userdata)

    def destroy(self):
        if self.handle:
            ret = self.lib.rkllm_destroy(self.handle)
            self.handle = c_void_p()
            return ret
        return 0

if __name__ == "__main__":
    print("[INFO] RKLLM Wrapper V2 Cargado (Prueba de carga de librera)")
    wrapper = RKLLMWrapper("/usr/lib/librkllmrt.so")
    if wrapper.lib:
        print("[SUCCESS] Librera RKLLM cargada correctamente.")
        param = wrapper.create_default_param()
        print(f"[DEBUG] Default model_path: {param.model_path}")
    else:
        print("[SKIP] Librera no disponible.")
