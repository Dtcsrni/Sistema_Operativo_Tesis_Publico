#!/usr/bin/env python3
"""Verificar estructura de BD y buscar tareas huérfanas."""

import sqlite3
from pathlib import Path

DB_PATH = Path("runtime/openclaw/state/openclaw.db")
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Ver estructura de tasks
print("🔍 Estructura de tabla 'tasks':")
cursor.execute("PRAGMA table_info(tasks)")
for col in cursor.fetchall():
    print(f"  • {col[1]}: {col[2]}")

print("\n🔍 Estructura de tabla 'task_outcomes':")
cursor.execute("PRAGMA table_info(task_outcomes)")
for col in cursor.fetchall():
    print(f"  • {col[1]}: {col[2]}")

# Ver muestra de datos
print("\n📊 Muestra de tareas (primeras 5):")
cursor.execute("SELECT * FROM tasks LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
