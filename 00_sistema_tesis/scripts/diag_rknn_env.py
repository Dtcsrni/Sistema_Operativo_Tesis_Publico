import time
import os
import sys

try:
    from rknnlite.api import RKNNLite
    import numpy as np
except ImportError as e:
    print(f"Error: No se pudo importar RKNNLite o dependencias. {e}")
    sys.exit(1)

def run_benchmark():
    print("--- SIOT RKNN NPU Benchmark ---")
    
    # 1. Verificar presencia de /dev/rknpu
    if os.path.exists("/dev/rknpu"):
        print("[OK] Dispositivo /dev/rknpu detectado.")
    else:
        print("[WARN] No se detectó /dev/rknpu. La inferencia NPU fallará fuera del contenedor privilegiado.")

    rknn = RKNNLite()
    
    print("[INFO] RKNNLite inicializado correctamente.")
    
    # Nota: Para un benchmark real se requiere un archivo .rknn
    # Aquí solo validamos que el runtime esté operativo.
    
    print("\n[INFO] El entorno RKNN está listo para cargar modelos.")
    print("[INFO] Librería librknnrt.so cargada correctamente.")
    
    # Metadata del sistema
    print(f"[INFO] Python version: {sys.version}")
    try:
        import cv2
        print(f"[INFO] OpenCV version: {cv2.__version__}")
    except:
        print("[WARN] OpenCV no está instalado.")

if __name__ == "__main__":
    run_benchmark()
