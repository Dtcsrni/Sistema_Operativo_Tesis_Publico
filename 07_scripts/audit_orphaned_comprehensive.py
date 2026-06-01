#!/usr/bin/env python3
"""Búsqueda exhaustiva de tareas huérfanas en la base de datos."""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path("runtime/openclaw/state/openclaw.db")
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("🔍 AUDITORÍA EXHAUSTIVA DE INTEGRIDAD DE TAREAS")
print("=" * 70)

# Estadísticas generales
cursor.execute("SELECT COUNT(*) FROM tasks")
total_tasks = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM task_outcomes")
total_outcomes = cursor.fetchone()[0]

print(f"\n📊 Estadísticas Generales:")
print(f"  • Total de tareas en BD: {total_tasks}")
print(f"  • Total de outcomes: {total_outcomes}")
print(f"  • Tareas sin outcome (potencialmente huérfanas): {total_tasks - total_outcomes}")

if total_tasks - total_outcomes > 0:
    print(f"\n🚨 ALERTA: Hay {total_tasks - total_outcomes} tarea(s) sin conclusión\n")
    
    cursor.execute("""
        SELECT t.task_id, t.created_at, t.payload_json
        FROM tasks t
        WHERE t.task_id NOT IN (SELECT task_id FROM task_outcomes)
        ORDER BY t.created_at DESC
        LIMIT 20
    """)
    
    orphan_tasks = cursor.fetchall()
    for task_id, created_at, payload in orphan_tasks:
        print(f"  ⚠️ {task_id}")
        print(f"     Creada: {created_at}")
        try:
            p = json.loads(payload)
            if "title" in p:
                print(f"     Título: {p['title']}")
            if "objective" in p:
                print(f"     Objetivo: {p['objective'][:60]}")
        except:
            pass
        print()
else:
    print(f"\n✅ TODAS LAS TAREAS TIENEN OUTCOME REGISTRADO")

# Verificar integridad de outcomes sin tareas asociadas
print("\n" + "-" * 70)
print("🔗 Verificación de Integridad Referencial:")

cursor.execute("""
    SELECT COUNT(*) FROM task_outcomes 
    WHERE task_id NOT IN (SELECT task_id FROM tasks)
""")
orphan_outcomes = cursor.fetchone()[0]

if orphan_outcomes > 0:
    print(f"⚠️ ALERTA: {orphan_outcomes} outcome(s) sin tarea asociada (problema de integridad referencial)")
else:
    print(f"✅ Integridad referencial: OK")

# Distribución de outcomes por tipo
print("\n" + "-" * 70)
print("📈 Distribución de Resultados:")

cursor.execute("""
    SELECT outcome, COUNT(*) as count 
    FROM task_outcomes 
    GROUP BY outcome 
    ORDER BY count DESC
""")

for outcome, count in cursor.fetchall():
    print(f"  • {outcome}: {count}")

# Tareas más recientes (últimas 24h)
print("\n" + "-" * 70)
print("📅 Tareas Recientes (últimas 10):")

cursor.execute("""
    SELECT t.task_id, t.created_at, 
           CASE WHEN tout.outcome_id IS NOT NULL THEN '✅' ELSE '⚠️' END as has_outcome
    FROM tasks t
    LEFT JOIN task_outcomes tout ON t.task_id = tout.task_id
    ORDER BY t.created_at DESC
    LIMIT 10
""")

for task_id, created_at, has_outcome in cursor.fetchall():
    print(f"  {has_outcome} {task_id} ({created_at})")

conn.close()
