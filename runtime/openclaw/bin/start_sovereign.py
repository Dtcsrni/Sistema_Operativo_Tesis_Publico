import os
import threading
import subprocess
import sys
import time
from pathlib import Path

def run_telegram_bot():
    print("[INIT] Lanzando Hilo de Telemetría (Telegram)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = "/workspace/runtime/openclaw:/workspace"
    # Ejecutamos con -m para que resuelva imports relativos
    subprocess.run([sys.executable, "-m", "openclaw_local.telegram_bot"], env=env, cwd="/workspace/runtime/openclaw")

def run_gateway_server():
    print("[INIT] Lanzando Hilo de Misiones (Pasarela Gateway)...")
    host = os.getenv("OPENCLAW_HOST", "0.0.0.0")
    port = os.getenv("OPENCLAW_PORT", "18789")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = "/workspace/runtime/openclaw:/workspace"
    
    # Usamos el CLI renombrado para evitar conflictos de nombre de módulo
    cmd = [
        sys.executable, 
        "/workspace/runtime/openclaw/bin/openclaw_cli.py", 
        "pasarela", 
        "servir", 
        "--host", host, 
        "--puerto", port
    ]
    subprocess.run(cmd, env=env, cwd="/workspace")

if __name__ == "__main__":
    print("======================================================")
    print("   ORQUESTADOR SOBERANO TOLTECAYOTL - MULTI-HILO")
    print("======================================================")
    
    # Configurar PYTHONPATH para que encuentre los módulos locales
    os.environ["PYTHONPATH"] = "/workspace/07_scripts:/workspace/runtime/openclaw:/workspace/runtime/openclaw/openclaw_local:/workspace"
    
    # Iniciar hilos
    t1 = threading.Thread(target=run_gateway_server, daemon=True)
    t2 = threading.Thread(target=run_telegram_bot, daemon=True)
    
    t1.start()
    time.sleep(2) # Dar tiempo a que el server abra el socket
    t2.start()
    
    # Mantener el proceso principal vivo
    try:
        while True:
            time.sleep(1)
            if not t1.is_alive():
                print("[CRITICAL] El hilo de la Pasarela ha muerto. Reiniciando...")
                t1 = threading.Thread(target=run_gateway_server, daemon=True)
                t1.start()
            if not t2.is_alive():
                print("[WARN] El hilo de Telegram ha muerto. Reiniciando...")
                t2 = threading.Thread(target=run_telegram_bot, daemon=True)
                t2.start()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Cerrando orquestador soberano...")
