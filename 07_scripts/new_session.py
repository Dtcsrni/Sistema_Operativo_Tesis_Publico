import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

from common import apply_agent_identity_placeholders
from guardrails import safe_write

ROOT = Path(__file__).resolve().parents[1]
BITACORA_DIR = ROOT / "00_sistema_tesis" / "bitacora"
TEMPLATE_PATH = ROOT / "00_sistema_tesis" / "plantillas" / "bitacora_template.md"

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

def create_new_session(session_id=None):
    latest = get_latest_bitacora()
    if latest:
        prev_hash = calc_hash(latest)
        prev_name = latest.name
    else:
        prev_hash = "INICIO"
        prev_name = "N/A"

    today = datetime.now().strftime("%Y-%m-%d")
    new_filename = f"{today}_bitacora_sesion.md"
    new_path = BITACORA_DIR / new_filename
    
    # Si ya existe, añadir un sufijo
    counter = 1
    while new_path.exists():
        new_path = BITACORA_DIR / f"{today}_bitacora_sesion_{counter}.md"
        counter += 1

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        content = apply_agent_identity_placeholders(f.read())

    # Reemplazos básicos
    content = content.replace("YYYY-MM-DD", today)
    content = content.replace("[ID-SESION-GUID]", session_id or "PENDIENTE")
    content = content.replace("[hash_bitacora_previa_o_INICIO]", prev_hash)
    
    if not safe_write(new_path, content, force=True):
        sys.exit(1)

    print(f"[OK] Nueva bitácora creada: {new_path.relative_to(ROOT)}")
    print(f"     Vinculada a: {prev_name} (Hash: {prev_hash[:10]}...)")

if __name__ == "__main__":
    sid = sys.argv[1] if len(sys.argv) > 1 else None
    create_new_session(sid)
