import os
import sys
import time
from pathlib import Path

# Configurar rutas para importar runtime.openclaw
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    from runtime.openclaw.openclaw_local.progress import AdvancedProgressMonitor
except ImportError as e:
    print(f"[ERROR] No se pudo importar AdvancedProgressMonitor: {e}")
    sys.exit(1)

def get_dir_size(path):
    """Calcula el tamaño de un directorio en bytes."""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    except Exception:
        pass
    return total

def main():
    # Cargar credenciales manuales
    CHAT_ID = "6866872051"
    
    # Metadatos del proceso
    MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
    QUANT = "W4A16 (Experimental)"
    TARGET_NODE = "Orange Pi 5 Plus (8GB RAM)"
    
    TARGET_DIR = ROOT / "runtime/models/edge/ds-r1-7b-hf"
    TOTAL_EXPECTED_SIZE = 15 * 1024 * 1024 * 1024 # ~15GB
    
    print(f"[*] Iniciando monitor de notificaciones para {MODEL_ID}...")
    
    title = f"Fase 1: Descarga {MODEL_ID}"
    process_info = (
        f"<b>🎯 Objetivo:</b> {MODEL_ID}\n"
        f"<b>🛠 Cuantización:</b> {QUANT}\n"
        f"<b>🖥 Nodo Destino:</b> {TARGET_NODE}\n"
        f"<b>📦 Tamaño est.:</b> ~15GB (FP16)"
    )
    
    with AdvancedProgressMonitor(CHAT_ID, title, total_items=100) as monitor:
        # Enviar información detallada del proceso en el primer mensaje (editando el inicial)
        monitor.update(current=0, title=f"{title}\n{process_info}")
        while True:
            current_size = get_dir_size(TARGET_DIR)
            progress_pct = int((current_size / TOTAL_EXPECTED_SIZE) * 100)
            if progress_pct > 100: progress_pct = 100
            
            # Actualizar monitor
            monitor.update(current=progress_pct, title=f"Descarga DS-R1-7B: {current_size / (1024**3):.2f}GB / 15GB")
            
            if progress_pct >= 100:
                print("[SUCCESS] Descarga completada o tamaño objetivo alcanzado.")
                monitor.finish(success=True, final_text="Descarga FP16 finalizada. Listo para iniciar fase de compilación RKLLM.")
                break
                
            # Verificar si el proceso de descarga sigue vivo (opcional, pero recomendado)
            # Como este script corre independiente, simplemente dormimos.
            time.sleep(30)

if __name__ == "__main__":
    main()
