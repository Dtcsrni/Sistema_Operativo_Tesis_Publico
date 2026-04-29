import os
import requests
from pathlib import Path

# URL de un modelo Llama-3.2-3B pre-convertido confiable para RK3588
MODEL_URL = "https://huggingface.co/jamescallander/Llama-3.2-3B-Instruct-RK3588-RKLLM/resolve/main/Llama-3.2-3B-Instruct_w8a8_g128_rk3588.rkllm"
TARGET_PATH = "runtime/models/edge/llama3_2_3b_rkllm.rkllm"

def download_file(url, dest_path):
    print(f"[INFO] Iniciando descarga de modelo pre-convertido...")
    print(f"       Desde: {url}")
    print(f"       Hacia: {dest_path}")
    
    # Crear directorio si no existe
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024 * 1024 # 1MB
    
    downloaded = 0
    with open(dest_path, 'wb') as f:
        for data in response.iter_content(block_size):
            f.write(data)
            downloaded += len(data)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"\r       Progreso: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)", end="")
    print("\n[OK] Descarga completada.")

def main():
    root = Path(__file__).parent.parent.absolute()
    dest = root / TARGET_PATH
    
    try:
        download_file(MODEL_URL, dest)
        print(f"\n[SUCCESS] Modelo listo para el Edge en: {TARGET_PATH}")
        print("Siguiente paso: Transferir al Orange Pi 5 Plus y ejecutar benchmark.")
    except Exception as e:
        print(f"\n[ERROR] Falló la descarga automática: {e}")
        print("Por favor, descarga manualmente el modelo desde HuggingFace y colócalo en runtime/models/edge/")

if __name__ == "__main__":
    main()
