from __future__ import annotations

import argparse
import subprocess
import sys

from common import ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wrapper de compatibilidad para registrar validaciones humanas en el canon.")
    parser.add_argument("--step", required=True, help="Step ID (ej: VAL-STEP-XXX)")
    parser.add_argument("--level", default="MEDIO", choices=["BAJO", "MEDIO", "ALTO", "CRÍTICO"], help="Nivel de auditoría")
    parser.add_argument("--content", required=True, help="Contenido de la validación")
    parser.add_argument("--link", default="[DEC-0014]", help="Vínculo (ej: DEC-XXXX)")
    parser.add_argument("--matrix-summary", default="Cambio registrado en canon")
    parser.add_argument("--matrix-reference", default="")
    parser.add_argument("--ethical-alignment", default="Responsabilidad (ISO 42001)")
    parser.add_argument("--state-label", default="[x] Validado")
    parser.add_argument("--session-id", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = subprocess.run(
        [
            sys.executable,
            "07_scripts/tesis.py",
            "event",
            "append",
            "--type",
            "human_validation",
            "--step-id",
            args.step,
            "--audit-level",
            args.level,
            "--content",
            args.content,
            "--linked-reference",
            args.link,
            "--matrix-summary",
            args.matrix_summary,
            "--matrix-reference",
            args.matrix_reference,
            "--ethical-alignment",
            args.ethical_alignment,
            "--state-label",
            args.state_label,
            "--session-id",
            args.session_id,
        ],
        cwd=ROOT,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
