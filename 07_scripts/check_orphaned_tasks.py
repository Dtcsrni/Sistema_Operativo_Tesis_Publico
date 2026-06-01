#!/usr/bin/env python3
"""Verificar integridad de tareas del Monitor Satélite (sin huérfanas)."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

DB_PATH = Path("runtime/openclaw/state/openclaw.db")

if not DB_PATH.exists():
    print(f"❌ Base de datos no encontrada: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("🛰️ AUDITORÍA DE INTEGRIDAD: MONITOR SATÉLITE v2.3")
print("=" * 70)

# 1. Buscar tareas vinculadas al Monitor Satélite
print("\n📋 BÚSQUEDA DE TAREAS DEL MONITOR SATÉLITE")
print("-" * 70)

cursor.execute("""
    SELECT task_id, payload_json, created_at 
    FROM tasks 
    WHERE payload_json LIKE '%Monitor Satélite%' 
       OR payload_json LIKE '%satellite_monitor%'
       OR payload_json LIKE '%DeepSeek-R1%'
    ORDER BY created_at DESC
    LIMIT 20
""")

satellite_tasks = cursor.fetchall()
if satellite_tasks:
    print(f"✅ Encontradas {len(satellite_tasks)} tareas del Monitor Satélite\n")
    
    for task_id, payload_json, created_at in satellite_tasks:
        print(f"  📌 Task ID: {task_id}")
        print(f"     Creada: {created_at}")
        if payload_json and payload_json != "null":
            try:
                details_dict = json.loads(payload_json)
                if "title" in details_dict:
                    print(f"     Título: {details_dict['title']}")
                if "objective" in details_dict:
                    print(f"     Objetivo: {details_dict['objective']}")
            except:
                pass
        print()
else:
    print("⚠️ No se encontraron tareas vinculadas al Monitor Satélite")

# 2. Verificar outcomes de tareas
print("\n📊 VERIFICACIÓN DE OUTCOMES (RESULTADOS)")
print("-" * 70)

cursor.execute("""
    SELECT task_outcomes.task_id, task_outcomes.outcome, task_outcomes.created_at, task_outcomes.error_text
    FROM task_outcomes
    WHERE task_outcomes.task_id IN (
        SELECT task_id FROM tasks 
        WHERE payload_json LIKE '%Monitor Satélite%' 
           OR payload_json LIKE '%satellite_monitor%'
           OR payload_json LIKE '%DeepSeek-R1%'
    )
    ORDER BY task_outcomes.created_at DESC
    LIMIT 20
""")

outcomes = cursor.fetchall()
if outcomes:
    print(f"✅ Encontrados {len(outcomes)} resultados finales\n")
    for task_id, outcome, created_at, error_text in outcomes:
        status_icon = "✅" if outcome == "success" else "❌" if outcome == "failed" else "⚠️"
        print(f"  {status_icon} {task_id}: {outcome} ({created_at})")
        if error_text:
            print(f"     Error: {error_text}")
else:
    print("⚠️ No se encontraron outcomes")

# 3. Buscar tareas sin outcome (HUÉRFANAS)
print("\n🚨 BÚSQUEDA DE TAREAS HUÉRFANAS (SIN OUTCOME)")
print("-" * 70)

cursor.execute("""
    SELECT t.task_id, t.created_at 
    FROM tasks t
    WHERE (t.payload_json LIKE '%Monitor Satélite%' 
        OR t.payload_json LIKE '%satellite_monitor%'
        OR t.payload_json LIKE '%DeepSeek-R1%')
    AND t.task_id NOT IN (SELECT task_id FROM task_outcomes)
    ORDER BY t.created_at DESC
""")

orphan_tasks = cursor.fetchall()
if orphan_tasks:
    print(f"🚨 ALERTA: {len(orphan_tasks)} tarea(s) HUÉRFANA(S) DETECTADA(S)\n")
    for task_id, created_at in orphan_tasks:
        try:
            elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except:
            elapsed = "desconocido"
        print(f"  ⚠️ {task_id}")
        print(f"     Creada: {created_at}")
        print(f"     Tiempo sin actualización: {elapsed}")
        print()
else:
    print("✅ NINGUNA TAREA HUÉRFANA DETECTADA")

# 4. Revisar eventos de Telegram del Monitor
print("\n📡 EVENTOS TELEGRAM VINCULADOS AL MONITOR")
print("-" * 70)

cursor.execute("""
    SELECT event_id, status, created_at, payload_json 
    FROM telegram_events 
    WHERE payload_json LIKE '%Monitor%'
       OR payload_json LIKE '%satellite%'
       OR payload_json LIKE '%DeepSeek%'
    ORDER BY created_at DESC
    LIMIT 10
""")

tg_events = cursor.fetchall()
if tg_events:
    print(f"✅ Encontrados {len(tg_events)} eventos de Telegram\n")
    for event_id, status, created_at, payload_json in tg_events:
        status_icon = "✅" if status == "delivered" else "⚠️"
        print(f"  {status_icon} {event_id}: {status} ({created_at})")
else:
    print("ℹ️ No se encontraron eventos específicos del Monitor en Telegram")

# 5. Resumen de integridad
print("\n" + "=" * 70)
print("📋 RESUMEN DE INTEGRIDAD")
print("=" * 70)

cursor.execute("""
    SELECT COUNT(*) FROM tasks 
    WHERE payload_json LIKE '%Monitor Satélite%' 
       OR payload_json LIKE '%satellite_monitor%'
       OR payload_json LIKE '%DeepSeek-R1%'
""")
total_tasks = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM task_outcomes 
    WHERE task_id IN (
        SELECT task_id FROM tasks 
        WHERE payload_json LIKE '%Monitor Satélite%' 
           OR payload_json LIKE '%satellite_monitor%'
           OR payload_json LIKE '%DeepSeek-R1%'
    )
""")
completed_tasks = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM task_outcomes 
    WHERE task_id IN (
        SELECT task_id FROM tasks 
        WHERE payload_json LIKE '%Monitor Satélite%' 
           OR payload_json LIKE '%satellite_monitor%'
           OR payload_json LIKE '%DeepSeek-R1%'
    )
    AND (outcome = 'success' OR outcome LIKE '%success%')
""")
success_tasks = cursor.fetchone()[0]

print(f"\n📊 Estadísticas:")
print(f"  • Total de tareas: {total_tasks}")
print(f"  • Con outcome registrado: {completed_tasks}")
print(f"  • Huérfanas (sin outcome): {total_tasks - completed_tasks}")
print(f"  • Exitosas: {success_tasks}")

if total_tasks - completed_tasks == 0:
    print(f"\n✅ ESTADO: ÍNTEGRO - Todas las tareas tienen conclusión registrada")
else:
    print(f"\n🚨 ESTADO: CRÍTICO - Hay tareas sin conclusión")

conn.close()
