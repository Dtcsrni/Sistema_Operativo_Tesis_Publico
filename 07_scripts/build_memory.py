"""build_memory.py — Punto de entrada y re-exportación desde ops/build_memory.py.

El módulo real vive en 07_scripts/ops/build_memory.py.
Este stub permite que audit/validate_memory.py lo importe directamente desde 07_scripts/.
"""
import sys
import importlib
from pathlib import Path

# Añadir ops/ al path pero con nombre diferente para evitar import circular
_ops = Path(__file__).resolve().parent / "ops"
if str(_ops) not in sys.path:
    sys.path.insert(0, str(_ops))

# Importar usando importlib con nombre explícito para evitar circular
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_build_memory_real", _ops / "build_memory.py")
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

OUTPUT_PATH = _mod.OUTPUT_PATH
render_memory = _mod.render_memory
main = _mod.main

if __name__ == "__main__":
    raise SystemExit(main())
