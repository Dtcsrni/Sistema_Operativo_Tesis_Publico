from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wrapper legado hacia `tesis sync`.")
    parser.add_argument("message", help="Mensaje del commit principal")
    parser.add_argument("--step-id", default=os.getenv("SISTEMA_TESIS_STEP_ID", "").strip())
    parser.add_argument("--agent", default=os.getenv("SISTEMA_TESIS_AGENT", "").strip())
    parser.add_argument("--push", action="store_true", help="Empuja al remoto al finalizar")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cmd = [sys.executable, "07_scripts/tesis.py", "sync", "--message", args.message]
    if args.step_id:
        cmd.extend(["--step-id", args.step_id])
    if args.agent:
        cmd.extend(["--agent", args.agent])
    if args.push:
        cmd.append("--push")
    if args.remote:
        cmd.extend(["--remote", args.remote])
    if args.branch:
        cmd.extend(["--branch", args.branch])

    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
