import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import json
import subprocess

# Cargar canon.py para usar sus funciones si es posible, o simplemente llamar a tesis.py vía subprocess
# Pero mejor llamar a tesis.py con el escape correcto de python

payload = {
    "bloque": "B0",
    "resultado": "completado",
    "arquitectura": "distribuida_docker",
    "resilience_test": "pass"
}

payload_str = json.dumps(payload)

cmd = [
    sys.executable, "07_scripts/tesis.py", "event", "append",
    "--type", "handshake",
    "--step-id", "VAL-STEP-710",
    "--source-event-id", "EVT-0154",
    "--payload", payload_str
]

subprocess.run(cmd, check=True)
print("[OK] Handshake VAL-STEP-710 registrado.")
