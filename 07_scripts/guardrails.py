import os
import shutil
import datetime
import hashlib
import json
import subprocess
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
    "00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md",
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
    "06_dashboard/wiki/",
    "06_dashboard/generado/",
    "06_dashboard/publico/",
)

def get_file_hash(file_path):
    path = Path(file_path)
    text_suffixes = {
        ".md", ".markdown", ".txt", ".yaml", ".yml", ".json", ".jsonl", ".csv", ".html", ".py", ".sh", ".tex"
    }
    sha256_hash = hashlib.sha256()
    if path.suffix.lower() in text_suffixes:
        content = path.read_text(encoding="utf-8", errors="replace")
        normalized = content.replace("\r\n", "\n").replace("\r", "\n")
        sha256_hash.update(normalized.encode("utf-8"))
        return sha256_hash.hexdigest()

    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return set()
    return {line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()}


def _load_manifest_payload() -> dict[str, str] | None:
    if not MANIFEST_PATH.exists():
        return None
    try:
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {str(key).replace("\\", "/"): str(value) for key, value in payload.items()}


def _write_manifest_payload(manifest: dict[str, str]) -> None:
    if not MANIFEST_PATH.parent.exists():
        os.makedirs(MANIFEST_PATH.parent, exist_ok=True)
    ordered = {key: manifest[key] for key in sorted(manifest)}
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(ordered, f, indent=4, sort_keys=False)

def relative_to_root(file_path):
    path = Path(file_path).resolve()
    try:
        rel = path.relative_to(ROOT).as_posix()
        return rel
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
    tracked = tracked_files()
    if tracked:
        for rel_posix in sorted(tracked):
            p = ROOT / rel_posix
            if not p.is_file():
                continue
            if p.resolve() == MANIFEST_PATH.resolve():
                continue
            if any(part.startswith(".") for part in p.parts):
                continue
            if is_protected_path(p):
                manifest[rel_posix] = get_file_hash(p)
    else:
        # Fallback cuando git no esta disponible.
        for p in ROOT.rglob("*"):
            if p.is_file() and not any(part.startswith(".") for part in p.parts):
                if p.resolve() == MANIFEST_PATH.resolve():
                    continue
                rel_posix = p.relative_to(ROOT).as_posix()
                if is_protected_path(p):
                    manifest[rel_posix] = get_file_hash(p)
    
    _write_manifest_payload(manifest)
    print(f"[GUARDRAIL] Integridad actualizada en manifest.")


def update_manifest_for_path(file_path):
    rel_path = relative_to_root(file_path) or str(file_path).strip().replace("\\", "/")
    normalized_rel_path = rel_path.replace("\\", "/")
    if normalized_rel_path == str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"):
        return

    manifest = _load_manifest_payload()
    if manifest is None:
        update_manifest()
        return

    abs_path = ROOT / normalized_rel_path
    if not abs_path.exists() or not abs_path.is_file() or any(part.startswith(".") for part in abs_path.parts):
        manifest.pop(normalized_rel_path, None)
    elif is_protected_path(abs_path):
        manifest[normalized_rel_path] = get_file_hash(abs_path)
    else:
        manifest.pop(normalized_rel_path, None)

    _write_manifest_payload(manifest)
    print(f"[GUARDRAIL] Integridad incremental actualizada: {normalized_rel_path}")

def verify_integrity():
    if not MANIFEST_PATH.exists():
        print("[WARNING] No hay manifest de integridad. Generando uno nuevo...")
        update_manifest()
        return True
    
    with open(MANIFEST_PATH, "r", encoding='utf-8') as f:
        manifest = json.load(f)
    
    violations = []
    for rel_path, expected_hash in manifest.items():
        # Normalizar rutas: convertir backslashes a forward slashes para compatibilidad
        normalized_rel_path = rel_path.replace("\\", "/")
        
        if normalized_rel_path == str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"):
            continue
        
        # Intentar ambas formas (con \ y con /) por compatibilidad
        abs_path = ROOT / normalized_rel_path
        if not abs_path.exists():
            # Intentar con backslashes por si acaso (Windows)
            alt_path = ROOT / rel_path
            if alt_path.exists():
                abs_path = alt_path
            else:
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
        update_manifest_for_path(file_path)
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

