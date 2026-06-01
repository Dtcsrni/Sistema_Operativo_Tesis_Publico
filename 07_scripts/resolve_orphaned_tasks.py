#!/usr/bin/env python3
"""Resolver tareas huérfanas: marcarlas como 'aborted' con fecha actual."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path("runtime/openclaw/state/openclaw.db")
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("🔧 RESOLUCIÓN DE TAREAS HUÉRFANAS")
print("=" * 70)

# Identificar huérfanas
cursor.execute("""
    SELECT t.task_id, t.payload_json, t.created_at
    FROM tasks t
    WHERE t.task_id NOT IN (SELECT task_id FROM task_outcomes)
    ORDER BY t.created_at DESC
""")

orphan_tasks = cursor.fetchall()

if not orphan_tasks:
    print("✅ No hay tareas huérfanas. Sistema íntegro.")
    conn.close()
    exit(0)

print(f"🚨 Se encontraron {len(orphan_tasks)} tarea(s) huérfana(s)\n")

# Mostrar lo que se va a hacer
now_utc = datetime.now(timezone.utc).isoformat()

for task_id, payload_json, created_at in orphan_tasks:
    print(f"  📌 {task_id}")
    print(f"     Creada: {created_at}")
    print(f"     Será marcada como: ABORTED")
    print(f"     Timestamp de conclusión: {now_utc}")
    print()

# Confirmar antes de proceder
response = input("¿Continuar y marcar estas tareas como ABORTED? (s/n): ").strip().lower()

if response != 's':
    print("❌ Operación cancelada.")
    conn.close()
    exit(0)

# Proceder con la resolución
print("\n⏳ Registrando conclusión para cada tarea...\n")

for task_id, payload_json, created_at in orphan_tasks:
    try:
        outcome_id = f"OUTCOME-{task_id}-ABORTED"
        error_text = f"Tarea huérfana detectada durante auditoría del 2026-05-05. " \
                     f"Creada el {created_at}. Marcada como abortada."
        
        recovery_payload = json.dumps({
            "recovery": True,
            "reason": "orphan_task_resolution",
            "audit_date": "2026-05-05",
            "original_task_id": task_id
        })
        
        cursor.execute("""
            INSERT INTO task_outcomes 
            (outcome_id, task_id, domain, provider, outcome, request_kind, complexity, error_text, payload_json, created_at)
            VALUES (?, ?, 'unknown', 'system_audit', 'aborted', 'orphan_recovery', 'unknown', ?, ?, ?)
        """, (outcome_id, task_id, error_text, recovery_payload, now_utc))
        
        print(f"  ✅ {task_id} → ABORTED")
    except Exception as e:
        print(f"  ❌ {task_id} → ERROR: {e}")

conn.commit()
print("\n💾 Cambios guardados en la base de datos.")

# Verificación final
cursor.execute("SELECT COUNT(*) FROM tasks WHERE task_id NOT IN (SELECT task_id FROM task_outcomes)")
remaining_orphans = cursor.fetchone()[0]

if remaining_orphans == 0:
    print("\n✅ RESOLUCIÓN EXITOSA: Sistema completamente íntegro.")
else:
    print(f"\n⚠️ Aún hay {remaining_orphans} tarea(s) sin resolver.")

conn.close()
