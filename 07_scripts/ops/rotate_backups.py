from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import argparse
import json
import re
import gzip
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime

from common import ROOT, now_stamp

DEFAULT_POLICY_PATH = ROOT / "00_sistema_tesis" / "config" / "backup_rotation_policy.json"
BACKUP_DIR = ROOT / "config" / "backups"
LOG_DIR = ROOT / "config" / "logs"
BACKUP_NAME_PATTERN = re.compile(r"^(?P<stem>.+)\.(?P<stamp>\d{8}_\d{6})\.bak$")
STAMP_FORMAT = "%Y%m%d_%H%M%S"
RISK_ORDER = {"operativo": 0, "alto": 1, "critico": 2}

def setup_logging(policy: dict) -> logging.Logger:
    """Configura logging según política."""
    log_config = policy.get("backup_rotation", {}).get("logging", {})
    if not log_config.get("enabled", True):
        return logging.getLogger("backup_rotation")
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / log_config.get("output", "backup_rotation.log").split("/")[-1]
    level = getattr(logging, log_config.get("level", "INFO"))
    
    logger = logging.getLogger("backup_rotation")
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

@dataclass
class BackupEntry:
    path: Path
    source_stem: str
    created_at: datetime
    age_days: float
    size_bytes: int
    risk: str
    protected_window: bool
    expired: bool
    content_hash: str = ""
    is_compressed: bool = False

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rota backups .bak por antigüedad, riesgo y límites de volumen (Git-First).")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--apply", action="store_true", help="Aplica cambios reales (compresión + purga).")
    parser.add_argument("--compress-only", action="store_true", help="Solo comprime archivos >7 días, no purga.")
    parser.add_argument("--json", action="store_true", help="Imprime resumen JSON.")
    parser.add_argument("--verbose", action="store_true", help="Salida detallada.")
    return parser.parse_args()

