from __future__ import annotations

import importlib.util
import runpy
from pathlib import Path

# Exportar símbolos para tests sin depender de que 07_scripts/ops sea un paquete.
_TARGET = Path(__file__).resolve().parent / "ops" / "sync_public_repo.py"
_spec = importlib.util.spec_from_file_location("siot_ops_sync_public_repo", _TARGET)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    for _name, _value in vars(_mod).items():
        if _name.startswith("__"):
            continue
        globals().setdefault(_name, _value)

if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")
