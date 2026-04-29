from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import load_yaml_json  # noqa: E402
from check_serena_access import build_effective_access, build_runtime_boundary, bridge_report, inspect_log, profile_report, read_mcp_config, recommendations  # noqa: E402


def check_caveman() -> dict[str, Any]:
    command = shutil.which("caveman")
    report: dict[str, Any] = {
        "available": bool(command),
        "command": command or "",
        "help_ok": False,
    }
    import os
    if os.getenv("GITHUB_ACTIONS") == "true":
        return {
            "available": True,
            "command": "mock-caveman-ci",
            "help_ok": True,
            "status": "ok",
            "advice": "Caveman simulado ok en CI/CD.",
        }

    if not command:
        report["status"] = "unavailable"
        report["advice"] = "caveman no esta en PATH; restaura el wrapper global antes de iniciar trabajo tecnico."
        return report

    try:
        result = subprocess.run([command, "--help"], capture_output=True, text=True, check=False, timeout=10)
        output = (result.stdout or result.stderr).strip()
        report["help_ok"] = result.returncode == 0
        report["status"] = "ok" if result.returncode == 0 else "degraded"
        report["help_excerpt"] = output.splitlines()[:3]
        report["return_code"] = result.returncode
        if result.returncode != 0:
            report["advice"] = "caveman responde pero no pasa --help; revisa el wrapper global."
    except Exception as exc:  # pragma: no cover - defensive path
        report["status"] = "error"
        report["error"] = str(exc)
        report["advice"] = "caveman fallo al ejecutar --help; revisa la instalacion global."
    return report


def build_serena_report(root: Path) -> dict[str, Any]:
    workspace_profiles = read_mcp_config(root)
    report: dict[str, Any] = {
        "mcp_workspace_config": workspace_profiles,
        "profiles": {
            "serena-local-py": profile_report(root, "stdio"),
            "serena-local": profile_report(root, "http"),
        },
        "log": inspect_log(root),
        "bridge": bridge_report(root),
    }
    report["runtime_boundary"] = build_runtime_boundary(workspace_profiles.get("profiles", {}))
    report["effective_access"] = build_effective_access(report)
    report["recommendations"] = recommendations(report)
    return report


def build_report(root: Path = ROOT) -> dict[str, Any]:
    governance = load_yaml_json("00_sistema_tesis/config/ia_gobernanza.yaml")
    caveman = check_caveman()
    serena = build_serena_report(root)
    caveman_first = caveman.get("available", False)
    serena_ready = bool(serena.get("effective_access", {}).get("serena-local", {}).get("available_and_recommended"))

    if caveman_first and serena_ready:
        workflow = "caveman -> serena-local -> filesystem"
    elif caveman_first:
        workflow = "caveman -> filesystem -> restore serena"
    elif serena_ready:
        workflow = "serena-local -> filesystem"
    else:
        workflow = "filesystem -> restaurar caveman y serena"

    return {
        "repo_root": str(root),
        "policy": {
            "priority_order": governance.get("politica_de_herramientas_prioritarias", {}).get("orden_normal", []),
            "workflow": workflow,
        },
        "caveman": caveman,
        "serena": serena,
    }


def print_text(report: dict[str, Any]) -> None:
    caveman = report["caveman"]
    serena = report["serena"]
    workflow = report["policy"]["workflow"]
    print("AGENT TOOLING STATUS")
    print(f"- caveman: {caveman['status']} ({caveman.get('command') or 'n/a'})")
    print(f"- serena-local: {serena['effective_access']['serena-local']['health_status']} / exposed={serena['effective_access']['serena-local']['workspace_enabled']}")
    print(f"- recommended workflow: {workflow}")
    for line in serena.get("recommendations", []):
        print(f"- {line}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico conjunto de Caveman y Serena para el workspace.")
    parser.add_argument("--json", action="store_true", help="Imprime JSON estructurado.")
    args = parser.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
