from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HISTORY_PATH = ROOT / "00_sistema_tesis" / "bitacora" / "audit_history" / "test_impact_history.jsonl"

INTEGRATION_MARKERS = (
    "docker-compose",
    "Dockerfile",
    "04_implementacion/control_mission",
    "runtime/openclaw",
    "runtime/edge_iot",
    "runtime/pc_control",
    "config/env/",
)
IGNORED_IMPACT_PREFIXES = (
    "00_sistema_tesis/bitacora/audit_history/",
    "06_dashboard/generado/",
    ".pytest_cache/",
)
IGNORED_IMPACT_SUFFIXES = (
    "__pycache__",
    ".pyc",
)


@dataclass(frozen=True)
class TestCommand:
    id: str
    command: list[str]
    reason: str
    scope: str = "focused"
    requires_justification: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_git(args: list[str]) -> list[str]:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def discover_changed_paths() -> list[str]:
    paths = set(run_git(["diff", "--name-only", "HEAD", "--"]))
    paths.update(run_git(["ls-files", "--others", "--exclude-standard"]))
    return sorted(path for path in paths if path and not is_ignored_impact_path(path))


def is_ignored_impact_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized == "00_sistema_tesis/bitacora/audit_history/test_impact_history.jsonl":
        return True
    if any(normalized.startswith(prefix) for prefix in IGNORED_IMPACT_PREFIXES):
        return True
    return any(part.endswith(IGNORED_IMPACT_SUFFIXES) for part in normalized.split("/"))


def existing(paths: list[str]) -> list[str]:
    return [path for path in paths if (ROOT / path).exists()]


def add_command(commands: dict[str, TestCommand], command: TestCommand) -> None:
    commands.setdefault(command.id, command)


def direct_python_test_for(path: str) -> str | None:
    p = Path(path)
    if p.name.startswith("test_") and p.suffix == ".py" and "tests" in p.parts:
        module = ".".join(p.with_suffix("").parts)
        return module
    return None


