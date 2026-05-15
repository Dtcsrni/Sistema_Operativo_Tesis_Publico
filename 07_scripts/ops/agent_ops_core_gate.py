from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "00_sistema_tesis" / "pendientes" / "2026-05-13_spec_agent_ops_core_optimizacion_holistica.md"
MISSION_CONTROL_DB = ROOT / "04_implementacion" / "control_mission" / "mission-control.db"

STANDARD_KEYS = (
    "status",
    "available",
    "recommended",
    "blocking_reason",
    "affected_paths",
    "required_step_id",
    "next_action",
)

REQUIRED_SPEC_TERMS = (
    "Objetivo",
    "Alcance",
    "Rutas Afectadas",
    "decisions:",
    "step_id:",
    "Gates Publicos",
    "Pruebas y Aceptacion",
    "Rollback",
    "Cierre de Trazabilidad",
    "FRE",
    "ESE",
)

EXTERNAL_MCP_CONTRACTS = [
    {
        "capability_id": "zotero",
        "backend": "mcp",
        "auth_required": True,
        "live_check": "connector_health",
        "fallback": "manual_bibliography_export",
        "allowed_domains": ["academico"],
        "trace_level": "alto",
    },
    {
        "capability_id": "scite_arxiv",
        "backend": "mcp",
        "auth_required": False,
        "live_check": "query_smoke_test",
        "fallback": "web_or_manual_source_lookup",
        "allowed_domains": ["academico"],
        "trace_level": "alto",
    },
    {
        "capability_id": "e2b",
        "backend": "mcp",
        "auth_required": True,
        "live_check": "sandbox_create_probe",
        "fallback": "local_tests_or_manual_sandbox",
        "allowed_domains": ["profesional", "academico"],
        "trace_level": "alto",
    },
    {
        "capability_id": "playwright",
        "backend": "mcp",
        "auth_required": False,
        "live_check": "browser_launch_probe",
        "fallback": "local_playwright_or_supervised_manual_browser",
        "allowed_domains": ["profesional", "academico"],
        "trace_level": "medio",
    },
    {
        "capability_id": "github",
        "backend": "mcp",
        "auth_required": True,
        "live_check": "repo_metadata_probe",
        "fallback": "git_cli_read_only",
        "allowed_domains": ["profesional", "academico"],
        "trace_level": "alto",
    },
    {
        "capability_id": "docker",
        "backend": "mcp",
        "auth_required": False,
        "live_check": "docker_info_probe",
        "fallback": "docker_cli_read_only",
        "allowed_domains": ["profesional", "academico", "edge"],
        "trace_level": "alto",
    },
]


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


def standard_result(
    *,
    status: str,
    available: bool,
    recommended: bool,
    blocking_reason: str = "",
    affected_paths: list[str] | None = None,
    required_step_id: str = "",
    next_action: str = "none",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "available": available,
        "recommended": recommended,
        "blocking_reason": blocking_reason,
        "affected_paths": affected_paths or [],
        "required_step_id": required_step_id,
        "next_action": next_action,
    }
    if details is not None:
        payload["details"] = details
    return payload


def run_command(command: list[str], *, timeout: int = 60) -> CommandResult:
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(result.returncode, result.stdout.strip(), result.stderr.strip())


def parse_json_output(text: str) -> dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    return {}


def check_agent_context_tools() -> dict[str, Any]:
    command = ["python3", "07_scripts/audit/check_agent_context_tools.py", "--attempt-start-http", "--json"]
    try:
        result = run_command(command, timeout=90)
    except Exception as exc:
        return standard_result(
            status="unavailable",
            available=False,
            recommended=False,
            blocking_reason=f"agent_context_tools_exception:{exc}",
            affected_paths=["07_scripts/audit/check_agent_context_tools.py"],
            next_action="repair_agent_context_tools",
        )
    payload = parse_json_output(result.stdout)
    status = dict(payload.get("status", {}))
    ready = result.returncode == 0 and bool(status.get("caveman_ready")) and bool(status.get("serena_recommended"))
    return standard_result(
        status="ok" if ready else "degraded",
        available=bool(status.get("caveman_ready")) and bool(payload.get("serena")),
        recommended=ready,
        blocking_reason="" if ready else (result.stderr or "caveman_or_serena_not_ready"),
        affected_paths=["07_scripts/audit/check_agent_context_tools.py"],
        next_action="none" if ready else "restore_caveman_or_serena",
        details={
            "exit_code": result.returncode,
            "caveman_ready": bool(status.get("caveman_ready")),
            "serena_recommended": bool(status.get("serena_recommended")),
        },
    )


