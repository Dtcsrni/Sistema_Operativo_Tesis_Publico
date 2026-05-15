import sqlite3
from pathlib import Path

DB = Path('04_implementacion/control_mission/mission-control.db')
if not DB.exists():
    print('DB not found:', DB)
    raise SystemExit(1)
conn = sqlite3.connect(str(DB))
cur = conn.cursor()
cur.execute("SELECT id,title,status,status_reason,updated_at FROM tasks WHERE title LIKE 'Prueba: Crear misión%'")
rows = cur.fetchall()
if not rows:
    print('No matching tasks found')
else:
    for r in rows:
        print('TASK:', r)
conn.close()
