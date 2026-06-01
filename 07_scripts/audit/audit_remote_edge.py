import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import subprocess

import os
import requests

def audit_remote():
    print("[*] Iniciando auditoría remota del Nodo Edge...")
    
    # Intentar vía API del Gateway (si está expuesta por el túnel)
    edge_api_url = os.getenv("EDGE_API_URL", "http://localhost:5000/health")
    try:
        response = requests.get(edge_api_url, timeout=5)
        if response.status_code == 200:
            print("[OK] API del Nodo Edge respondiendo.")
            return True
    except:
        print("[INFO] API remota no disponible. Intentando verificación vía túnel SSH...")

    # Intentar vía SSH (si el túnel reverso está activo)
    # Nota: Requiere configuración de llaves sin contraseña
    try:
        # Verificar si el puerto del túnel reverso está abierto
        result = subprocess.run(["ssh", "-p", "2222", "-o", "ConnectTimeout=3", "tesisai@localhost", "uname -a"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[OK] Conexión SSH al Edge verificada: {result.stdout.strip()}")
            return True
        else:
            print("[WARN] Túnel SSH al Edge no responde.")
    except Exception as e:
        print(f"[ERROR] Error al intentar auditoría remota: {e}")

    return False

if __name__ == "__main__":
    if not audit_remote():
        print("[WARN] El Nodo Edge no está disponible actualmente para auditoría.")
        # No salimos con error 1 para permitir que el build de la PC continúe
        sys.exit(0)
    sys.exit(0)
