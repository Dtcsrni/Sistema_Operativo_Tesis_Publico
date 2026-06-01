"""
Inspección de Mission Control DB: agentes y tareas (solo lectura)
No realiza cambios.

Salida:
- Columnas de `agents` y muestra de entradas
- Para cada agente: último heartbeat/actividad y conteo de tareas asignadas
- Listado de tareas recientes con estado y assigned_agent_id
"""
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

DB = Path('04_implementacion/control_mission/mission-control.db')
if not DB.exists():
    print('DB not found:', DB)
    raise SystemExit(1)

conn = sqlite3.connect(str(DB))
cur = conn.cursor()

# Helper: safe query

def table_columns(table_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = [r[1] for r in cur.fetchall()]
    return cols

print('--- mission-control DB inspection ---')
print('DB:', DB)

# Show agents table columns
try:
    agent_cols = table_columns('agents')
    print('\nagents columns:', agent_cols)
except Exception as e:
    print('\nCould not read agents table schema:', e)
    agent_cols = []

# Show sample agents
if agent_cols:
    sel = ', '.join(agent_cols)
    try:
        cur.execute(f"SELECT {sel} FROM agents ORDER BY updated_at DESC LIMIT 50")
        rows = cur.fetchall()
        print(f"\nFound {len(rows)} agent(s) (showing up to 50):")
        now = datetime.now(timezone.utc)
        for r in rows:
            rec = dict(zip(agent_cols, r))
            aid = rec.get('id') or rec.get('agent_id') or '<no-id>'
            name = rec.get('name') or rec.get('display_name') or rec.get('role') or ''
            last = rec.get('last_activity_at') or rec.get('updated_at') or rec.get('created_at')
            status = rec.get('status') or rec.get('state') or ''
            # parse last timestamp if possible
            last_dt = None
            if last:
                try:
                    last_dt = datetime.fromisoformat(last.replace('Z', '+00:00'))
                except Exception:
                    last_dt = None
            age = None
            if last_dt:
                age = (now - last_dt).total_seconds()
            print(f"- agent {aid} name='{name}' status='{status}' last_activity='{last}' age_s={age}")
    except Exception as e:
        print('Error querying agents:', e)

# Tasks summary: recent tasks and assignment
try:
    task_cols = table_columns('tasks')
    print('\n tasks columns:', task_cols)
    # show recent 50 tasks
    sel = ', '.join([c for c in task_cols if c in ['id','title','status','status_reason','assigned_agent_id','updated_at','created_at']])
    cur.execute(f"SELECT {sel} FROM tasks ORDER BY updated_at DESC LIMIT 200")
    tasks = cur.fetchall()
    print(f"\nFound {len(tasks)} recent tasks (showing up to 200):")
    for t in tasks:
        print('-', t)
    # Count tasks per agent
    cur.execute("SELECT assigned_agent_id, COUNT(*) FROM tasks WHERE assigned_agent_id IS NOT NULL GROUP BY assigned_agent_id")
    counts = cur.fetchall()
    print('\nTask counts by assigned_agent_id:')
    for c in counts:
        print(' ', c)
except Exception as e:
    print('Could not read tasks table or columns:', e)

conn.close()
print('\n--- end inspection ---')
