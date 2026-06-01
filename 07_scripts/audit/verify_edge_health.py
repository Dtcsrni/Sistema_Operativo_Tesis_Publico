import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import subprocess
import os

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "07_scripts"))
from rknpu_detect import rknpu_summary

def verify_edge_environment():
    print("[*] Verificando entorno de Nodo Edge...")
    
    # 1. Verificar arquitectura
    arch = subprocess.check_output(["uname", "-m"], text=True).strip()
    if arch != "aarch64":
        print(f"[WARN] Arquitectura {arch} no es nativa de Orange Pi 5 Plus (aarch64).")
    else:
        print("[OK] Arquitectura ARM64 detectada.")

    # 2. Verificar acceso a NPU
    npu = rknpu_summary()
    if npu["ready"]:
        print(f"[OK] Acelerador NPU RK3588 detectado: {', '.join(npu['devices'])}.")
    else:
        print("[WARN] No se detectó NPU RK3588 por /dev/rknpu, /dev/rknn ni DRM render RKNPU. La inferencia será por CPU.")

    # 3. Verificar acceso a GPIO/I2C
    if os.path.exists("/dev/i2c-1") or os.path.exists("/dev/gpiomem"):
        print("[OK] Bus de hardware detectado.")
    else:
        print("[WARN] No se detectaron buses de sensores. Verifique privilegios del contenedor.")

    return True

if __name__ == "__main__":
    # Este script está diseñado para correr DENTRO del contenedor edge o en el host edge
    try:
        verify_edge_environment()
    except Exception as e:
        print(f"[ERROR] Falló la verificación edge: {e}")
        sys.exit(1)
