from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path(__file__).resolve().parent / "audit" / "verify_bitacora_chain.py"

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
