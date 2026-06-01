#!/usr/bin/env python3
"""Limpieza inicial agresiva de config/backups/ enfocado en Git-First.

Mantiene solo:
- Últimos 3 backups de archivos críticos
- Ningún backup de archivos operativos innecesarios
- Elimina duplicados de openclaw.env y configuración redundante
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timedelta
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import ROOT

BACKUP_DIR = ROOT / "config" / "backups"
BACKUP_NAME_PATTERN = re.compile(r"^(?P<stem>.+)\.(?P<stamp>\d{8}_\d{6})\.bak")
STAMP_FORMAT = "%Y%m%d_%H%M%S"

# Prefijos considerados "críticos" que merecen guardar los últimos 3
CRITICAL_PREFIXES = (
    "00_sistema_tesis_decisiones_",
    "00_sistema_tesis_canon_events",
    "log_sesiones_trabajo_registradas",
    "matriz_trazabilidad",
)

# Prefijos que se deben eliminar completamente (son redundantes o legacy)
JUNK_PATTERNS = (
    "start_backends_auto.py",
    "check_stack_status.py",
    "sistema_tesis.yaml",
    "docker-compose.yml",
    "runtime_openclaw_",
    "observability_command_center",
)

def parse_backup_entry(path: Path) -> tuple[str, datetime] | None:
    """Extrae prefijo y timestamp de un archivo .bak."""
    name = path.name.replace('.gz', '').replace('.bak', '')
    match = BACKUP_NAME_PATTERN.match(name + '.bak')
    if match:
        stem = match.group("stem")
        try:
            ts = datetime.strptime(match.group("stamp"), STAMP_FORMAT)
            return (stem, ts)
        except ValueError:
            pass
    # Fallback: usar mtime
    stem = path.stem
    mtime = datetime.fromtimestamp(path.stat().st_mtime)
    return (stem, mtime)

def main() -> int:
    if not BACKUP_DIR.exists():
        print(f"[CLEANUP] Directorio no existe: {BACKUP_DIR}")
        return 0

    print(f"[CLEANUP] Analizando {BACKUP_DIR}...")
    
    all_files = sorted(BACKUP_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    to_delete = []
    kept = {}

    for path in all_files:
        if path.name.endswith('.log'):
            continue

        result = parse_backup_entry(path)
        if not result:
            continue
        
        stem, ts = result
        size_kb = path.stat().st_size / 1024

        # Regla 1: Eliminar basura conocida
        if any(junk in stem for junk in JUNK_PATTERNS):
            print(f"[CLEANUP] JUNK: {path.name} ({size_kb:.1f}KB)")
            to_delete.append(path)
            continue

        # Regla 2: Mantener últimos 3 de críticos, eliminar resto
        if any(stem.startswith(crit) for crit in CRITICAL_PREFIXES):
            key = stem  # Agrupar por archivo base
            if key not in kept:
                kept[key] = []
            
            if len(kept[key]) < 3:
                kept[key].append(path)
                print(f"[CLEANUP] KEEP (crítico): {path.name} ({size_kb:.1f}KB)")
            else:
                print(f"[CLEANUP] DELETE (crítico, >3): {path.name} ({size_kb:.1f}KB)")
                to_delete.append(path)
            continue

        # Regla 3: Eliminar todo lo demás (operativo sin uso actual)
        print(f"[CLEANUP] DELETE (operativo): {path.name} ({size_kb:.1f}KB)")
        to_delete.append(path)

    print(f"\n[CLEANUP] Resumen:")
    print(f"  - Total archivos: {len(all_files)}")
    print(f"  - A mantener: {sum(len(v) for v in kept.values())}")
    print(f"  - A eliminar: {len(to_delete)}")
    
    total_free_mb = sum(p.stat().st_size for p in to_delete) / (1024 * 1024)
    print(f"  - Espacio a liberar: {total_free_mb:.2f}MB")

    if to_delete:
        confirm = input("\n¿Proceder con eliminación? (s/n): ")
        if confirm.lower() == 's':
            for path in to_delete:
                try:
                    path.unlink()
                    print(f"  ✓ Eliminado: {path.name}")
                except Exception as e:
                    print(f"  ✗ Fallo: {path.name}: {e}")
        else:
            print("[CLEANUP] Cancelado por usuario.")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
