"""
Script de prueba para Mission Control
- Crea varias misiones de prueba en `04_implementacion/control_mission/mission-control.db`
- Genera artefactos en `07_scripts/test_mission_control_artifacts/`
- Marca misiones como 'done' y registra `status_reason` con ruta al artefacto
- Si están configuradas las variables de entorno `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`, envía una notificación con el informe.

USO:
  python 07_scripts/test_mission_control_runner.py

Advertencia: el script crea un backup automático en `04_implementacion/control_mission/db-backups/`.

"""

import os
import sqlite3
import uuid
import json
from datetime import datetime
from pathlib import Path
import platform

try:
    import psutil
except Exception:
    psutil = None

try:
    import requests
except Exception:
    requests = None

DB_PATH = os.environ.get('DATABASE_PATH') or '04_implementacion/control_mission/mission-control.db'
DB_PATH = Path(DB_PATH)
BACKUP_DIR = DB_PATH.parent / 'db-backups'
ARTIFACTS_DIR = Path('07_scripts/test_mission_control_artifacts')
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

NOW = lambda: datetime.utcnow().isoformat(timespec='seconds') + 'Z'


def create_backup(conn):
    # VACUUM INTO requires SQLite >= 3.27.0; attempt and ignore failure.
    ts = datetime.utcnow().isoformat().replace(':', '-').split('.')[0]
    backup_path = BACKUP_DIR / f"{DB_PATH.name}.backup.{ts}"
    try:
        conn.execute(f"VACUUM INTO '{str(backup_path).replace("'","''")}'")
        print(f"Backup creado: {backup_path}")
    except Exception as e:
        print("No fue posible ejecutar VACUUM INTO (continuando):", e)


def insert_task(conn, title, description=None):
    tid = str(uuid.uuid4())
    created = NOW()
    # Minimal insert — la tabla tasks puede variar según migraciones, intentamos columnas comunes
    conn.execute(
        "INSERT INTO tasks (id, title, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (tid, title, description or '', 'inbox', created, created)
    )
    conn.commit()
    return tid


def update_task_done(conn, tid, artifact_path=None, reason=None):
    now = NOW()
    status_reason = reason or (f"Artifact: {artifact_path}" if artifact_path else None)
    conn.execute(
        "UPDATE tasks SET status = ?, status_reason = ?, updated_at = ? WHERE id = ?",
        ('done', status_reason, now, tid)
    )
    conn.commit()


def gather_system_info():
    info = {
        'platform': platform.platform(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
    }
    if psutil:
        try:
            info.update({
                'cpu_count': psutil.cpu_count(logical=True),
                'memory_total': psutil.virtual_memory().total,
                'swap_total': psutil.swap_memory().total,
            })
        except Exception as e:
            info['psutil_error'] = str(e)
    return info


def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print('Credenciales de Telegram no configuradas; se omite notificación')
        return False
    if not requests:
        print('Paquete requests no disponible; no se puede enviar Telegram')
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'Markdown'
    }
    try:
        r = requests.post(url, data=payload, timeout=15)
        if r.status_code == 200:
            return True
        else:
            print('Telegram API returned', r.status_code, r.text)
            return False
    except Exception as e:
        print('Error enviando Telegram:', e)
        return False


def main():
    if not DB_PATH.exists():
        print('No se encontró mission-control.db en', DB_PATH)
        return

    conn = sqlite3.connect(str(DB_PATH))
    try:
        create_backup(conn)
    except Exception:
        pass

    created_tasks = []

    # 1) Tarea: demo de herramientas (simulada)
    tid_tools = insert_task(conn, 'Test: herramientas (simulado)')
    artifact_tools = ARTIFACTS_DIR / f"artifact_tools_{tid_tools}.txt"
    artifact_tools.write_text('Simulación de ejecución de herramientas:\n- echo Hello\n- date\n')
    update_task_done(conn, tid_tools, artifact_tools, reason='Herramientas simuladas ejecutadas')
    created_tasks.append((tid_tools, 'herramientas', str(artifact_tools)))

    # 2) Tarea: demo búsqueda web (simulada/limitada)
    tid_search = insert_task(conn, 'Test: búsqueda web (demo)')
    artifact_search = ARTIFACTS_DIR / f"artifact_search_{tid_search}.json"
    search_result = {'note': 'Simulación: no se hizo scraping real', 'url_sample': 'https://example.com'}
    # Try to fetch example.com as a connectivity probe
    try:
        if requests:
            r = requests.get('https://example.com', timeout=10)
            search_result['example_com_status'] = r.status_code
            search_result['example_com_snippet'] = r.text[:200]
        else:
            search_result['requests'] = 'not available'
    except Exception as e:
        search_result['error'] = str(e)
    artifact_search.write_text(json.dumps(search_result, indent=2, ensure_ascii=False))
    update_task_done(conn, tid_search, artifact_search, reason='Búsqueda demo completada')
    created_tasks.append((tid_search, 'busqueda_web', str(artifact_search)))

    # 3) Tarea: probe PC + Edge
    tid_probe = insert_task(conn, 'Test: probe sistema PC/Edge')
    artifact_probe = ARTIFACTS_DIR / f"artifact_probe_{tid_probe}.json"
    sysinfo = gather_system_info()
    # Edge probe: attempt to reach configured EDGE host if provided
    edge_host = os.environ.get('EDGE_HOST')
    if edge_host and requests:
        try:
            r = requests.get(f'http://{edge_host}:11434/health', timeout=5)
            sysinfo['edge_probe'] = {'host': edge_host, 'status': r.status_code}
        except Exception as e:
            sysinfo['edge_probe'] = {'host': edge_host, 'error': str(e)}
    artifact_probe.write_text(json.dumps(sysinfo, indent=2, ensure_ascii=False))
    update_task_done(conn, tid_probe, artifact_probe, reason='Probe de sistemas completado')
    created_tasks.append((tid_probe, 'probe_sistemas', str(artifact_probe)))

    # 4) Tarea: notificación Telegram
    tid_tg = insert_task(conn, 'Test: notificación Telegram (si configurado)')
    artifact_tg = ARTIFACTS_DIR / f"artifact_tg_{tid_tg}.txt"
    report_lines = [f"Informe de prueba - {NOW()}", 'Tareas creadas:']
    for t in created_tasks:
        report_lines.append(f"- id={t[0]} tipo={t[1]} artifact={t[2]}")
    report_text = '\n'.join(report_lines)
    artifact_tg.write_text(report_text)
    sent = send_telegram_message(report_text)
    update_task_done(conn, tid_tg, artifact_tg, reason=('Telegram enviado' if sent else 'Telegram no enviado/omitido'))
    created_tasks.append((tid_tg, 'telegram_notify', str(artifact_tg)))

    print('\nResumen:')
    for t in created_tasks:
        print(f"- {t[0]} | {t[1]} -> {t[2]}")

    conn.close()


if __name__ == '__main__':
    main()
