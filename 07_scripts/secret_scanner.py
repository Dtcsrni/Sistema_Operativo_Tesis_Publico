import sys
import os
from pathlib import Path
import re

# Patrones comunes de secretos
PATTERNS = {
    "GitHub PAT (Classic)": r"ghp_[a-zA-Z0-9]{36}",
    "GitHub PAT (Fine-grained)": r"github_pat_[a-zA-Z0-9_]{82}",
}

EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
EXCLUDE_FILES = {".env.example", "common.py", "sign_off.py"} # Scripts que pueden contener el nombre de la variable pero no el valor real si se manejan bien

def scan():
    root = Path(__file__).resolve().parents[1]
    found_secrets = []

    for path in root.rglob("*"):
        if any(exc in path.parts for exc in EXCLUDE_DIRS):
            continue
        if path.name in EXCLUDE_FILES or not path.is_file():
            continue
        
        # Saltar archivos binarios
        if path.suffix in {".png", ".jpg", ".pyc", ".exe"}:
            continue

        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            for name, pattern in PATTERNS.items():
                if re.search(pattern, content):
                    found_secrets.append(f"{name} encontrado en: {path.relative_to(root)}")
        except Exception as e:
            print(f"[WARN] No se pudo escanear {path}: {e}")

    return found_secrets

def main():
    print("[PROCESS] Escaneando secretos en el repositorio...")
    secrets = scan()
    if secrets:
        print("\n[CRITICAL ERROR] Se encontraron potenciales secretos en el código:")
        for s in secrets:
            print(f"  - {s}")
        print("\nPOR SEGURIDAD, EL BUILD SE HA DETENIDO. Limpie los secretos y use variables de entorno (.env)")
        sys.exit(1)
    else:
        print("[OK] No se detectaron secretos evidentes.")

if __name__ == "__main__":
    main()
