from __future__ import annotations

import argparse
from pathlib import Path

from .compiler import compile_schematic
from .spec import load_circuit_spec
from .verification import run_verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Generador KiCad verificado desde YAML.")
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args()

    spec_path = args.project_root / "circuito.yaml"
    schematic = args.project_root / "kicad" / f"{args.project_root.name}.kicad_sch"
    spec = load_circuit_spec(spec_path)
    compile_schematic(spec, schematic)
    if not args.no_verify:
        run_verification(args.project_root, schematic)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

