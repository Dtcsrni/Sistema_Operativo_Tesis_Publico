from __future__ import annotations

import runpy
from pathlib import Path

# Exportar para tests
try:
    from audit.governance_gate import *
except ImportError:
    pass

TARGET = Path(__file__).resolve().parent / "audit" / "governance_gate.py"

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
