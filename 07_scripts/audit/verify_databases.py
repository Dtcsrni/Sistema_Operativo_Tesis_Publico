import sqlite3
import os
import sys
from pathlib import Path

# Configuración de bases de datos críticas
CRITICAL_DATABASES = [
    "04_implementacion/control_mission/data/mission-control.db",
    "runtime/openclaw/openclaw_store.db",
    "runtime/openclaw/state/openclaw.db",
]

def check_integrity(db_path: Path) -> tuple[bool, str]:
    if not db_path.exists():
        return True, "No existe (se creará limpia)"
    
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        if result == ("ok",):
            return True, "Integridad OK"
        else:
            return False, f"FALLO: {result}"
    except Exception as e:
        return False, f"ERROR: {e}"

def main():
    root = Path(__file__).resolve().parents[2]
    all_ok = True
    print("## Auditoría de Integridad de Bases de Datos SQLite")
    print("")
    
    for rel_path in CRITICAL_DATABASES:
        db_path = root / rel_path
        ok, msg = check_integrity(db_path)
        status_icon = "✅" if ok else "❌"
        print(f"- {status_icon} `{rel_path}`: {msg}")
        if not ok:
            all_ok = False
            
    if not all_ok:
        print("\n[!] Algunas bases de datos están corruptas. Usa `python 07_scripts/ops/db_maintenance.py <path> --repair`.")
        sys.exit(1)
    else:
        print("\n[OK] Todas las bases de datos críticas están sanas.")
        sys.exit(0)

if __name__ == "__main__":
    main()
