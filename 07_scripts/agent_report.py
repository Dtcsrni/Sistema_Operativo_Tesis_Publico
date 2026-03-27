from __future__ import annotations

import argparse
import subprocess
import sys

from common import ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wrapper de compatibilidad para registrar actividad agéntica en el canon.")
    parser.add_argument("session_id")
    parser.add_argument("task_summary")
    parser.add_argument("files", nargs="?", default="")
    parser.add_argument("--agent-name", default="")
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
            "agent_activity",
            "--session-id",
            args.session_id,
            "--task-summary",
            args.task_summary,
            "--files",
            args.files,
            "--agent-name",
            args.agent_name,
        ],
        cwd=ROOT,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
