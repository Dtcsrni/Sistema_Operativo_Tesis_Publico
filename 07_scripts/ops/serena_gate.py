#!/usr/bin/env python3
"""Puerta fail-closed para Serena: ejecuta `check_serena_access.py --json` y falla si la salud no es 'ok' o no arrancó.
Salida: exit 0 si pasa; exit 2 si falla (uso en hooks/CI).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    script = Path(__file__).resolve().parents[1] / "serena" / "check_serena_access.py"
    cmd = [sys.executable, str(script), "--json"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    except Exception as e:
        print("Error ejecutando check_serena_access:", e, file=sys.stderr)
        return 2

    if p.returncode != 0:
        print("check_serena_access returned non-zero:", p.returncode, file=sys.stderr)
        if p.stderr:
            print(p.stderr, file=sys.stderr)
        return 2

    try:
        data = json.loads(p.stdout)
    except Exception as e:
        print("Salida JSON inválida de check_serena_access:", e, file=sys.stderr)
        print(p.stdout, file=sys.stderr)
        return 2

    profiles = data.get("profiles", {})
    serena_local = profiles.get("serena-local") or data.get("serena-local") or data
    health = serena_local.get("healthcheck") or serena_local.get("health")
    status = None
    if isinstance(health, dict):
        status = health.get("status")
    else:
        # Try root-level health
        status = data.get("health", {}).get("status")

    if status == "ok":
        print("Serena gate PASSED (already running)")
        return 0

    startup = None
    if isinstance(serena_local, dict):
        startup = serena_local.get("startup")
    if not startup:
        startup = data.get("startup")

    if not (isinstance(startup, dict) and startup.get("started") is True):
        print("Serena health not OK and not auto-started", file=sys.stderr)
        return 2

    print("Serena gate PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
