import sys
from pathlib import Path
import json

# Setup paths
SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from common import ROOT
from audit.guardrails import safe_write
from utils.relevance_filter import RelevanceFilter
from toltecayotl.capsule_generator import CapsuleGenerator

SESIONES_DIR = ROOT / "00_sistema_tesis" / "sesiones"
BITACORA_DIR = ROOT / "00_sistema_tesis" / "bitacora"

def close_active_session():
    active_session_file = SESIONES_DIR / "ACTIVE_SESSION.txt"
    if not active_session_file.exists():
        print("[ERROR] No hay sesión activa registrada en ACTIVE_SESSION.txt")
        return 1
    
    session_dirname = active_session_file.read_text().strip()
    session_path = SESIONES_DIR / session_dirname
    context_path = session_path / "session_context.json"
    
    if not session_path.exists() or not context_path.exists():
        print(f"[ERROR] No se encuentra la carpeta o contexto de la sesión: {session_dirname}")
        return 1
    
    with open(context_path, "r", encoding="utf-8") as f:
        context = json.load(f)
    
    session_id = context.get("session_id", "UNKNOWN")
    archetype = context.get("archetype", "General")
    
    # 1. Buscar bitácora asociada (heurística por fecha y ID o nombre)
    # Por ahora buscamos la más reciente que mencione el ID
    bitacoras = list(BITACORA_DIR.glob("*.md"))
    target_bitacora = None
    for b in sorted(bitacoras, key=lambda x: x.stat().st_mtime, reverse=True):
        content = b.read_text(encoding="utf-8")
        if session_id in content:
            target_bitacora = b
            break
            
    if not target_bitacora:
        print(f"[WARN] No se encontró bitácora vinculada al ID: {session_id}")
        raw_log = ""
    else:
        raw_log = target_bitacora.read_text(encoding="utf-8")
        print(f"[OK] Procesando bitácora: {target_bitacora.name}")

    # 2. Procesar relevancia y anonimización
    rf = RelevanceFilter()
    processed_data = rf.process_session_log(raw_log)
    
    # 3. Generar Cápsula
    cg = CapsuleGenerator(ROOT)
    capsule_path = cg.generate_capsule(
        session_id=session_id,
        context=context,
        nexuses=processed_data["academic_nexuses"],
        bitacora_path=str(target_bitacora.relative_to(ROOT)) if target_bitacora else "N/A"
    )
    
    # 4. Limpiar sesión activa
    active_session_file.unlink()
    
    print(f"\n[CIERRE EXITOSO]")
    print(f"Sesión: {session_dirname}")
    print(f"Arquetipo: {archetype}")
    print(f"Cápsula: {capsule_path.relative_to(ROOT)}")
    print(f"Nexos Epistémicos encontrados: {len(processed_data['academic_nexuses'])}")
    
    return 0

if __name__ == "__main__":
    sys.exit(close_active_session())