def select_commands(changed_paths: list[str]) -> list[TestCommand]:
    commands: dict[str, TestCommand] = {}
    for path in changed_paths:
        direct = direct_python_test_for(path)
        if direct:
            add_command(
                commands,
                TestCommand(
                    id=f"unittest:{direct}",
                    command=["python3", "-m", "unittest", direct, "-v"],
                    reason=f"archivo de prueba modificado: {path}",
                ),
            )

        if path == "07_scripts/ops/agent_ops_core_gate.py" or "spec_agent_ops_core" in path:
            add_command(
                commands,
                TestCommand(
                    id="agent_ops_core_gate_unit",
                    command=["python3", "-m", "unittest", "07_scripts.tests.test_agent_ops_core_gate", "-v"],
                    reason="cambio en Agent Ops Core o su spec",
                ),
            )
            add_command(
                commands,
                TestCommand(
                    id="agent_ops_core_gate_dry",
                    command=["python3", "07_scripts/ops/agent_ops_core_gate.py", "--no-live", "--json"],
                    reason="validar reporte sistemico sin checks externos",
                ),
            )

        if path == "07_scripts/ops/test_impact_gate.py":
            add_command(
                commands,
                TestCommand(
                    id="test_impact_gate_unit",
                    command=["python3", "-m", "unittest", "07_scripts.tests.test_test_impact_gate", "-v"],
                    reason="cambio en selector incremental de pruebas",
                ),
            )
            add_command(
                commands,
                TestCommand(
                    id="test_impact_gate_dry",
                    command=["python3", "07_scripts/ops/test_impact_gate.py", "--paths", path, "--json"],
                    reason="validar salida JSON del selector incremental",
                ),
            )

        if path == "07_scripts/ops/human_validation_gate.py":
            add_command(
                commands,
                TestCommand(
                    id="human_validation_gate_unit",
                    command=["python3", "-m", "unittest", "07_scripts.tests.test_human_validation_gate", "-v"],
                    reason="cambio en gate de validacion humana",
                ),
            )
            add_command(
                commands,
                TestCommand(
                    id="human_validation_gate_dry",
                    command=["python3", "07_scripts/ops/human_validation_gate.py", "--json"],
                    reason="validar salida dry-run sin mutar canon",
                ),
            )

        if path.startswith("07_scripts/serena/") or path in {"07_scripts/serena_mcp.py", "07_scripts/serena_http_supervisor.py"}:
            add_command(
                commands,
                TestCommand(
                    id="serena_contract_tests",
                    command=[
                        "python3",
                        "-m",
                        "unittest",
                        "07_scripts.tests.test_check_serena_access",
                        "07_scripts.tests.test_check_serena_multi_host_contract",
                        "07_scripts.tests.test_serena_mcp",
                        "07_scripts.tests.test_serena_policy",
                        "-v",
                    ],
                    reason="cambio en Serena MCP o contrato multi-host",
                ),
            )

        if path.startswith("07_scripts/audit/"):
            stem = Path(path).stem
            candidate = ROOT / "07_scripts" / "tests" / f"test_{stem}.py"
            if candidate.exists():
                add_command(
                    commands,
                    TestCommand(
                        id=f"audit:{stem}",
                        command=["python3", "-m", "unittest", f"07_scripts.tests.test_{stem}", "-v"],
                        reason=f"prueba directa para {path}",
                    ),
                )

        if path.startswith("07_scripts/build_runner/") or path == "07_scripts/build_all.py":
            add_command(
                commands,
                TestCommand(
                    id="build_all_contract",
                    command=["python3", "-m", "pytest", "tests/test_build_all.py", "-q"],
                    reason="cambio en build incremental o registro de pasos",
                ),
            )

        if path.startswith("runtime/openclaw/") or path.startswith("config/env/openclaw"):
            add_command(
                commands,
                TestCommand(
                    id="openclaw_focused",
                    command=[
                        "python3",
                        "-m",
                        "pytest",
                        "tests/test_openclaw_cli.py",
                        "tests/test_openclaw_runtime.py",
                        "tests/test_openclaw_sources_and_routing.py",
                        "-q",
                    ],
                    reason="cambio en runtime/config OpenClaw",
                    scope="focused-integration",
                    requires_justification=True,
                ),
            )

        if path.startswith("04_implementacion/control_mission/src/"):
            related_ts = related_control_mission_tests(path)
            if related_ts:
                add_command(
                    commands,
                    TestCommand(
                        id="mission_control_related_ts",
                        command=["npx", "tsx", "--test", "--test-concurrency=1", *related_ts],
                        reason="pruebas TypeScript relacionadas con Mission Control",
                        scope="focused",
                    ),
                )
            else:
                add_command(
                    commands,
                    TestCommand(
                        id="mission_control_unit_all",
                        command=["npm", "test"],
                        reason="cambio Mission Control sin prueba directa localizada",
                        scope="component",
                        requires_justification=True,
                    ),
                )

        if path.startswith("docker-compose") or Path(path).name.startswith("Dockerfile"):
            add_command(
                commands,
                TestCommand(
                    id="docker_stack_focused",
                    command=["python3", "-m", "pytest", "tests/test_docker_stack.py", "-q"],
                    reason="cambio en Docker/Compose",
                    scope="integration",
                    requires_justification=True,
                ),
            )

        if path.startswith("00_sistema_tesis/pendientes/"):
            add_command(
                commands,
                TestCommand(
                    id="sdd_specs",
                    command=["python3", "07_scripts/audit/validate_sdd_specs.py", "--json"],
                    reason="cambio en specs o pendientes SDD",
                ),
            )

    if not commands:
        add_command(
            commands,
            TestCommand(
                id="agent_ops_core_gate_dry",
                command=["python3", "07_scripts/ops/agent_ops_core_gate.py", "--no-live", "--json"],
                reason="fallback minimo cuando no hay mapeo especifico",
            ),
        )
    return list(commands.values())


