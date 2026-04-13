import sys
from pathlib import Path
from datetime import datetime
import csv

from common import apply_agent_identity_placeholders
from guardrails import safe_write

def load_pending_tasks(backlog_path):
    tasks = []
    if not Path(backlog_path).exists():
        return tasks
    with open(backlog_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['estado'] == 'pendiente':
                tasks.append(f"- [ ] {row['task_id']}: {row['tarea']} ({row['bloque']})")
    return tasks

def main():
    root = Path(__file__).parent.parent
    template_path = root / "00_sistema_tesis" / "plantillas" / "bitacora_template.md"
    today = datetime.now().strftime("%Y-%m-%d")
    bitacora_dir = root / "00_sistema_tesis" / "bitacora"
    
    # Buscar el ID de sesión más alto para hoy o el siguiente global
    existing_logs = list(bitacora_dir.glob("*.md"))
    session_id = len(existing_logs) + 1
    
    filename = f"{today}_bitacora_S{session_id:03d}.md"
    target_path = bitacora_dir / filename
    
    if target_path.exists():
        print(f"[ERROR] El archivo {filename} ya existe.")
        sys.exit(1)
        
    if not template_path.exists():
        print(f"[ERROR] No se encontró la plantilla en {template_path}")
        sys.exit(1)
        
    content = apply_agent_identity_placeholders(template_path.read_text(encoding='utf-8'))
    
    # Pre-llenar fecha y tareas
    pending = load_pending_tasks(root / "01_planeacion" / "backlog.csv")
    tasks_str = "\n".join(pending) if pending else "- [ ] (No hay tareas pendientes en el backlog)"
    
    content = content.replace("YYYY-MM-DD", today)
    content = content.replace("(Inserción automática de tareas pendientes)", tasks_str)
    
    if not safe_write(target_path, content, force=True):
        sys.exit(1)
    print(f"[OK] Bitácora creada: {target_path}")

if __name__ == "__main__":
    main()
