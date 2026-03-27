from __future__ import annotations

import argparse
import subprocess
import sys

from common import ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wrapper de compatibilidad para cerrar tareas vía la CLI canónica.")
    parser.add_argument("task_id")
    parser.add_argument("files")
    parser.add_argument("comment", nargs="?", default="")
    parser.add_argument("--session-id", default="workflow_assistant")
    parser.add_argument("--rebuild", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comment = args.comment or f"Tarea {args.task_id} completada y verificada."
    command = [
        sys.executable,
        "07_scripts/tesis.py",
        "task",
        "close",
        "--task-id",
        args.task_id,
        "--files",
        args.files,
        "--comment",
        comment,
        "--session-id",
        args.session_id,
    ]
    if args.rebuild:
        command.append("--rebuild")
    result = subprocess.run(command, cwd=ROOT)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
