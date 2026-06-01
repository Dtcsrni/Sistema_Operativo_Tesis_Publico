import os
import time
import sys
from pathlib import Path

# Asegurar que el root del repo esté en el path para los imports
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(repo_root))

from runtime.openclaw.openclaw_local.progress import AdvancedProgressMonitor

def simulate_heavy_task():
    chat_id = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "").split(",")[0]
    if not chat_id:
        print("Error: OPENCLAW_TELEGRAM_CHAT_ID no configurado.")
        return

    print(f"Iniciando tarea pesada para chat {chat_id}...")
    
    total = 5
    with AdvancedProgressMonitor(
        chat_id, 
        "🔨 Reconstrucción de Canon de Tesis", 
        total_items=total,
        update_interval=5.0 # Más rápido para este ejemplo
    ) as monitor:
        
        for i in range(total):
            time.sleep(3) # Simular trabajo
            monitor.update(current=i + 1, title=f"🔨 Procesando fase {i+1}")
            print(f"Fase {i+1} completada.")
            
    print("Tarea finalizada con éxito.")

if __name__ == "__main__":
    # Cargar .env para pruebas manuales si es necesario
    simulate_heavy_task()
