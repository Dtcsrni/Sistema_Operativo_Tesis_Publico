import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import time
import os

import numpy as np
try:
    import cv2
    from rknnlite.api import RKNNLite
except ImportError as e:
    print(f"Error: No se pudieron importar las libreras necesarias. {e}")
    sys.exit(1)

# Configuracin del Benchmark
MODEL_PATH = 'runtime/models/edge/resnet18_for_rk3588.rknn'
IMAGE_PATH = 'runtime/models/edge/space_shuttle_224.jpg'
ITERATIONS = 100
WARMUP = 10

def run_benchmark():
    print("=== SIOT RKNN NPU PERFORMANCE BENCHMARK ===")
    
    if not os.path.exists(MODEL_PATH):
        print(f"Error: No se encuentra el modelo en {MODEL_PATH}")
        return

    if not os.path.exists(IMAGE_PATH):
        print(f"Error: No se encuentra la imagen en {IMAGE_PATH}")
        return

    # Inicializar RKNN
    rknn_lite = RKNNLite()
    
    print(f"--> Cargando modelo: {MODEL_PATH}")
    ret = rknn_lite.load_rknn(MODEL_PATH)
    if ret != 0:
        print("Error al cargar el modelo.")
        return

    # Pre-procesamiento de imagen
    img = cv2.imread(IMAGE_PATH)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = np.expand_dims(img, 0)

    print("--> Inicializando runtime NPU...")
    # Usar core_mask para RK3588 (Core 0 por defecto)
    ret = rknn_lite.init_runtime(core_mask=RKNNLite.NPU_CORE_0)
    if ret != 0:
        print("Error al inicializar el runtime. Est el driver /dev/rknpu disponible?")
        return

    print(f"--> Calentamiento ({WARMUP} iteraciones)...")
    for _ in range(WARMUP):
        rknn_lite.inference(inputs=[img])

    print(f"--> Ejecutando benchmark ({ITERATIONS} iteraciones)...")
    latencies = []
    for i in range(ITERATIONS):
        start_time = time.perf_counter()
        rknn_lite.inference(inputs=[img])
        end_time = time.perf_counter()
        latencies.append((end_time - start_time) * 1000) # ms

    # Estadsticas
    avg_latency = np.mean(latencies)
    min_latency = np.min(latencies)
    max_latency = np.max(latencies)
    std_latency = np.std(latencies)
    fps = 1000 / avg_latency

    print("\n--- RESULTADOS ---")
    print(f"Modelo: ResNet-18 (RK3588 Optimized)")
    print(f"Latencia Promedio: {avg_latency:.2f} ms")
    print(f"Latencia Mnima:   {min_latency:.2f} ms")
    print(f"Latencia Mxima:   {max_latency:.2f} ms")
    print(f"Desviacin Est.:   {std_latency:.2f} ms")
    print(f"Inferencia/seg:    {fps:.2f} FPS")
    print("------------------\n")

    rknn_lite.release()

if __name__ == "__main__":
    run_benchmark()
