#!/usr/bin/env python3
"""Análisis exhaustivo de mensajes del bot Telegram: clasificación y patrones."""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

DB_PATH = Path("runtime/openclaw/state/openclaw.db")
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("📊 ANÁLISIS INTEGRAL: MENSAJES TELEGRAM DEL BOT")
print("=" * 80)

# Obtener todos los eventos de Telegram
cursor.execute("""
    SELECT event_id, command, created_at, payload_json, status 
    FROM telegram_events 
    ORDER BY created_at ASC
""")

events = cursor.fetchall()

print(f"\n📋 Total de eventos registrados: {len(events)}\n")

# Analizar cada evento
conversations = defaultdict(list)
command_stats = Counter()
domain_stats = Counter()
complexity_stats = Counter()

for event_id, command, created_at, payload_json, status in events:
    try:
        payload = json.loads(payload_json)
        
        # Extraer información
        chat_id = payload.get("chat_id", "unknown")
        text = payload.get("text", "")
        response = payload.get("response", "")
        
        # Agrupar por chat
        conversations[chat_id].append({
            "event_id": event_id,
            "command": command,
            "text": text,
            "response": response,
            "status": status,
            "timestamp": created_at
        })
        
        # Estadísticas
        command_stats[command] += 1
        
    except Exception as e:
        print(f"  ⚠️ Error parsing {event_id}: {e}")

print("="*80)
print("1️⃣ ESTADÍSTICAS DE COMANDOS")
print("="*80)
for cmd, count in command_stats.most_common():
    print(f"  • {cmd}: {count} evento(s)")

print("\n" + "="*80)
print("2️⃣ CONVERSACIONES POR CHAT_ID")
print("="*80)

for chat_id, convs in sorted(conversations.items()):
    print(f"\n  📱 Chat: {chat_id}")
    print(f"     Total de mensajes: {len(convs)}")
    
    for i, msg in enumerate(convs, 1):
        user_text = (msg["text"][:60] + "...") if len(msg["text"]) > 60 else msg["text"]
        status_icon = "✅" if msg["status"] == "delivered" else "⚠️"
        
        print(f"\n     [{i}] {status_icon} {msg['command'].upper()}")
        print(f"         Tiempo: {msg['timestamp']}")
        print(f"         Usuario: {user_text}")
        
        response_preview = (msg["response"][:70] + "...") if len(msg["response"]) > 70 else msg["response"]
        print(f"         Respuesta: {response_preview}")

print("\n" + "="*80)
print("3️⃣ FLUJOS DE TRABAJO DETECTADOS")
print("="*80)

# Detectar flujos
flujos = {
    "chat_general": [],
    "investigacion_tecnica": [],
    "operaciones": [],
    "sistema": [],
}

for chat_id, convs in conversations.items():
    for msg in convs:
        text_lower = msg["text"].lower()
        
        # Clasificar por contenido
        if any(kw in text_lower for kw in ["chiste", "hola", "qué tal"]):
            flujos["chat_general"].append((chat_id, msg))
        elif any(kw in text_lower for kw in ["caveman", "debug", "bug", "error", "fix"]):
            flujos["investigacion_tecnica"].append((chat_id, msg))
        elif any(kw in text_lower for kw in ["modelo", "status", "modelos"]):
            flujos["sistema"].append((chat_id, msg))
        else:
            flujos["operaciones"].append((chat_id, msg))

for flujo, msgs in flujos.items():
    if msgs:
        print(f"\n  🔷 {flujo.upper()}: {len(msgs)} mensaje(s)")
        for chat_id, msg in msgs[:3]:  # Mostrar primeros 3
            preview = (msg["text"][:50] + "...") if len(msg["text"]) > 50 else msg["text"]
            print(f"     • [{chat_id}] {preview}")

print("\n" + "="*80)
print("4️⃣ PATRONES DE RESPUESTA")
print("="*80)

# Analizar patrones de respuesta
success_responses = 0
error_responses = 0
timeout_responses = 0

for chat_id, convs in conversations.items():
    for msg in convs:
        response = msg["response"].lower()
        
        if "saturado" in response or "sla" in response:
            error_responses += 1
        elif "éxito" in response or "enviado" in response:
            success_responses += 1
        elif "timeout" in response or "esperando" in response:
            timeout_responses += 1

total_responses = success_responses + error_responses + timeout_responses

print(f"\n  ✅ Respuestas exitosas: {success_responses} ({100*success_responses/total_responses if total_responses else 0:.1f}%)")
print(f"  ❌ Errores/Saturación: {error_responses} ({100*error_responses/total_responses if total_responses else 0:.1f}%)")
print(f"  ⏱️ Timeouts: {timeout_responses} ({100*timeout_responses/total_responses if total_responses else 0:.1f}%)")

conn.close()
print("\n✅ Análisis completado.")
