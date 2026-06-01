import sys
import argparse
from rkllm_wrapper_v2 import RKLLMWrapper, RKLLMParam, LLMCallState, LLMResultCallback, POINTER, RKLLMResult

# <!-- SISTEMA_TESIS:PROTEGIDO -->

def result_callback(result, userdata, state):
    if state == LLMCallState.RKLLM_RUN_NORMAL:
        # Imprimir el texto parcial (streaming simulado por la librera)
        print(result.contents.text.decode('utf-8'), end='', flush=True)
    elif state == LLMCallState.RKLLM_RUN_FINISH:
        print("\n[FINISH]")
    elif state == LLMCallState.RKLLM_RUN_ERROR:
        print("\n[ERROR] Error en la ejecución del modelo.")

# Definir el wrapper del callback
c_callback = LLMResultCallback(result_callback)

def main():
    parser = argparse.ArgumentParser(description="Inferencia RKLLM simple")
    parser.add_argument("--model", type=str, required=True, help="Ruta al modelo .rkllm")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt de entrada")
    args = parser.parse_args()

    wrapper = RKLLMWrapper()
    if not wrapper.lib:
        print("[ERROR] Librería RKLLM no encontrada.")
        sys.exit(1)

    param = wrapper.create_default_param()
    param.model_path = args.model.encode('utf-8')
    param.max_new_tokens = 512
    param.max_context_len = 2048
    param.use_gpu = True

    ret = wrapper.init(param, c_callback)
    if ret != 0:
        print(f"[ERROR] Error al inicializar RKLLM: {ret}")
        sys.exit(1)

    print(f"--- Ejecutando Prompt en NPU ---")
    ret = wrapper.run(args.prompt)
    if ret != 0:
        print(f"[ERROR] Error al ejecutar el modelo: {ret}")

    wrapper.destroy()

if __name__ == "__main__":
    main()
