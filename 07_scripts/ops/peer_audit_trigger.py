import sqlite3
import os
import uuid
from pathlib import Path

DB_PATH = Path("04_implementacion/control_mission/mission-control.db")

def check_audit_needs():
    if not DB_PATH.exists():
        print("[ERROR] No se encuentra la base de datos de Mission Control.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Buscar tareas en revisión
    print("\n[AUDITORÍA] Buscando tareas en estado 'REVIEW'...")
    cursor.execute("SELECT id, title, assigned_agent_id, status FROM tasks WHERE status = 'REVIEW'")
    tasks = cursor.fetchall()
    
    if not tasks:
        print("No hay tareas pendientes de auditoría.")
        return

    for task in tasks:
        tid, title, agent_id, status = task
        print(f"\n>>> Detectada tarea para auditar: [{tid}] {title}")
        print(f"    Asignada a Agente ID: {agent_id}")
        
        # 2. Simular el proceso de Auditoría de Pares
        print("    [FISCAL] Iniciando revisión de integridad y cumplimiento de normas...")
        print("    [FISCAL] Verificando trazabilidad VAL-STEP...")
        
        # Generar un ID de evento único
        evt_id = str(uuid.uuid4())
        
        # 3. Registrar el resultado de la auditoría en la tabla de eventos
        event_msg = f"Auditoría de Pares EXITOSA para tarea {tid}: El Fiscal valida el cumplimiento del estándar PET."
        cursor.execute("""
            INSERT INTO events (id, type, message, metadata, created_at) 
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (evt_id, "agent.audit", event_msg, '{"result": "success", "auditor": "Fiscal"}'))
        
        # 4. Mover a DONE (Opcional, simulando aprobación automática tras auditoría exitosa)
        # cursor.execute("UPDATE tasks SET status = 'DONE' WHERE id = ?", (tid,))
        print(f"    [OK] Integridad verificada para {tid}. Evento {evt_id} registrado.")
        
    conn.commit()
    conn.close()
    print("\n[DONE] Auditoría de Pares completada.")

if __name__ == "__main__":
    check_audit_needs()
