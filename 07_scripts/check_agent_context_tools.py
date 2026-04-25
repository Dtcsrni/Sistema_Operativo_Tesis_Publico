from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from check_serena_access import collect_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verificador unificado de disponibilidad Caveman + Serena para sesiones del repositorio."
    )
    parser.add_argument("--json", action="store_true", help="Imprime reporte completo en JSON.")
    parser.add_argument(
        "--attempt-start-http",
        action="store_true",
        help="Intenta levantar `serena-local` por HTTP antes de evaluar recomendacion.",
    )
    return parser.parse_args()


def _run_shell(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    payload = (result.stdout or result.stderr or "").strip()
    return result.returncode, payload


def caveman_report() -> dict[str, Any]:
    where_code, where_text = _run_shell(["bash", "-lc", "command -v caveman"])
    help_code, help_text = _run_shell(["bash", "-lc", "caveman --help"])
    available = where_code == 0 and bool(where_text.strip()) and help_code == 0
    return {
        "available": available,
        "path": where_text.strip() if where_code == 0 else "",
        "help_ok": help_code == 0,
        "help_preview": (help_text.splitlines()[0] if help_text else ""),
    }


def compute_exit_code(caveman: dict[str, Any], serena: dict[str, Any]) -> int:
    serena_ready = bool(
        serena.get("effective_access", {}).get("serena-local", {}).get("available_and_recommended", False)
    )
    caveman_ready = bool(caveman.get("available", False))
    if caveman_ready and serena_ready:
        return 0
    if caveman_ready and not serena_ready:
        return 2
    if not caveman_ready and serena_ready:
        return 3
    return 4


def collect_unified_report(*, attempt_start_http: bool = False) -> dict[str, Any]:
    caveman = caveman_report()
    serena = collect_report(attempt_start_http_if_needed=attempt_start_http)
    exit_code = compute_exit_code(caveman, serena)
    return {
        "repo_root": str(ROOT),
        "caveman": caveman,
        "serena": serena,
        "status": {
            "caveman_ready": caveman["available"],
            "serena_recommended": serena.get("effective_access", {})
            .get("serena-local", {})
            .get("available_and_recommended", False),
            "exit_code": exit_code,
        },
    }


def main() -> int:
    args = parse_args()
    report = collect_unified_report(attempt_start_http=args.attempt_start_http)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(report["status"]["exit_code"])

    print("AGENT CONTEXT TOOLS REPORT")
    print(f"- Repo root: {report['repo_root']}")
    print(
        "- Caveman: "
        f"available={report['caveman']['available']} "
        f"path={report['caveman']['path']} "
        f"help_ok={report['caveman']['help_ok']}"
    )
    if report["caveman"]["help_preview"]:
        print(f"  help_preview: {report['caveman']['help_preview']}")
    serena_local = report["serena"]["effective_access"]["serena-local"]
    print(
        "- Serena(local): "
        f"workspace_enabled={serena_local['workspace_enabled']} "
        f"health={serena_local['health_status']} "
        f"recommended={serena_local['available_and_recommended']}"
    )
    startup = report["serena"].get("startup")
    if startup:
        print(
            "- Serena startup: "
            f"attempted={startup.get('attempted', False)} "
            f"status={startup.get('status', 'unknown')} "
            f"reason={startup.get('reason', '')}"
        )
    print(f"- Exit code: {report['status']['exit_code']}")
    return int(report["status"]["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