def check_serena_access() -> dict[str, Any]:
    command = ["python3", "07_scripts/serena/check_serena_access.py", "--attempt-start-http", "--json"]
    try:
        result = run_command(command, timeout=90)
    except Exception as exc:
        return standard_result(
            status="unavailable",
            available=False,
            recommended=False,
            blocking_reason=f"serena_access_exception:{exc}",
            affected_paths=["07_scripts/serena/check_serena_access.py"],
            next_action="restore_serena_http",
        )
    payload = parse_json_output(result.stdout)
    serena_local = dict(dict(payload.get("effective_access", {})).get("serena-local", {}))
    ready = result.returncode == 0 and bool(serena_local.get("available_and_recommended"))
    return standard_result(
        status="ok" if ready else "degraded",
        available=str(serena_local.get("health_status", "")) == "ok",
        recommended=ready,
        blocking_reason="" if ready else (result.stderr or "serena_local_not_recommended"),
        affected_paths=["07_scripts/serena/check_serena_access.py", ".vscode/mcp.json"],
        next_action="none" if ready else "reload_vscode_or_start_serena_http",
        details={
            "transport": serena_local.get("transport"),
            "health_status": serena_local.get("health_status"),
            "available_and_recommended": serena_local.get("available_and_recommended"),
        },
    )


def check_serena_contract() -> dict[str, Any]:
    command = ["python3", "07_scripts/serena/check_serena_multi_host_contract.py", "--json"]
    try:
        result = run_command(command, timeout=60)
    except Exception as exc:
        return standard_result(
            status="unavailable",
            available=False,
            recommended=False,
            blocking_reason=f"serena_contract_exception:{exc}",
            affected_paths=["07_scripts/serena/check_serena_multi_host_contract.py"],
            next_action="repair_serena_contract",
        )
    payload = parse_json_output(result.stdout)
    ok = result.returncode == 0 and payload.get("status") == "ok" and payload.get("configured_tool_count") == 29
    return standard_result(
        status="ok" if ok else "blocked",
        available=bool(payload),
        recommended=ok,
        blocking_reason="" if ok else (result.stderr or "serena_contract_drift"),
        affected_paths=[
            "00_sistema_tesis/config/serena_mcp.json",
            ".vscode/mcp.json",
            "00_sistema_tesis/documentacion_sistema/contrato_serena_mcp_agentes.md",
        ],
        next_action="none" if ok else "sync_serena_contract_docs_and_config",
        details={
            "configured_tool_count": payload.get("configured_tool_count"),
            "missing_config_tools": payload.get("missing_config_tools", []),
            "unexpected_config_tools": payload.get("unexpected_config_tools", []),
        },
    )


def check_mission_control_db(db_path: Path = MISSION_CONTROL_DB) -> dict[str, Any]:
    rel_path = str(db_path.relative_to(ROOT)) if db_path.is_relative_to(ROOT) else str(db_path)
    if not db_path.exists():
        return standard_result(
            status="unavailable",
            available=False,
            recommended=False,
            blocking_reason="mission_control_db_missing",
            affected_paths=[rel_path],
            next_action="restore_or_initialize_mission_control_db",
        )
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        integrity = connection.execute("PRAGMA integrity_check;").fetchone()
        tables = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()
        connection.close()
    except sqlite3.Error as exc:
        return standard_result(
            status="blocked",
            available=True,
            recommended=False,
            blocking_reason=f"sqlite_error:{exc}",
            affected_paths=[rel_path],
            next_action="run_db_maintenance_with_repair_after_backup",
        )
    ok = integrity == ("ok",)
    return standard_result(
        status="ok" if ok else "blocked",
        available=True,
        recommended=ok,
        blocking_reason="" if ok else "pragma_integrity_check_failed",
        affected_paths=[rel_path],
        next_action="none" if ok else "run_db_maintenance_with_repair_after_backup",
        details={"integrity_check": integrity[0] if integrity else "", "table_count": int(tables[0] if tables else 0)},
    )


