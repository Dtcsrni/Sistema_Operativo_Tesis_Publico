#!/usr/bin/env python3
"""
docker_cache_policy.py — Política automática de caché Docker para OpenClaw
===========================================================================
Implementa la DEC-XXXX de gestión eficiente de build cache:
  - Nivel 1 (soft): prune suave, retiene layers de la última semana
  - Nivel 2 (standard): keep-storage 4GB (default, ejecución semanal)
  - Nivel 3 (hard): purga total del caché (pre-rebuild o mantenimiento)

Integración con build_all.py:
  python 07_scripts/ops/docker_cache_policy.py --level standard

Uso directo:
  python 07_scripts/ops/docker_cache_policy.py [--level soft|standard|hard] [--dry-run] [--report]

Política definida (alineada con daemon.json defaultKeepStorage=6GB):
  - BuildKit GC automático: 6 GB máximo continuo
  - Prune semanal programado: keep 4 GB (nivel standard)
  - Prune pre-rebuild de imágenes grandes (>5 GB): nivel hard sobre caché antiguo
  - .dockerignore: excluir runtime/state/, web_session_profile/, evidencia_privada/

Integración con AGENTS.md: No ejecuta eliminaciones sin reportar resultado.
"""

import subprocess
import json
import sys
import os
import argparse
from datetime import datetime

# Forzar UTF-8 en Windows para compatibilidad con caracteres especiales
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Constantes de política ─────────────────────────────────────────────────

POLICY = {
    "soft": {
        "description": "Prune suave — elimina solo caché no referenciado de >48h",
        "cmd": ["docker", "buildx", "prune", "--filter", "until=48h", "--force"],
        "max_gb": None,
    },
    "standard": {
        "description": "Prune estándar — retiene 4 GB de caché más reciente (ejecución semanal recomendada)",
        "cmd": ["docker", "buildx", "prune", "--reserved-space", "4GB", "--force"],
        "max_gb": 4,
    },
    "hard": {
        "description": "Prune agresivo — retiene solo 1 GB (pre-rebuild de imágenes grandes)",
        "cmd": ["docker", "buildx", "prune", "--reserved-space", "1GB", "--force"],
        "max_gb": 1,
    },
}

TARGETS_GB = {
    "soft": 10,      # objetivo: <10 GB después del prune suave
    "standard": 5,   # objetivo: <5 GB (alineado con daemon.json 6GB)
    "hard": 2,       # objetivo: <2 GB (máximo compresión)
}


def get_docker_df() -> dict:
    """Obtiene el uso actual de disco de Docker."""
    result = subprocess.run(
        ["docker", "system", "df", "--format", "json"],
        capture_output=True, text=True
    )
    # docker system df --format json retorna líneas JSON, no un array
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    items = {}
    for line in lines:
        try:
            obj = json.loads(line)
            t = obj.get("Type", "")
            items[t] = obj
        except Exception:
            pass

    # Fallback: parsear texto plano
    if not items:
        result2 = subprocess.run(["docker", "system", "df"], capture_output=True, text=True)
        return {"raw": result2.stdout}
    return items


