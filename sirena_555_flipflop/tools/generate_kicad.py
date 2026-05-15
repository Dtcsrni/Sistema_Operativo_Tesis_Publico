from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(REPO / "07_scripts"))

from eda_kicad.compiler import compile_schematic
from eda_kicad.spec import load_circuit_spec
from eda_kicad.symbols import LOCAL_LIBRARY, kicad_symbol_library_text
from eda_kicad.verification import run_verification


PROJECT_NAME = "sirena_555_flipflop"


def project_text() -> str:
    return json.dumps(
        {
            "board": {"layer_pairs": [], "viewports": []},
            "boards": [],
            "cvpcb": {"equivalence_files": []},
            "erc": {"erc_exclusions": [], "meta": {"version": 0}, "pin_map": []},
            "meta": {"filename": f"{PROJECT_NAME}.kicad_pro", "version": 1},
            "schematic": {"annotate_start_num": 1, "legacy_lib_dir": "", "legacy_lib_list": []},
            "text_variables": {},
        },
        indent=2,
    ) + "\n"


def main() -> int:
    kicad_dir = ROOT / "kicad"
    kicad_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "export").mkdir(parents=True, exist_ok=True)
    (kicad_dir / f"{PROJECT_NAME}.kicad_pro").write_text(project_text(), encoding="utf-8")
    symbol_library = kicad_dir / "sirena.kicad_sym"
    symbol_library.write_text(kicad_symbol_library_text(), encoding="utf-8")
    (kicad_dir / "sym-lib-table").write_text(
        "(sym_lib_table\n"
        f'  (lib (name "{LOCAL_LIBRARY}")(type "KiCad")(uri "${{KIPRJMOD}}/{symbol_library.name}")(options "")(descr "Simbolos locales generados para sirena_555_flipflop"))\n'
        ")\n",
        encoding="utf-8",
    )
    spec = load_circuit_spec(ROOT / "circuito.yaml")
    schematic = kicad_dir / f"{PROJECT_NAME}.kicad_sch"
    compile_schematic(spec, schematic)
    run_verification(ROOT, schematic)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
