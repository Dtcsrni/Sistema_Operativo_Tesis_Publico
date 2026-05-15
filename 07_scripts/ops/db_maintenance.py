#!/usr/bin/env python3
"""
Mantenimiento y Reparación de Bases de Datos SQLite (SIOT/Mission Control).
Soporta: Check de integridad, Backup y Recuperación por volcado (Dump/Restore).
"""

import sqlite3
import os
import sys
import shutil
import time
from pathlib import Path

def check_integrity(db_path: str) -> bool:
    """Verifica la integridad de la base de datos."""
    if not os.path.exists(db_path):
        return True # Si no existe, se creará limpia
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        return result == ("ok",)
    except Exception as e:
        print(f"Error al verificar integridad: {e}")
        return False

def repair_db(db_path: str) -> bool:
    """Repara la base de datos usando dump/restore."""
    print(f"[REPAIR] Iniciando reparación de: {db_path}")
    backup_path = f"{db_path}.corrupt_{int(time.time())}"
    dump_path = f"{db_path}.sql"
    new_db_path = f"{db_path}.repaired"
    
    try:
        # 1. Backup del corrupto
        shutil.copy2(db_path, backup_path)
        print(f"[BACKUP] Backup de emergencia creado en: {backup_path}")
        
        # 2. Dump
        print("[DUMP] Extrayendo datos (iterdump)...")
        conn_old = sqlite3.connect(db_path)
        with open(dump_path, "w", encoding="utf-8") as f:
            for line in conn_old.iterdump():
                f.write(f"{line}\n")
        conn_old.close()
        
        # 3. Sanitize (Optional but recommended for known issues)
        print("[CLEAN] Sanitizando contenido (ASCII normalization)...")
        with open(dump_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Correcciones específicas conocidas que causan errores de encoding en el stack
        content = content.replace("Epistémico", "Epistemico")
        
        with open(dump_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 4. Restore
        print("[RESTORE] Restaurando en nueva imagen...")
        if os.path.exists(new_db_path):
            os.remove(new_db_path)
            
        conn_new = sqlite3.connect(new_db_path)
        with open(dump_path, "r", encoding="utf-8") as f:
            conn_new.executescript(f.read())
        conn_new.close()
        
        # 5. Verificación de la reparación
        if check_integrity(new_db_path):
            print("[SUCCESS] Reparación exitosa. Reemplazando archivo original...")
            os.remove(db_path)
            os.rename(new_db_path, db_path)
            if os.path.exists(dump_path):
                os.remove(dump_path)
            return True
        else:
            print("❌ La reparación no pasó el chequeo de integridad final.")
            return False
            
    except Exception as e:
        print(f"💥 Error crítico durante la reparación: {e}")
        return False

def main():
    # Asegurar salida en UTF-8 en Windows para evitar UnicodeEncodeError con emojis
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    if len(sys.argv) < 2:
        print("Uso: python db_maintenance.py <path_to_db> [--repair]")
        sys.exit(1)
        
    db_path = sys.argv[1]
    do_repair = "--repair" in sys.argv
    
    print(f"[SEARCH] Analizando base de datos: {db_path}")
    
    if check_integrity(db_path):
        print("[OK] Integridad correcta.")
        sys.exit(0)
    else:
        print("[WARN] CORRUPCIÓN DETECTADA.")
        if do_repair:
            if repair_db(db_path):
                print("[DONE] Proceso completado con éxito.")
                sys.exit(0)
            else:
                print("[ERROR] Falló la reparación automática.")
                sys.exit(1)
        else:
            print("[INFO] Usa --repair para intentar arreglarla automáticamente.")
            sys.exit(1)

if __name__ == "__main__":
    main()
