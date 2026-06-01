#!/usr/bin/env python3
"""
openclaw_sentinel.py -- El vigía proactivo del Sistema de Tesis.
Monitorea cambios, descubre nuevos hallazgos y envía recordatorios via Telegram.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta, UTC

# Añadir el path para importar módulos de openclaw_local
repo_root = Path(__file__).resolve().parents[2]
sys.path.append(str(repo_root))

from runtime.openclaw.openclaw_local.notifier import broadcast_discovery, broadcast_nudge
from runtime.openclaw.openclaw_local.storage import OpenClawStore

def get_last_ledger_entry():
    ledger_path = repo_root / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md"
    if not ledger_path.exists():
        return None
    return ledger_path.stat().st_mtime

def check_thesis_stagnation(store):
    last_mtime = get_last_ledger_entry()
    if not last_mtime:
        return
    
    elapsed_days = (time.time() - last_mtime) / 86400
    if 1.0 < elapsed_days < 1.1: # Nudge una vez al día aprox
        broadcast_nudge(
            "Erick, ha pasado un día desde la última entrada en la bitácora. "
            "¿Te gustaría retomar hoy la investigación sobre LoRa o revisar los pendientes?"
        )

def check_new_decisions():
    decisiones_dir = repo_root / "00_sistema_tesis" / "decisiones"
    state_file = repo_root / "runtime" / "openclaw" / "state" / "last_decision_check.txt"
    
    if not decisiones_dir.exists():
        return
    
    last_count = 0
    if state_file.exists():
        try:
            last_count = int(state_file.read_text().strip())
        except ValueError: pass
        
    current_files = list(decisiones_dir.glob("*.md"))
    current_count = len(current_files)
    
    if current_count > last_count:
        new_files = current_files[last_count:]
        for f in new_files:
            broadcast_discovery(
                f"Nueva Decisión Arquitectónica: {f.name}",
                "He detectado una nueva decisión formalizada. Procedo a indexarla en mi memoria técnica."
            )
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(str(current_count))

def main():
    print(f"[SENTINEL] Iniciando vigilancia proactiva...")
    db_path = Path(os.getenv("OPENCLAW_DB_PATH", repo_root / "runtime" / "openclaw" / "state" / "openclaw.db"))
    store = OpenClawStore(db_path)
    
    while True:
        try:
            # 1. Verificar estancamiento (recordatorios)
            check_thesis_stagnation(store)
            
            # 2. Verificar nuevos hitos (decisiones)
            check_new_decisions()
            
            # 3. Dormir (ej. revisar cada hora)
            time.sleep(3600)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[SENTINEL ERROR] {e}")
            time.sleep(300)

if __name__ == "__main__":
    main()