def inventory_context_residue(*, max_items: int = 80) -> dict[str, Any]:
    roots = [
        ROOT / "config" / "backups",
        ROOT / "04_implementacion" / "control_mission" / ".tmp",
        ROOT / "07_scripts" / "ops",
        ROOT / "runtime" / "pc_control" / "benchmarks",
    ]
    patterns = ("*.bak", "*.log", "tmp_*", "*.tmp", "*.db-wal", "*.db-shm")
    items: list[dict[str, Any]] = []
    for base in roots:
        if not base.exists():
            continue
        for pattern in patterns:
            for path in sorted(base.glob(pattern)):
                if len(items) >= max_items:
                    break
                if path.is_file():
                    rel = path.relative_to(ROOT).as_posix()
                    items.append({"path": rel, "size_bytes": path.stat().st_size})
            if len(items) >= max_items:
                break
    for path in sorted(ROOT.glob("*.log")):
        if len(items) >= max_items:
            break
        if path.is_file():
            items.append({"path": path.relative_to(ROOT).as_posix(), "size_bytes": path.stat().st_size})
    return standard_result(
        status="ok",
        available=True,
        recommended=True,
        affected_paths=[item["path"] for item in items[:20]],
        next_action="review_inventory_before_delete" if items else "none",
        details={
            "mode": "dry_run",
            "candidate_count_reported": len(items),
            "truncated": len(items) >= max_items,
            "candidates": items,
        },
    )


def validate_spec_file(path: Path = SPEC_PATH) -> dict[str, Any]:
    rel_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    if not path.exists():
        return standard_result(
            status="blocked",
            available=False,
            recommended=False,
            blocking_reason="spec_missing",
            affected_paths=[rel_path],
            next_action="create_agent_ops_core_spec",
        )
    text = path.read_text(encoding="utf-8")
    missing = [term for term in REQUIRED_SPEC_TERMS if term not in text]
    ok = not missing
    step_pending = 'step_id: "PENDIENTE"' in text or "Step ID humano" in text
    return standard_result(
        status="ok" if ok else "blocked",
        available=True,
        recommended=ok,
        blocking_reason="" if ok else "spec_required_terms_missing",
        affected_paths=[rel_path],
        required_step_id="PENDIENTE" if step_pending else "",
        next_action="none" if ok else "complete_spec_required_terms",
        details={"missing_terms": missing, "step_pending": step_pending},
    )


def traceability_gate(step_id: str) -> dict[str, Any]:
    if step_id.strip():
        return standard_result(
            status="ok",
            available=True,
            recommended=True,
            required_step_id=step_id.strip(),
            next_action="register_ledger_matrix_after_changes",
        )
    return standard_result(
        status="degraded",
        available=True,
        recommended=False,
        blocking_reason="missing_human_step_id_for_canonical_closeout",
        affected_paths=[
            "00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md",
            "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
        ],
        required_step_id="PENDIENTE",
        next_action="request_human_step_id_before_canonical_validation",
    )


def check_test_impact() -> dict[str, Any]:
    command = ["python3", "07_scripts/ops/test_impact_gate.py", "--json"]
    try:
        result = run_command(command, timeout=60)
    except Exception as exc:
        return standard_result(
            status="unavailable",
            available=False,
            recommended=False,
            blocking_reason=f"test_impact_gate_exception:{exc}",
            affected_paths=["07_scripts/ops/test_impact_gate.py"],
            next_action="repair_test_impact_gate",
        )
    payload = parse_json_output(result.stdout)
    ok = result.returncode == 0 and bool(payload)
    integration = list(payload.get("integration_commands_require_justification", [])) if payload else []
    return standard_result(
        status="degraded" if integration else ("ok" if ok else "blocked"),
        available=ok,
        recommended=ok and not integration,
        blocking_reason="" if ok else (result.stderr or "test_impact_gate_failed"),
        affected_paths=["07_scripts/ops/test_impact_gate.py", "00_sistema_tesis/bitacora/audit_history/test_impact_history.jsonl"],
        next_action="review_integration_justification_before_running" if integration else ("none" if ok else "repair_test_impact_gate"),
        details={
            "changed_path_count": len(payload.get("changed_paths", [])) if payload else 0,
            "selected_command_ids": [item.get("id") for item in payload.get("selected_commands", [])] if payload else [],
            "redundancy_hint": payload.get("redundancy_hint") if payload else "",
            "integration_commands_require_justification": integration,
        },
    )


