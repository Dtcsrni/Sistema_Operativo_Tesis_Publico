import subprocess
import os
import tempfile
import sys
from pathlib import Path

# Cargar datos del tesista
TESISTA_CONFIG = Path("00_sistema_tesis/config/tesista.json")

def run_unattended_gen():
    if not TESISTA_CONFIG.exists():
        print("[ERROR] No se encuentra tesista.json. Corre el build primero.")
        return

    import json
    with open(TESISTA_CONFIG, 'r', encoding='utf-8') as f:
        data = json.load(f)["tesista"]

    nombre = data["nombre_completo"]
    email = data["identidad_digital"]["emails_autorizados"][0]
    cedula = data.get("cedula_profesional", "N/A")
    cuenta = data.get("numero_cuenta", "N/A")
    
    comment = f"Tesis IoT UAEH | Ced: {cedula} | Cuenta: {cuenta}"

    # Crear archivo de lote para GPG
    batch_content = f"""
    Key-Type: RSA
    Key-Length: 4096
    Subkey-Type: RSA
    Subkey-Length: 4096
    Name-Real: {nombre}
    Name-Email: {email}
    Name-Comment: {comment}
    Expire-Date: 0
    %commit
    """

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp:
        tmp.write(batch_content.strip())
        tmp_path = tmp.name

    print(f"=== Generando Llave Maestra para: {nombre} ===")
    print(f"[INFO] Identidad: {email}")
    print(f"[INFO] Comentario: {comment}")
    print("\n[!] A continuación aparecerá una ventana de Windows pidiendo tu CONTRASEÑA.")
    print("[!] RECUERDA: Esta contraseña es tu SELLO DE SOBERANÍA. No la compartas con la IA.\n")

    gpg_path = r"C:\Program Files\Git\usr\bin\gpg.exe"
    if not os.path.exists(gpg_path):
        gpg_path = "gpg"

    try:
        subprocess.run([gpg_path, "--batch", "--generate-key", tmp_path], check=True)
        print("\n[SUCCESS] Llave generada exitosamente.")
        print("[PROXIMO PASO] Corre: python 07_scripts/setup_gpg_attestation.py")
    except Exception as e:
        print(f"\n[ERROR] Falló la generación: {e}")
    finally:
        os.unlink(tmp_path)

if __name__ == "__main__":
    run_unattended_gen()
