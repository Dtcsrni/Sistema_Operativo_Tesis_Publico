from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from common import ROOT, now_stamp


DEFAULT_POLICY_PATH = ROOT / "00_sistema_tesis" / "config" / "backup_rotation_policy.json"
BACKUP_DIR = ROOT / "config" / "backups"
BACKUP_NAME_PATTERN = re.compile(r"^(?P<stem>.+)\.(?P<stamp>\d{8}_\d{6})\.bak$")
STAMP_FORMAT = "%Y%m%d_%H%M%S"
RISK_ORDER = {"operativo": 0, "alto": 1, "critico": 2}


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rota backups .bak por antigüedad, riesgo y límites de volumen.")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--apply", action="store_true", help="Aplica borrado real. Sin esta bandera se ejecuta dry-run.")
    parser.add_argument("--json", action="store_true", help="Imprime también resumen JSON.")
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


def read_backups(policy: dict) -> list[BackupEntry]:
    now = datetime.now()
    if not BACKUP_DIR.exists():
        return []

    retention = policy["backup_rotation"]["retention_days"]
    min_protected_days = int(policy["backup_rotation"]["limits"]["min_protected_days"])
    entries: list[BackupEntry] = []

    for path in BACKUP_DIR.glob("*.bak"):
        match = BACKUP_NAME_PATTERN.match(path.name)
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
            )
        )
    return entries


def plan_rotation(entries: list[BackupEntry], policy: dict) -> tuple[list[BackupEntry], dict]:
    limits = policy["backup_rotation"]["limits"]
    max_files = int(limits["max_files"])
    max_size_bytes = int(float(limits["max_total_size_mb"]) * 1024 * 1024)

    total_files = len(entries)
    total_size = sum(item.size_bytes for item in entries)
    to_delete: list[BackupEntry] = []
    selected_paths: set[Path] = set()

    # Primera pasada: todo lo expirado fuera de ventana protegida.
    expired_candidates = [item for item in entries if item.expired and not item.protected_window]
    expired_candidates.sort(key=lambda item: item.created_at)
    for item in expired_candidates:
        to_delete.append(item)
        selected_paths.add(item.path)

    kept = [item for item in entries if item.path not in selected_paths]
    current_files = len(kept)
    current_size = sum(item.size_bytes for item in kept)

    # Segunda pasada: si rebasa límites, purga por antigüedad iniciando en riesgo operativo.
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
        "limits": {
            "max_files": max_files,
            "max_total_size_mb": float(limits["max_total_size_mb"]),
            "min_protected_days": int(limits["min_protected_days"]),
        },
    }
    return to_delete, summary


def apply_rotation(to_delete: list[BackupEntry]) -> None:
    for entry in to_delete:
        entry.path.unlink(missing_ok=True)


def print_report(to_delete: list[BackupEntry], summary: dict, apply_mode: bool) -> None:
    mode = "APPLY" if apply_mode else "DRY-RUN"
    print(f"[BACKUP-ROTATE] Modo: {mode}")
    print(
        f"[BACKUP-ROTATE] Archivos: {summary['total_files_before']} -> {summary['total_files_after']} | "
        f"MB: {summary['total_size_mb_before']} -> {summary['total_size_mb_after']}"
    )
    print(f"[BACKUP-ROTATE] Candidatos a borrar: {summary['to_delete_count']}")
    if to_delete:
        for entry in to_delete[:20]:
            print(
                f"- {entry.path.name} | riesgo={entry.risk} | edad_dias={entry.age_days:.1f} | "
                f"size_kb={entry.size_bytes / 1024:.1f}"
            )
        if len(to_delete) > 20:
            print(f"- ... ({len(to_delete) - 20} adicionales)")
    else:
        print("[BACKUP-ROTATE] Sin cambios requeridos.")


def main() -> int:
    args = parse_args()
    policy = load_policy(Path(args.policy))
    if not policy.get("backup_rotation", {}).get("enabled", True):
        print("[BACKUP-ROTATE] Política deshabilitada.")
        return 0

    entries = read_backups(policy)
    to_delete, summary = plan_rotation(entries, policy)
    if args.apply:
        apply_rotation(to_delete)
    print_report(to_delete, summary, args.apply)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
