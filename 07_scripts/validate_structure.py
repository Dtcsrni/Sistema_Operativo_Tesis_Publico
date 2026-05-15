from __future__ import annotations

import runpy
import importlib.util
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "audit" / "validate_structure.py"

_spec = importlib.util.spec_from_file_location("_audit_validate_structure", TARGET)
if _spec is None or _spec.loader is None:
    raise ImportError(f"No se pudo cargar {TARGET}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

validate = _module.validate
validate_identity = _module.validate_identity
main = _module.main

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
