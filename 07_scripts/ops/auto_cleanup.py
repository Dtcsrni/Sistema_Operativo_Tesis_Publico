from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import argparse
import json
import shutil
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime

from common import ROOT, now_stamp

CRITICAL_BACKUPS = {
    "AGENTS.md",
    "README_INICIO.md",
    "MEMORY.md",
    "log_sesiones_trabajo_registradas.md",
    "matriz_trazabilidad.md",
}

EXPLICIT_CLEANUP_TARGETS = {
    "build_log.txt",
    "final_audit_v3.txt",
    "hash_result.txt",
    "real_hashes.txt",
    "temp_payload.json",
    "tmp_ledger_entry.txt",
}

ARCHIVE_PREFIX = "Bóvedas_Obsidian_"

@dataclass(frozen=True)
class CleanupItem:
    path: str
    action: str
    reason: str
    source: str | None = None

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Limpia temporales, logs obsoletos y backups excedentes.")
    parser.add_argument("--root", default=str(ROOT), help="Raíz del repositorio")
    parser.add_argument("--keep-backups", type=int, default=3, help="Backups recientes a conservar por archivo crítico")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios reales")
    parser.add_argument("--json", action="store_true", help="Imprime salida JSON")
    return parser.parse_args()

def find_backup_groups(root: Path) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in root.rglob("*.bak.*"):
        if not path.is_file():
            continue
        stem = path.name.split(".bak.", 1)[0]
        groups[stem].append(path)
    for paths in groups.values():
        paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return groups

def plan_cleanup(root: Path, keep_backups: int) -> list[CleanupItem]:
    items: list[CleanupItem] = []

    for name in sorted(EXPLICIT_CLEANUP_TARGETS):
        path = root / name
        if path.exists():
            items.append(CleanupItem(path=str(path), action="delete", reason="archivo temporal u obsoleto"))

    for stem, paths in find_backup_groups(root).items():
        if stem in CRITICAL_BACKUPS:
            for path in paths[keep_backups:]:
                items.append(
                    CleanupItem(
                        path=str(path),
                        action="delete",
                        reason=f"backup excedente, conservar solo {keep_backups}",
                        source=stem,
                    )
                )

    obsidian_dir = root / "Bóvedas_Obsidian"
    if obsidian_dir.exists():
        archive_name = f"{ARCHIVE_PREFIX}{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
        items.append(
            CleanupItem(
                path=str(obsidian_dir),
                action="archive",
                reason="superficie histórica fuera del flujo principal",
                source=archive_name,
            )
        )

    return items

def apply_item(root: Path, item: CleanupItem) -> None:
    path = Path(item.path)
    if item.action == "delete":
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
        return

    if item.action == "archive" and path.is_dir():
        archive_dir = root / "00_sistema_tesis" / "archivo" / (item.source or ARCHIVE_PREFIX.rstrip("_"))
        archive_dir.parent.mkdir(parents=True, exist_ok=True)
        if archive_dir.exists():
            shutil.rmtree(archive_dir)
        shutil.move(str(path), str(archive_dir))

def print_report(items: list[CleanupItem], apply_mode: bool) -> None:
    mode = "APPLY" if apply_mode else "DRY-RUN"
    print(f"[AUTO-CLEANUP] Modo: {mode}")
    print(f"[AUTO-CLEANUP] Hallazgos: {len(items)}")
    for item in items:
        print(f"- {item.action}: {item.path} | {item.reason}")

def main() -> int:
    args = parse_args()
    root = Path(args.root)
    items = plan_cleanup(root, args.keep_backups)

    if args.apply:
        for item in items:
            apply_item(root, item)

    print_report(items, args.apply)

    if args.json:
        print(json.dumps({"generated_at": now_stamp(), "items": [asdict(item) for item in items]}, ensure_ascii=False, indent=2))

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