def related_control_mission_tests(path: str) -> list[str]:
    p = Path(path)
    candidates: list[Path] = []
    if p.name.endswith(".test.ts"):
        candidates.append(ROOT / path)
    else:
        sibling = ROOT / p.with_suffix(".test.ts")
        candidates.append(sibling)
        if p.name == "route.ts":
            candidates.extend((ROOT / "04_implementacion" / "control_mission" / "src" / "lib").glob("*.test.ts"))
    return [candidate.relative_to(ROOT / "04_implementacion" / "control_mission").as_posix() for candidate in candidates if candidate.exists()]


def file_digest(path: str) -> str:
    full = ROOT / path
    h = hashlib.sha256()
    h.update(path.encode("utf-8"))
    if full.exists() and full.is_file():
        h.update(full.read_bytes())
    else:
        h.update(b"<missing>")
    return h.hexdigest()


def impact_key(changed_paths: list[str], commands: list[TestCommand]) -> str:
    h = hashlib.sha256()
    for path in sorted(changed_paths):
        h.update(file_digest(path).encode("ascii"))
    for command in commands:
        h.update(command.id.encode("utf-8"))
        h.update("\0".join(command.command).encode("utf-8"))
    return h.hexdigest()


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def history_match(history: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    for entry in reversed(history):
        if entry.get("impact_key") == key:
            return entry
    return None


def append_history(path: Path, report: dict[str, Any], result_status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "impact_key": report["impact_key"],
        "result_status": result_status,
        "changed_paths": report["changed_paths"],
        "selected_command_ids": [item["id"] for item in report["selected_commands"]],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def build_report(
    *,
    paths: list[str] | None = None,
    history_path: Path = DEFAULT_HISTORY_PATH,
) -> dict[str, Any]:
    changed_paths = sorted(path for path in (paths if paths is not None else discover_changed_paths()) if not is_ignored_impact_path(path))
    changed_paths = existing(changed_paths)
    commands = select_commands(changed_paths)
    key = impact_key(changed_paths, commands)
    history = load_history(history_path)
    previous = history_match(history, key)
    integration = [cmd for cmd in commands if cmd.requires_justification]
    status = "degraded" if integration else "ok"
    redundancy = "previous_ok_same_impact" if previous and previous.get("result_status") == "ok" else "none"
    return {
        "status": status,
        "repo_root": str(ROOT),
        "changed_paths": changed_paths,
        "impact_key": key,
        "history_path": str(history_path.relative_to(ROOT) if history_path.is_relative_to(ROOT) else history_path),
        "history_match": previous,
        "redundancy_hint": redundancy,
        "selected_commands": [cmd.to_dict() for cmd in commands],
        "integration_commands_require_justification": [cmd.id for cmd in integration],
        "next_action": (
            "review_integration_justification_before_running"
            if integration
            else ("skip_or_run_smoke_only_if_previous_ok_is_trusted" if redundancy != "none" else "run_selected_commands")
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Selecciona pruebas por impacto y mantiene historial para evitar redundancia.")
    parser.add_argument("--json", action="store_true", help="Emitir JSON.")
    parser.add_argument("--paths", nargs="*", help="Rutas cambiadas explicitas. Si se omite, usa git diff/list untracked.")
    parser.add_argument("--history", default=str(DEFAULT_HISTORY_PATH))
    parser.add_argument("--record", choices=["ok", "failed", "skipped"], help="Registra el resultado del plan actual en historial.")
    args = parser.parse_args()

    report = build_report(paths=args.paths, history_path=Path(args.history))
    if args.record:
        append_history(Path(args.history), report, args.record)
        report["recorded_result_status"] = args.record
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"TEST IMPACT: {report['status']}")
        print(f"- changed paths: {len(report['changed_paths'])}")
        print(f"- redundancy: {report['redundancy_hint']}")
        for command in report["selected_commands"]:
            marker = " [integration]" if command["requires_justification"] else ""
            print(f"- {command['id']}{marker}: {' '.join(command['command'])}")
        print(f"- next: {report['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