def get_build_cache_gb() -> float:
    """Retorna el tamaño total del build cache en GB."""
    result = subprocess.run(
        ["docker", "buildx", "du"],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith("Total:"):
            parts = line.split()
            if len(parts) >= 2:
                size_str = parts[1]
                try:
                    if "GB" in size_str:
                        return float(size_str.replace("GB", ""))
                    elif "MB" in size_str:
                        return float(size_str.replace("MB", "")) / 1024
                    elif "kB" in size_str:
                        return float(size_str.replace("kB", "")) / (1024 * 1024)
                except ValueError:
                    pass
    return 0.0


def run_prune(level: str, dry_run: bool = False) -> tuple[bool, str]:
    """Ejecuta el prune según el nivel de política."""
    policy = POLICY[level]
    cmd = policy["cmd"]

    if dry_run:
        print(f"[DRY-RUN] Comando que se ejecutaría:")
        print(f"  {' '.join(cmd)}")
        return True, "dry-run"

    print(f"[INFO] Ejecutando política '{level}': {policy['description']}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # Extraer total liberado del output
        freed = "desconocido"
        for line in result.stdout.splitlines():
            if "Total:" in line or "freed" in line.lower():
                freed = line.strip()
        return True, freed
    else:
        return False, result.stderr.strip()


def check_daemon_config() -> dict:
    """Verifica la configuración actual del daemon de Docker."""
    import os, pathlib
    daemon_paths = [
        pathlib.Path.home() / ".docker" / "daemon.json",
        pathlib.Path("C:/ProgramData/Docker/config/daemon.json"),
    ]
    for p in daemon_paths:
        if p.exists():
            try:
                with open(p) as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def report_status():
    """Imprime un reporte del estado actual de caché y política."""
    print("\n" + "=" * 60)
    print("  REPORTE DE CACHÉ DOCKER — OpenClaw Cache Policy")
    print("=" * 60)

    cache_gb = get_build_cache_gb()
    print(f"\n  Build Cache actual:  {cache_gb:.2f} GB")

    daemon = check_daemon_config()
    keep = daemon.get("builder", {}).get("gc", {}).get("defaultKeepStorage", "no configurado")
    gc_enabled = daemon.get("builder", {}).get("gc", {}).get("enabled", False)
    print(f"  GC automatico:       {'[OK] habilitado' if gc_enabled else '[--] deshabilitado'}")
    print(f"  defaultKeepStorage:  {keep}")

    print(f"\n  Umbrales de política:")
    for lvl, target in TARGETS_GB.items():
        status = "[OK]" if cache_gb <= target else "[!!]"
        print(f"    {lvl:10s}: objetivo <{target} GB  {status}")

    print(f"\n  Recomendación:")
    if cache_gb > 15:
        print(f"    → Ejecutar nivel 'hard':     python 07_scripts/ops/docker_cache_policy.py --level hard")
    elif cache_gb > 8:
        print(f"    → Ejecutar nivel 'standard': python 07_scripts/ops/docker_cache_policy.py --level standard")
    elif cache_gb > 4:
        print(f"    → Ejecutar nivel 'soft':     python 07_scripts/ops/docker_cache_policy.py --level soft")
    else:
        print(f"    → Caché dentro del objetivo. Sin acción necesaria. ✅")

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Política de gestión de caché Docker para OpenClaw"
    )
    parser.add_argument(
        "--level",
        choices=["soft", "standard", "hard"],
        default="standard",
        help="Nivel de política de prune (default: standard)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra el comando sin ejecutarlo"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Solo muestra el reporte de estado actual"
    )
    args = parser.parse_args()

    if args.report:
        report_status()
        return

    # Pre-estado
    before_gb = get_build_cache_gb()
    print(f"[INFO] Build cache antes: {before_gb:.2f} GB")
    print(f"[INFO] Política seleccionada: {args.level}")
    print(f"[INFO] {POLICY[args.level]['description']}")

    # Ejecutar prune
    success, detail = run_prune(args.level, args.dry_run)

    if not args.dry_run:
        after_gb = get_build_cache_gb()
        freed_gb = before_gb - after_gb
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        print(f"\n[RESULTADO]")
        print(f"  Estado:    {'✅ OK' if success else '❌ ERROR'}")
        print(f"  Antes:     {before_gb:.2f} GB")
        print(f"  Después:   {after_gb:.2f} GB")
        print(f"  Liberado:  {freed_gb:.2f} GB")
        print(f"  Detalle:   {detail}")
        print(f"  Timestamp: {timestamp}")

        target = TARGETS_GB[args.level]
        if after_gb > target:
            print(f"[WARN] Cache ({after_gb:.1f} GB) sigue sobre objetivo ({target} GB)")
            print(f"       Considera ejecutar nivel superior o revisar imagenes")
        else:
            print(f"[OK] Cache dentro del objetivo ({target} GB) [OK]")

        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
