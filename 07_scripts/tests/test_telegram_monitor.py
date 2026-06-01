import os
import sys
import time
from pathlib import Path

# Configurar rutas para importar runtime.openclaw
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Cargar variables de entorno manualmente desde config/env/openclaw.env
def load_openclaw_env():
    env_path = ROOT / "config/env/openclaw.env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"')

load_openclaw_env()

try:
    from runtime.openclaw.openclaw_local.progress import AdvancedProgressMonitor
except ImportError as e:
    print(f"[ERROR] No se pudo importar AdvancedProgressMonitor: {e}")
    sys.exit(1)

def test_telegram_notification():
    chat_id = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID")
    if not chat_id:
        print("[ERROR] OPENCLAW_TELEGRAM_CHAT_ID no encontrado en el entorno.")
        return

    print(f"[*] Iniciando prueba de canal de Telegram para el Chat ID: {chat_id}...")
    
    title = "PRUEBA DE CANAL: Pipeline Experimental"
    process_info = (
        "<b>🧪 Test de Conectividad</b>\n"
        "<b>🤖 Proceso:</b> Validación de Orquestador Maestro\n"
        "<b>📉 Estado:</b> Iniciando monitoreo de larga espera\n"
        "<b>✅ Entrega Garantizada:</b> Verificando handshake..."
    )

    try:
        with AdvancedProgressMonitor(chat_id, title, total_items=5) as monitor:
            # Enviar información detallada del proceso en el primer mensaje
            monitor.update(current=0, title=f"{title}\n\n{process_info}")
            print("[OK] Primer mensaje enviado. Verifica tu Telegram.")
            
            # Simular un pequeño progreso
            for i in range(1, 4):
                time.sleep(2)
                monitor.update(current=i, title=f"{title}\n\n{process_info}\n\n<i>Paso de prueba {i}/3 completado...</i>")
                print(f"[*] Paso {i} de prueba enviado.")
            
            monitor.finish(success=True, final_text="Prueba de canal exitosa. El sistema de notificaciones está operativo.")
            print("[SUCCESS] Prueba finalizada correctamente.")
            
    except Exception as e:
        print(f"[FAIL] Error durante la prueba de Telegram: {e}")

if __name__ == "__main__":
    test_telegram_notification()