def check_human_validation(step_id: str) -> dict[str, Any]:
    command = ["python3", "07_scripts/ops/human_validation_gate.py", "--json"]
    if step_id.strip():
        command.extend(["--step-id", step_id.strip()])
    try:
        result = run_command(command, timeout=30)
    except Exception as exc:
        return standard_result(
            status="unavailable",
            available=False,
            recommended=False,
            blocking_reason=f"human_validation_gate_exception:{exc}",
            affected_paths=["07_scripts/ops/human_validation_gate.py"],
            next_action="repair_human_validation_gate",
        )
    payload = parse_json_output(result.stdout)
    if not payload:
        return standard_result(
            status="blocked",
            available=False,
            recommended=False,
            blocking_reason=result.stderr or "human_validation_gate_failed",
            affected_paths=["07_scripts/ops/human_validation_gate.py"],
            next_action="repair_human_validation_gate",
        )
    return standard_result(
        status=str(payload.get("status", "blocked")),
        available=bool(payload.get("available")),
        recommended=bool(payload.get("recommended")),
        blocking_reason=str(payload.get("blocking_reason", "")),
        affected_paths=list(payload.get("affected_paths", [])),
        required_step_id=str(payload.get("required_step_id", "")),
        next_action=str(payload.get("next_action", "none")),
        details=dict(payload.get("details", {})),
    )


def build_report(*, step_id: str = "", max_residue_items: int = 80, live: bool = True) -> dict[str, Any]:
    checks = {
        "spec": validate_spec_file(),
        "external_mcp_contracts": standard_result(
            status="ok",
            available=True,
            recommended=True,
            details={"contracts": EXTERNAL_MCP_CONTRACTS},
        ),
        "context_residue_inventory": inventory_context_residue(max_items=max_residue_items),
        "mission_control_db": check_mission_control_db(),
        "test_impact": check_test_impact(),
        "human_validation": check_human_validation(step_id),
        "traceability": traceability_gate(step_id),
    }
    if live:
        checks.update(
            {
                "agent_context_tools": check_agent_context_tools(),
                "serena_access": check_serena_access(),
                "serena_contract": check_serena_contract(),
            }
        )
    blocking = [name for name, item in checks.items() if item["status"] in {"blocked", "unavailable"}]
    degraded = [name for name, item in checks.items() if item["status"] == "degraded"]
    status = "blocked" if blocking else ("degraded" if degraded else "ok")
    return {
        "status": status,
        "repo_root": str(ROOT),
        "spec_path": str(SPEC_PATH.relative_to(ROOT)),
        "standard_keys": list(STANDARD_KEYS),
        "checks": checks,
        "summary": {
            "blocking_checks": blocking,
            "degraded_checks": degraded,
            "build_all_gate": "run_after_implementation_and_traceability",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate sistemico Agent Ops Core para agentes agnosticos.")
    parser.add_argument("--json", action="store_true", help="Emitir JSON.")
    parser.add_argument("--step-id", default="", help="Step ID humano para cierre canonico, si existe.")
    parser.add_argument("--max-residue-items", type=int, default=80)
    parser.add_argument("--no-live", action="store_true", help="No ejecuta checks live de Serena/Caveman.")
    args = parser.parse_args()

    report = build_report(
        step_id=args.step_id,
        max_residue_items=max(args.max_residue_items, 1),
        live=not args.no_live,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"AGENT OPS CORE: {report['status']}")
        for name, check in report["checks"].items():
            print(f"- {name}: {check['status']} next={check['next_action']}")
    return 0 if report["status"] in {"ok", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