def load_policy(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"No existe política de rotación: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def classify_risk(source_stem: str, policy: dict) -> str:
    patterns = policy["backup_rotation"].get("risk_patterns", {})
    for pattern in patterns.get("critico", []):
        if source_stem.startswith(pattern):
            return "critico"
    for pattern in patterns.get("alto", []):
        if source_stem.startswith(pattern):
            return "alto"
    return "operativo"

def compute_sha256(path: Path) -> str:
    """Calcula SHA-256 del contenido de un archivo."""
    sha = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha.update(chunk)
        return sha.hexdigest()[:16]  # Primeros 16 chars
    except Exception:
        return ""

def compress_backup(path: Path, policy: dict, logger: logging.Logger) -> bool:
    """Comprime un archivo .bak a .bak.gz si no está ya comprimido."""
    if path.suffix == '.gz':
        return False
    
    comp_config = policy.get("backup_rotation", {}).get("compression", {})
    if not comp_config.get("enabled", True):
        return False
    
    level = comp_config.get("compression_level", 6)
    try:
        gz_path = Path(str(path) + ".gz")
        with open(path, 'rb') as f_in:
            with gzip.open(gz_path, 'wb', compresslevel=level) as f_out:
                f_out.write(f_in.read())
        orig_size = path.stat().st_size
        comp_size = gz_path.stat().st_size
        ratio = (1 - comp_size / orig_size) * 100 if orig_size > 0 else 0
        logger.info(f"Comprimido: {path.name} ({orig_size}B -> {comp_size}B, -({ratio:.1f}%)) -> {gz_path.name}")
        path.unlink()  # Elimina original
        return True
    except Exception as e:
        logger.warning(f"Fallo compresión {path.name}: {e}")
        return False

def read_backups(policy: dict, logger: logging.Logger) -> list[BackupEntry]:
    now = datetime.now()
    if not BACKUP_DIR.exists():
        return []

    retention = policy["backup_rotation"]["retention_days"]
    min_protected_days = int(policy["backup_rotation"]["limits"]["min_protected_days"])
    entries: list[BackupEntry] = []
    
    dedup_config = policy.get("backup_rotation", {}).get("deduplication", {})
    dedup_enabled = dedup_config.get("enabled", True)

    for path in BACKUP_DIR.glob("*"):
        if path.name.endswith('.log'):
            continue  # Ignora logs
        
        is_compressed = path.suffix in ('.gz', '.bz2')
        match = BACKUP_NAME_PATTERN.match(path.name.replace('.gz', '').replace('.bz2', ''))
        
        if match:
            source_stem = match.group("stem")
            created_at = datetime.strptime(match.group("stamp"), STAMP_FORMAT)
        else:
            source_stem = path.stem
            created_at = datetime.fromtimestamp(path.stat().st_mtime)
        
        age_days = (now - created_at).total_seconds() / 86400.0
        risk = classify_risk(source_stem, policy)
        protected_window = age_days < float(min_protected_days)
        expired = age_days > float(retention[risk])
        
        content_hash = compute_sha256(path) if dedup_enabled else ""
        
        entries.append(
            BackupEntry(
                path=path,
                source_stem=source_stem,
                created_at=created_at,
                age_days=age_days,
                size_bytes=path.stat().st_size,
                risk=risk,
                protected_window=protected_window,
                expired=expired,
                content_hash=content_hash,
                is_compressed=is_compressed,
            )
        )
    return entries

def plan_rotation(entries: list[BackupEntry], policy: dict, logger: logging.Logger) -> tuple[list[BackupEntry], dict]:
    limits = policy["backup_rotation"]["limits"]
    max_files = int(limits["max_files"])
    max_size_bytes = int(float(limits["max_total_size_mb"]) * 1024 * 1024)
    
    dedup_config = policy.get("backup_rotation", {}).get("deduplication", {})
    dedup_enabled = dedup_config.get("enabled", True)
    keep_newer = dedup_config.get("keep_newer", True)

    total_files = len(entries)
    total_size = sum(item.size_bytes for item in entries)
    to_delete: list[BackupEntry] = []
    selected_paths: set[Path] = set()

    # Primera pasada: deduplicación
    if dedup_enabled:
        hash_map: dict[str, list[BackupEntry]] = {}
        for item in entries:
            if item.content_hash:
                if item.content_hash not in hash_map:
                    hash_map[item.content_hash] = []
                hash_map[item.content_hash].append(item)
        
        for content_hash, items in hash_map.items():
            if len(items) > 1:
                items.sort(key=lambda x: x.created_at, reverse=True)
                for duplicate in items[1:]:  # Keep newest, delete rest
                    if not duplicate.protected_window:
                        to_delete.append(duplicate)
                        selected_paths.add(duplicate.path)
                        logger.info(f"Deduplicado: {duplicate.path.name} (hash={content_hash[:8]}...)")

    # Segunda pasada: todo lo expirado fuera de ventana protegida.
    expired_candidates = [item for item in entries 
                         if item.expired and not item.protected_window 
                         and item.path not in selected_paths]
    expired_candidates.sort(key=lambda item: item.created_at)
    for item in expired_candidates:
        to_delete.append(item)
        selected_paths.add(item.path)

    kept = [item for item in entries if item.path not in selected_paths]
    current_files = len(kept)
    current_size = sum(item.size_bytes for item in kept)

    # Tercera pasada: si rebasa límites, purga por antigüedad iniciando en riesgo operativo.
    if current_files > max_files or current_size > max_size_bytes:
        overflow_candidates = [item for item in kept if not item.protected_window]
        overflow_candidates.sort(key=lambda item: (RISK_ORDER[item.risk], item.created_at))
        for item in overflow_candidates:
            if current_files <= max_files and current_size <= max_size_bytes:
                break
            to_delete.append(item)
            selected_paths.add(item.path)
            current_files -= 1
            current_size -= item.size_bytes

    summary = {
        "generated_at": now_stamp(),
        "total_files_before": total_files,
        "total_size_mb_before": round(total_size / (1024 * 1024), 2),
        "total_files_after": total_files - len(to_delete),
        "total_size_mb_after": round((total_size - sum(item.size_bytes for item in to_delete)) / (1024 * 1024), 2),
        "to_delete_count": len(to_delete),
        "to_delete_by_risk": {
            "critico": sum(1 for item in to_delete if item.risk == "critico"),
            "alto": sum(1 for item in to_delete if item.risk == "alto"),
            "operativo": sum(1 for item in to_delete if item.risk == "operativo"),
        },
        "deduplication": {
            "enabled": dedup_enabled,
            "duplicates_found": sum(len(items) - 1 for items in hash_map.values() if len(items) > 1) if dedup_enabled else 0,
        } if dedup_enabled else {},
        "limits": {
            "max_files": max_files,
            "max_total_size_mb": float(limits["max_total_size_mb"]),
            "min_protected_days": int(limits["min_protected_days"]),
        },
    }
    return to_delete, summary

def apply_rotation(to_delete: list[BackupEntry], policy: dict, logger: logging.Logger) -> None:
    for entry in to_delete:
        try:
            entry.path.unlink(missing_ok=True)
            logger.info(f"Eliminado: {entry.path.name}")
        except Exception as e:
            logger.error(f"Fallo al eliminar {entry.path.name}: {e}")

def print_report(to_delete: list[BackupEntry], summary: dict, apply_mode: bool, logger: logging.Logger) -> None:
    mode = "APPLY" if apply_mode else "DRY-RUN"
    msg = f"[BACKUP-ROTATE] Modo: {mode} | Archivos: {summary['total_files_before']} -> {summary['total_files_after']} | MB: {summary['total_size_mb_before']} -> {summary['total_size_mb_after']}"
    print(msg)
    logger.info(msg)
    
    msg = f"[BACKUP-ROTATE] Candidatos a borrar: {summary['to_delete_count']}"
    print(msg)
    logger.info(msg)
    
    if to_delete:
        for entry in to_delete[:20]:
            msg = f"- {entry.path.name} | riesgo={entry.risk} | edad_dias={entry.age_days:.1f} | size_kb={entry.size_bytes / 1024:.1f}"
            print(msg)
            logger.info(msg)
        if len(to_delete) > 20:
            msg = f"- ... ({len(to_delete) - 20} adicionales)"
            print(msg)
            logger.info(msg)
    else:
        msg = "[BACKUP-ROTATE] Sin cambios requeridos."
        print(msg)
        logger.info(msg)

def main() -> int:
    args = parse_args()
    policy = load_policy(Path(args.policy))
    logger = setup_logging(policy)
    
    if not policy.get("backup_rotation", {}).get("enabled", True):
        logger.info("[BACKUP-ROTATE] Política deshabilitada.")
        print("[BACKUP-ROTATE] Política deshabilitada.")
        return 0

    entries = read_backups(policy, logger)
    logger.info(f"Detectados {len(entries)} backups en {BACKUP_DIR}")
    
    # Compresión automática de archivos >7 días
    comp_config = policy.get("backup_rotation", {}).get("compression", {})
    if comp_config.get("enabled", True) and not args.compress_only:
        trigger_days = float(comp_config.get("trigger_age_days", 7))
        for entry in entries:
            if entry.age_days > trigger_days and not entry.is_compressed:
                compress_backup(entry.path, policy, logger)
    
    # Re-leer backups tras compresión
    entries = read_backups(policy, logger)
    
    to_delete, summary = plan_rotation(entries, policy, logger)
    if args.apply:
        apply_rotation(to_delete, policy, logger)
    
    print_report(to_delete, summary, args.apply, logger)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        logger.info(f"Resumen JSON: {json.dumps(summary, ensure_ascii=False)}")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
