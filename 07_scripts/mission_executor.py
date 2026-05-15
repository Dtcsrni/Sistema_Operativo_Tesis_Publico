# !/usr/bin/env python3
# """
# mission_executor.py - Ejecuta misiones asignadas tomando agentes del Mission Control.
# Pollea tareas con status='assigned', dispara el modelo del agente y actualiza el estado.
# """

from __future__ import annotations
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

# Calcular repo_root desde ubicación del script
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent
sys.path.insert(0, str(repo_root))

MC_DB = repo_root / "04_implementacion" / "control_mission" / "mission-control.db"
print(f"[INIT] Script dir: {script_dir}")
print(f"[INIT] Repo root: {repo_root}")
print(f"[INIT] MC_DB: {MC_DB}")
POLL_INTERVAL = 5
ALLOWED_TASK_STATUSES = {
    "pending_dispatch",
    "planning",
    "inbox",
    "assigned",
    "in_progress",
    "convoy_active",
    "testing",
    "review",
    "verification",
    "done",
}


def get_mission_control_url() -> str:
    return (os.environ.get("MISSION_CONTROL_URL") or f"http://localhost:{os.environ.get('PORT', '4000')}").rstrip("/")

def get_gateway_url() -> str:
    return (os.environ.get("GATEWAY_URL") or "http://localhost:18789").rstrip("/")

def get_mc_db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(MC_DB), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError:
        pass
    return conn

def create_task_activity(task_id: str, agent_id: str, activity_type: str, model: str) -> None:
    """Crear un registro de actividad de tarea con los datos del modelo ejecutado."""
    conn = get_mc_db_conn()
    try:
        cursor = conn.cursor()
        activity_id = f"activity-{task_id}-{datetime.now(timezone.utc).isoformat()}"
        metadata = json.dumps({"model": model, "model_state": "executing"})
        
        cursor.execute(
            """
            INSERT INTO task_activities (id, task_id, agent_id, activity_type, message, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                activity_id,
                task_id,
                agent_id,
                activity_type,
                f"Model execution: {model}",
                metadata,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    except Exception as e:
        print(f"  ⚠️ Error creating task activity: {e}")
    finally:
        conn.close()

def get_assigned_tasks(limit: int = 5) -> list[sqlite3.Row]:
    conn = get_mc_db_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                t.id,
                t.title,
                t.description,
                t.assigned_agent_id,
                a.name AS agent_name,
                a.model AS agent_model
            FROM tasks t
            LEFT JOIN agents a ON t.assigned_agent_id = a.id
            WHERE t.status = 'assigned'
            ORDER BY t.created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        return list(cursor.fetchall())
    finally:
        conn.close()

def update_task_state(
    task_id: str,
    *,
    status: str | None = None,
    status_reason: str | None = None,
    planning_dispatch_error: str | None = None,
    agent_id: str | None = None,
    model: str | None = None,
) -> None:
    if status is not None and status not in ALLOWED_TASK_STATUSES:
        raise ValueError(f"Invalid task status: {status}")

    columns: list[str] = []
    params: list[Any] = []

    if status is not None:
        columns.append("status = ?")
        params.append(status)
    if status_reason is not None:
        columns.append("status_reason = ?")
        params.append(status_reason)
    if planning_dispatch_error is not None:
        columns.append("planning_dispatch_error = ?")
        params.append(planning_dispatch_error)
    columns.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).isoformat())
    params.append(task_id)
    sql = f"UPDATE tasks SET {', '.join(columns)} WHERE id = ?"

    for attempt in range(5):
        conn = get_mc_db_conn()
        try:
            conn.execute(sql, params)
            conn.commit()
            # Log activity if model execution completed
            if status == "done" and agent_id and model:
                create_task_activity(task_id, agent_id, "model_execution_completed", model)
            return
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == 4:
                raise
            time.sleep(0.5 * (attempt + 1))
        finally:
            conn.close()

def execute_task_via_gateway(task_id: str, agent_name: str, agent_model: str, title: str, description: str) -> bool:
    print(f"\n[EXEC] Task {task_id[:8]}...")
    print(f"  Agent: {agent_name} | Model: {agent_model}")
    print(f"  Title: {title}")

    mission_control_url = get_mission_control_url()
    dispatch_url = f"{mission_control_url}/api/tasks/{task_id}/dispatch"
    payload = json.dumps({"board_override": True}).encode("utf-8")
    req = request.Request(
        dispatch_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {"raw": body}

            if resp.status >= 200 and resp.status < 300:
                print("  ✓ Despachada por Mission Control HTTP")
                if isinstance(data, dict) and data.get("openclaw_response", {}).get("assistant_text"):
                    assistant_text = str(data["openclaw_response"]["assistant_text"])
                    print(f"    {assistant_text[:120]}")
                return True

            print(f"  ✗ HTTP {resp.status}")
            return False
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        print(f"  ✗ HTTP {exc.code}: {body[:240]}")
        return False
    except Exception as exc:
        print(f"  ✗ Exception: {exc}")
        return False

def mission_executor_loop() -> None:
    print("[START] Mission Executor iniciado")
    print(f"  Gateway: {get_gateway_url()}")
    print(f"  Mission Control: {get_mission_control_url()}")
    print(f"  Mission Control DB: {MC_DB}")
    print(f"  Poll interval: {POLL_INTERVAL}s")
    print()

    while True:
        try:
            tasks = get_assigned_tasks()
            if not tasks:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sin tareas asignadas", end="\r")
                time.sleep(POLL_INTERVAL)
                continue

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {len(tasks)} tarea(s) encontrada(s)")

            for task in tasks:
                task_id = str(task["id"])
                agent_name = str(task["agent_name"] or "(sin agente)")
                agent_model = str(task["agent_model"] or "").strip()
                title = str(task["title"] or "")
                description = str(task["description"] or "")

                if not agent_model:
                    print(f"  ⚠️ Task {task_id[:8]}: sin modelo asignado, se estaciona en planning")
                    update_task_state(
                        task_id,
                        status="planning",
                        status_reason="Agent has no model assigned",
                        planning_dispatch_error="No agent model assigned",
                    )
                    continue

                update_task_state(task_id, status="in_progress", status_reason="Modelo ejecutándose...")
                success = execute_task_via_gateway(task_id, agent_name, agent_model, title, description)

                if success:
                    update_task_state(
                        task_id,
                        status="done",
                        status_reason="Completada por modelo",
                        planning_dispatch_error=None,
                        agent_id=str(task["assigned_agent_id"]),
                        model=agent_model,
                    )
                else:
                    update_task_state(
                        task_id,
                        status="planning",
                        status_reason="Execution failed; parked for manual recovery",
                        planning_dispatch_error="Error in model execution loop",
                    )

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n[STOP] Executor interrumpido")
            break
        except Exception as exc:
            print(f"\n[ERROR] {exc}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    if not MC_DB.exists():
        print(f"ERROR: Mission Control DB no encontrada: {MC_DB}")
        sys.exit(1)

    mission_executor_loop()
