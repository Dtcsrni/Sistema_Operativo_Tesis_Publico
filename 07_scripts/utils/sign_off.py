from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import argparse
import subprocess

from common import ROOT

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wrapper de compatibilidad para registrar firmas humanas en el canon.")
    parser.add_argument("path", help="Ruta del archivo a firmar")
    parser.add_argument("comment", nargs="?", default="Revisado y aprobado por tesista humano.")
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
            "artifact_signed",
            "--path",
            args.path,
            "--comment",
            args.comment,
            "--session-id",
            args.session_id,
        ],
        cwd=ROOT,
    )
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
