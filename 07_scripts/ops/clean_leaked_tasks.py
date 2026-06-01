#!/usr/bin/env python3
"""
clean_leaked_tasks.py - Limpia las misiones de prueba con título 'T' y sus registros
relacionados en la base de datos de Mission Control. Crea un respaldo antes de operar.
"""

import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "04_implementacion" / "control_mission" / "mission-control.db"
BACKUP_DIR = DB_PATH.parent / "db-backups"

def main():
    print("=== LIMPIEZA DE TAREAS DE PRUEBA LEAKED ===")
    if not DB_PATH.exists():
        print(f"[FAIL] No se encontró la base de datos en: {DB_PATH}")
        return 1

    # 1. Crear backup de seguridad
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"mission-control.pre-cleanup.{ts}.db"
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"[OK] Respaldo de seguridad creado en: {backup_path.relative_to(ROOT)}")
    except Exception as e:
        print(f"[FAIL] No se pudo crear el respaldo de seguridad: {e}")
        return 1

    # 2. Conectar y borrar las misiones de prueba
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    
    try:
        # Habilitar claves foráneas
        cur.execute("PRAGMA foreign_keys = ON")
        
        # Buscar tareas a eliminar (incluyendo la de integración E2E si se filtró)
        cur.execute("SELECT id, title, status FROM tasks WHERE title = 'T' OR title = 'Test Integration Task' OR id = 'integration-task-uuid-123'")
        tasks_to_delete = cur.fetchall()
        
        if not tasks_to_delete:
            print("[INFO] No se encontraron misiones de prueba ('T' o 'Test Integration Task') en la base de datos.")
            conn.close()
            return 0
            
        print(f"[INFO] Se encontraron {len(tasks_to_delete)} tareas de prueba para eliminar.")
        for t in tasks_to_delete:
            print(f"  - ID: {t[0]} | Title: {t[1]} | Status: {t[2]}")
            
        task_ids = [t[0] for t in tasks_to_delete]
        placeholders = ",".join("?" for _ in task_ids)
        
        # Eliminar entregables
        cur.execute(f"DELETE FROM task_deliverables WHERE task_id IN ({placeholders})", task_ids)
        del_count = cur.rowcount
        print(f"[OK] Eliminados {del_count} entregables relacionados.")
        
        # Eliminar actividades
        cur.execute(f"DELETE FROM task_activities WHERE task_id IN ({placeholders})", task_ids)
        act_count = cur.rowcount
        print(f"[OK] Eliminadas {act_count} actividades relacionadas.")
        
        # Eliminar checkpoints de trabajo si existen
        cur.execute(f"DELETE FROM work_checkpoints WHERE task_id IN ({placeholders})", task_ids)
        checkpoint_count = cur.rowcount
        print(f"[OK] Eliminados {checkpoint_count} checkpoints de trabajo.")
        
        # Eliminar tareas
        cur.execute(f"DELETE FROM tasks WHERE id IN ({placeholders})", task_ids)
        task_count = cur.rowcount
        print(f"[OK] Eliminadas {task_count} tareas de prueba.")
        
        conn.commit()
        print("[SUCCESS] Limpieza completada con éxito.")
        
    except Exception as e:
        conn.rollback()
        print(f"[FAIL] Error durante la transacción de limpieza: {e}")
        return 1
    finally:
        conn.close()
        
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
