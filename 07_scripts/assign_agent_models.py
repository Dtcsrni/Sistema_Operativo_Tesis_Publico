#!/usr/bin/env python3
"""
assign_agent_models.py - Asigna modelos a agentes según su rol
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

db_path = Path(__file__).resolve().parents[1] / "04_implementacion" / "control_mission" / "mission-control.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Primero obtener los nombres exactos de la BD
cursor.execute("SELECT id, name FROM agents ORDER BY is_master DESC, name")
agents = cursor.fetchall()

# Mapeo de modelos basado en patrón de nombre (para evitar encoding issues)
def get_model_for_agent(name: str) -> str:
    """Determina el modelo recomendado para un agente basado en su nombre."""
    lower = name.lower()
    
    if "orquestador" in lower or "maestro" in lower:
        return "mistral-nemo:12b"  # Orquestador local pesado
    elif "bibliote" in lower or "epistém" in lower:
        return "mistral-nemo:12b"  # Knowledge base local
    elif "investiga" in lower and "académico" in lower:
        return "mistral-nemo:12b"  # Academic research local
    elif "redactor" in lower or "científico" in lower:
        return "mistral-nemo:12b"  # Writing/composition local
    elif "experimentación" in lower or "experimenta" in lower:
        return "qwen3:4b"  # Experimentation - puede ser más ligero
    elif "hardware" in lower:
        return "qwen3:4b"  # Hardware engineering
    elif "revisor" in lower or "metodológico" in lower:
        return "mistral-nemo:12b"  # Methodology review local
    elif "asesor" in lower or "tesis" in lower:
        return "mistral-nemo:12b"  # Thesis advisory local
    elif "colega" in lower or "conversación" in lower or "conversacion" in lower:
        return "qwen3:4b"  # Conversation
    else:
        return "qwen3:4b"  # Default local ligero

now = datetime.now(timezone.utc).isoformat()
updated_count = 0

print("Asignando modelos a agentes:\n")
for agent_id, name in agents:
    model = get_model_for_agent(name)
    cursor.execute(
        "UPDATE agents SET model = ?, source = 'manual_assignment', updated_at = ? WHERE id = ?",
        (model, now, agent_id)
    )
    if cursor.rowcount > 0:
        updated_count += 1
        print(f"✓ {name:40} → {model}")
    else:
        print(f"✗ {name:40} → FALLO")

conn.commit()
print(f"\nTotal actualizado: {updated_count}/{len(agents)} agentes")
conn.close()
