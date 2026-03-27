import sys
import subprocess
import os
from pathlib import Path

def get_gpg_path():
    if sys.platform == "win32":
        # Buscar en rutas comunes de Git y Gpg4win
        common_paths = [
            r"C:\Program Files\Git\usr\bin\gpg.exe",
            r"C:\Program Files (x86)\gnupg\bin\gpg.exe",
            r"C:\Program Files\gnupg\bin\gpg.exe"
        ]
        for p in common_paths:
            if Path(p).exists():
                return p
    return "gpg" # Confiar en PATH en Linux o si ya está puesto

def configure_git(gpg_path, key_id=None):
    try:
        subprocess.run(["git", "config", "--global", "gpg.program", gpg_path], check=True)
        subprocess.run(["git", "config", "--global", "commit.gpgsign", "true"], check=True)
        if key_id:
            subprocess.run(["git", "config", "--global", "user.signingkey", key_id], check=True)
        return True
    except Exception as e:
        print(f"[ERROR] No se pudo configurar Git: {e}")
        return False

def check_signature_status():
    print("[STATUS] Verificando estado de firma en el repositorio...")
    try:
        # Verificar el último commit
        result = subprocess.run(["git", "log", "-1", "--show-signature"], capture_output=True, text=True)
        if "gpg: Good signature" in result.stdout or "gpg: firma correcta" in result.stdout:
            print("[OK] El último commit está verificado y firmado.")
            return True
        else:
            print("[WARN] El último commit NO tiene una firma válida.")
            return False
    except Exception as e:
        print(f"[ERROR] Error al verificar firma: {e}")
        return False

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        if not check_signature_status():
            sys.exit(1)
        sys.exit(0)

    print("=== Configurador de Soberanía Biométrica (GPG) ===")
    gpg_path = get_gpg_path()
    print(f"[INFO] Motor GPG detectado en: {gpg_path}")
    
    key_id = input("Introduce tu ID de Llave GPG (ej: ABC123DEF456) [Deja en blanco para solo habilitar firma]: ").strip()
    
    if configure_git(gpg_path, key_id if key_id else None):
        print("[SUCCESS] Git ha sido configurado para requerir firmas biométricas.")
        print("IMPORTANTE: Recuerda habilitar la integración con Windows Hello (PinEntry) en Kleopatra/Gpg4win.")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
