import sys
from pathlib import Path
import json
import uuid

# Setup paths relative to 07_scripts
SCRIPT_DIR = Path(__file__).resolve().parents[1] # 07_scripts/
sys.path.insert(0, str(SCRIPT_DIR))

import hashlib
import os
from datetime import datetime

from common import apply_agent_identity_placeholders
from audit.guardrails import safe_write

ROOT = Path(__file__).resolve().parents[2]
BITACORA_DIR = ROOT / "00_sistema_tesis" / "bitacora"
SESIONES_DIR = ROOT / "00_sistema_tesis" / "sesiones"
TEMPLATE_DIR = ROOT / "00_sistema_tesis" / "plantillas"
BITACORA_TEMPLATE_PATH = TEMPLATE_DIR / "bitacora_template.md"
BITACORA_DIALOGO_TEMPLATE_PATH = TEMPLATE_DIR / "bitacora_dialogo_template.md"
CONTEXT_TEMPLATE_PATH = TEMPLATE_DIR / "session_context_template.json"

ARCHETYPES = ["Investigación", "Operaciones", "Fiscalía", "Síntesis", "General", "Diálogo"]
ARCHETYPE_SAFE = {
    "Investigación": "Investigacion",
    "Operaciones": "Operaciones",
    "Fiscalía": "Fiscalia",
    "Síntesis": "Sintesis",
    "General": "General",
    "Diálogo": "Dialogo"
}

def get_latest_bitacora():
    bitacoras = [f for f in BITACORA_DIR.glob("*.md") if "bitacora" in f.name]
    if not bitacoras:
        return None
    return max(bitacoras, key=lambda x: x.stat().st_mtime)

def calc_hash(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def create_new_session(session_id=None, archetype="General"):
    if archetype not in ARCHETYPES:
        print(f"[WARN] Arquetipo '{archetype}' no reconocido. Usando 'General'.")
        archetype = "General"

    privacy_level = "HIGH" if archetype == "Diálogo" else "STANDARD"
    session_id = session_id or str(uuid.uuid4())
    latest = get_latest_bitacora()
    if latest:
        prev_hash = calc_hash(latest)
        prev_name = latest.name
    else:
        prev_hash = "INICIO"
        prev_name = "N/A"

    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H%M%S")
    
    # 1. Crear directorio de sesión
    arch_safe = ARCHETYPE_SAFE.get(archetype, "General")
    session_dirname = f"{today}_{arch_safe}_{session_id[:8]}"
    session_path = SESIONES_DIR / session_dirname
    os.makedirs(session_path, exist_ok=True)

    # 2. Generar session_context.json
    with open(CONTEXT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        context_content = f.read()
    
    context_content = context_content.replace("[ID-SESION-GUID]", session_id)
    context_content = context_content.replace("[ARCHETYPE]", archetype)
    context_content = context_content.replace("YYYY-MM-DDTHH:MM:SS", datetime.now().isoformat())
    context_content = context_content.replace("[PARENT-ID]", prev_name)
    context_content = context_content.replace("[PRIVACY-LEVEL]", privacy_level)

    context_file_path = session_path / "session_context.json"
    safe_write(context_file_path, context_content, force=True)

    # 3. Generar Bitácora
    # Seleccionar plantilla basada en el arquetipo
    template_path = BITACORA_DIALOGO_TEMPLATE_PATH if archetype == "Diálogo" else BITACORA_TEMPLATE_PATH
    
    new_filename = f"{today}_bitacora_sesion.md"
    if archetype == "Diálogo":
        new_filename = f"{today}_bitacora_dialogo.md"
        
    new_path = BITACORA_DIR / new_filename
    
    # Si ya existe, añadir un sufijo
    counter = 1
    while new_path.exists():
        if archetype == "Diálogo":
            new_path = BITACORA_DIR / f"{today}_bitacora_dialogo_{counter}.md"
        else:
            new_path = BITACORA_DIR / f"{today}_bitacora_sesion_{counter}.md"
        counter += 1

    with open(template_path, "r", encoding="utf-8") as f:
        content = apply_agent_identity_placeholders(f.read())

    # Reemplazos básicos
    content = content.replace("YYYY-MM-DD", today)
    content = content.replace("[ID-SESION-GUID]", session_id)
    content = content.replace("[hash_bitacora_previa_o_INICIO]", prev_hash)
    content = content.replace("[lectura | diseño | simulación | implementación | redacción | validación | administración]", archetype.lower())
    
    # Hash de la sesión (placeholder inicial)
    content = content.replace("[hash_sesion]", hashlib.sha256(session_id.encode()).hexdigest())

    # Añadir link al contexto
    relative_context_path = os.path.relpath(context_file_path, BITACORA_DIR)
    if archetype == "Diálogo":
        content = content.replace("./session_context.json", relative_context_path)
    else:
        content = content.replace("## Infraestructura de Sesión", f"## Infraestructura de Sesión\n- **Contexto de Sesión:** [{session_dirname}]({relative_context_path})")

    if not safe_write(new_path, content, force=True):
        sys.exit(1)

    # 4. Registrar como sesión activa
    with open(SESIONES_DIR / "ACTIVE_SESSION.txt", "w", encoding="utf-8") as f:
        f.write(session_dirname)

    print(f"[OK] Nueva sesión ({archetype}) creada: {session_dirname}")
    print(f"     Bitácora: {new_path.relative_to(ROOT)}")
    print(f"     Contexto: {context_file_path.relative_to(ROOT)}")

if __name__ == "__main__":
    sid = None
    arch = "General"
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--archetype" and i + 1 < len(args):
            arch = args[i+1]
            i += 2
        elif not arg.startswith("-"):
            sid = arg
            i += 1
        else:
            i += 1

    create_new_session(sid, arch)
