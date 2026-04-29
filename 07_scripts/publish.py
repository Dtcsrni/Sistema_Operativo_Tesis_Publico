#!/usr/bin/env python3
# 07_scripts/publish.py
# Script unificado para: Build -> Audit -> Commit -> Sync -> Push

import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run(cmd, cwd=ROOT):
    print(f"[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Comando falló con código {result.returncode}")
        sys.exit(result.returncode)
    return result

def main():
    print("=== PIPELINE DE PUBLICACIÓN SOBERANA ===")
    
    # 1. Verificar si estamos en WSL (Recomendado)
    is_wsl = "microsoft-standard" in Path("/proc/version").read_text().lower() if Path("/proc/version").exists() else False
    if not is_wsl and os.name == 'posix':
         print("[INFO] Ejecutando en entorno POSIX (Linux/macOS)")
    elif not is_wsl:
        print("[WARN] Se recomienda ejecutar este script desde WSL para garantizar integridad de dependencias.")
        # Podríamos intentar relanzar con wsl, pero mejor dejar que el usuario decida.

    # 2. Build & Audit
    print("\n--- Fase 1: Construcción y Auditoría ---")
    run(["python3", "07_scripts/build_all.py"])

    # 3. Git Status (Privado)
    print("\n--- Fase 2: Estado del Repositorio Privado ---")
    status = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if status:
        print("[INFO] El repositorio privado tiene cambios:")
        print(status)
        confirm = input("\n¿Deseas commitear estos cambios automáticamente? [y/N]: ").lower()
        if confirm == 'y':
            msg = input("Mensaje de commit [chore: actualización automática de trazabilidad]: ") or "chore: actualización automática de trazabilidad"
            run(["git", "add", "."])
            run(["git", "commit", "-m", msg])
    else:
        print("[OK] Repositorio privado limpio.")

    # 4. Sync & Push (Público)
    print("\n--- Fase 3: Sincronización Pública ---")
    push_confirm = input("¿Deseas sincronizar y hacer PUSH al repositorio público? [y/N]: ").lower()
    if push_confirm == 'y':
        # Nota: sync_public_repo.py ya maneja la sanitización
        run(["python3", "07_scripts/sync_public_repo.py", "--push", "--allow-dirty"])
        print("\n[SUCCESS] Publicación completada exitosamente.")
    else:
        print("\n[INFO] Sincronización omitida. Ejecuta 'python3 07_scripts/sync_public_repo.py --check' para verificar manualmente.")

if __name__ == "__main__":
    main()
