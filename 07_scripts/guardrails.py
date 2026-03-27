import os
import shutil
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "00_sistema_tesis" / "config" / "integrity_manifest.json"
PROTECTED_EXACT_PATHS = {
    "00_sistema_tesis/canon/events.jsonl",
    "00_sistema_tesis/config/agent_identity.json",
    "00_sistema_tesis/config/ia_gobernanza.yaml",
    "00_sistema_tesis/config/integrity_manifest.json",
}
UNPROTECTED_EXACT_PATHS = {
    "00_sistema_tesis/bitacora/log_conversaciones_ia.md",
    "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
    "00_sistema_tesis/config/sign_offs.json",
    "00_sistema_tesis/ia_journal.json",
    "00_sistema_tesis/canon/state.json",
}
PROTECTED_DIR_PREFIXES = (
    "00_sistema_tesis/canon/",
    "00_sistema_tesis/decisiones/",
)
UNPROTECTED_DIR_PREFIXES = (
    "00_sistema_tesis/bitacora/audit_history/",
    "00_sistema_tesis/bitacora/",
    "config/backups/",
)

def get_file_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def relative_to_root(file_path):
    path = Path(file_path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return None

def has_protected_marker(file_path):
    path = Path(file_path)
    if not path.exists():
        return False
    if path.suffix.lower() not in {".md", ".markdown", ".yaml", ".yml", ".html"}:
        return False

    try:
        content = path.read_text(encoding='utf-8')
        if "<!-- SISTEMA_TESIS:PROTEGIDO -->" in content:
            return True
    except Exception:
        return False
    return False

def is_protected_path(file_path):
    rel_path = relative_to_root(file_path)
    if rel_path:
        if any(rel_path.startswith(prefix) for prefix in UNPROTECTED_DIR_PREFIXES):
            return False
        if rel_path in UNPROTECTED_EXACT_PATHS:
            return False
        if rel_path in PROTECTED_EXACT_PATHS:
            return True
        if any(rel_path.startswith(prefix) for prefix in PROTECTED_DIR_PREFIXES):
            return True
    return has_protected_marker(file_path)

def is_protected(file_path):
    return is_protected_path(file_path)

def backup_file(file_path):
    path = Path(file_path).resolve()
    if not path.exists():
        return
    
    backup_root = ROOT / "config" / "backups"
    if not backup_root.exists():
        os.makedirs(backup_root, exist_ok=True)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Preserve directory structure in backup
    rel_path = path.relative_to(ROOT)
    backup_path = backup_root / f"{rel_path.as_posix().replace('/', '_')}.{timestamp}.bak"
    
    shutil.copy2(path, backup_path)
    print(f"[GUARDRAIL] Backup creado: {backup_path}")

def update_manifest():
    manifest = {}
    # Scan for protected files
    for p in ROOT.rglob("*"):
        if p.is_file() and not any(part.startswith(".") for part in p.parts):
            if p.resolve() == MANIFEST_PATH.resolve():
                continue
            if is_protected_path(p):
                manifest[str(p.relative_to(ROOT))] = get_file_hash(p)
    
    if not MANIFEST_PATH.parent.exists():
        os.makedirs(MANIFEST_PATH.parent, exist_ok=True)
        
    with open(MANIFEST_PATH, "w", encoding='utf-8') as f:
        json.dump(manifest, f, indent=4)
    print(f"[GUARDRAIL] Integridad actualizada en manifest.")

def verify_integrity():
    if not MANIFEST_PATH.exists():
        print("[WARNING] No hay manifest de integridad. Generando uno nuevo...")
        update_manifest()
        return True
    
    with open(MANIFEST_PATH, "r", encoding='utf-8') as f:
        manifest = json.load(f)
    
    violations = []
    for rel_path, expected_hash in manifest.items():
        if rel_path == str(MANIFEST_PATH.relative_to(ROOT)):
            continue
        abs_path = ROOT / rel_path
        if not abs_path.exists():
            violations.append(f"ARCHIVO ELIMINADO: {rel_path}")
            continue
        
        current_hash = get_file_hash(abs_path)
        if current_hash != expected_hash:
            violations.append(f"INTEGRIDAD VIOLADA: {rel_path}")
            
    if violations:
        for v in violations:
            print(f"[CRITICAL] {v}")
        return False
    
    print("[OK] Integridad del sistema verificada.")
    return True

def safe_write(file_path, content, force=False):
    protected = is_protected_path(file_path)
    if protected and not force:
        print(f"[ERROR] ARCHIVO PROTEGIDO: {file_path}. Use --force para omitir.")
        return False

    if protected:
        backup_file(file_path)
    Path(file_path).write_text(content, encoding='utf-8')
    # Update manifest after successful write if it was a protected file
    if protected:
        update_manifest()
    return True

def safe_dump_json(file_path, payload, force=False):
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    return safe_write(file_path, content, force=force)

if __name__ == "__main__":
    import sys
    if "--verify" in sys.argv:
        if not verify_integrity():
            sys.exit(1)
    elif "--update" in sys.argv:
        update_manifest()
