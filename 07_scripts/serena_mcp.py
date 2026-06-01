from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Compatibility wrapper: keeps legacy entrypoint path stable after reorganizing under 07_scripts/serena/.
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

if __name__ == "__main__":
    runpy.run_module("serena.serena_mcp", run_name="__main__")
