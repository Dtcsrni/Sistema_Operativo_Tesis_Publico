from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import argparse
import json

from typing import Any

from common import ROOT
from utils.data_io import load_structured_path

EXPECTED_TOOLS = [
    "context.fetch_compact",
    "context.repo_map",
    "context.fetch_changes",
    "context.trace_lookup",
    "context.session_brief",
    "context.search_ranked",
    "context.file_digest",
    "context.symbol_index",
    "context.dependency_map",
    "context.related_paths",
    "context.bundle",
    "context.change_impact",
    "context.todo_scan",
    "memory.lookup",
    "memory.session_recap",
    "memory.derived_index",
    "memory.evidence_digest",
    "governance.preflight",
    "governance.step_status",
    "governance.trace_gap_scan",
    "governance.protected_path_check",
    "artifacts.evaluate_serena",
    "artifacts.write_derived",
    "artifacts.write_memory_derived",
    "canon.prepare_change",
    "canon.apply_controlled_change",
    "canon.prepare_multi_change",
    "canon.apply_multi_change",
    "trace.append_operation",
]

def public_name(tool_name: str) -> str:
    return tool_name.replace(".", "_")

def _load_json(relative_path: str, root: Path) -> dict[str, Any]:
    path = root / relative_path
    if not path.exists():
        return {}
    payload = load_structured_path(path)
    return payload if isinstance(payload, dict) else {}

def _doc_contains(relative_path: str, root: Path, needle: str) -> bool:
    path = root / relative_path
    return path.exists() and needle in path.read_text(encoding="utf-8")

def build_report(root: Path = ROOT) -> dict[str, Any]:
    config = _load_json("00_sistema_tesis/config/serena_mcp.json", root)
    workspace = _load_json(".vscode/mcp.json", root)
    host_template = _load_json("docs/03_operacion/serena-mcp-host-template.json", root)
    bridge_template = _load_json("docs/03_operacion/serena-bridge-external-template.json", root)

    configured_tools = sorted(str(name) for name in dict(config.get("tools", {})).keys())
    expected_sorted = sorted(EXPECTED_TOOLS)
    missing_config_tools = sorted(set(expected_sorted) - set(configured_tools))
    unexpected_config_tools = sorted(set(configured_tools) - set(expected_sorted))

    workspace_servers = dict(workspace.get("servers", {}))
    workspace_serena = dict(workspace_servers.get("serena-local", {}))
    host_servers = dict(host_template.get("servers", {}))
    bridge_servers = dict(bridge_template.get("servers", {}))
    bridge = dict(config.get("bridge", {}))
    bridge_auth = dict(bridge.get("auth", {}))

    doc_path = "00_sistema_tesis/documentacion_sistema/contrato_serena_mcp_agentes.md"
    doc_has_all_tools = all(_doc_contains(doc_path, root, public_name(tool)) for tool in EXPECTED_TOOLS)
    doc_mentions_multi_host = all(
        _doc_contains(doc_path, root, needle)
        for needle in ("Codex", "OpenClaw", "Copilot", "Antigravity", "Cursor", "JetBrains")
    )

    checks = {
        "tool_count_29": len(configured_tools) == 29,
        "all_expected_tools_configured": not missing_config_tools and not unexpected_config_tools,
        "workspace_publishes_http_serena_local": workspace_serena.get("type") == "http" and workspace_serena.get("url") == "http://127.0.0.1:8765/mcp",
        "host_template_has_http_profile": "serena-local" in host_servers and dict(host_servers.get("serena-local", {})).get("type") == "http",
        "host_template_has_stdio_diagnostic_profile": "serena-local-py" in host_servers and dict(host_servers.get("serena-local-py", {})).get("type") == "stdio",
        "bridge_template_has_auth_header": "Authorization" in dict(dict(bridge_servers.get("serena-local-bridge", {})).get("headers", {})),
        "bridge_config_auth_enabled": bool(bridge_auth.get("enabled", False)) and str(bridge_auth.get("env_var", "")) == "SERENA_BRIDGE_BEARER_TOKEN",
        "contract_doc_lists_29_tools": doc_has_all_tools,
        "contract_doc_mentions_multi_host_targets": doc_mentions_multi_host,
    }
    status = "ok" if all(checks.values()) else "degraded"
    return {
        "repo_root": str(root),
        "status": status,
        "expected_tools": EXPECTED_TOOLS,
        "public_tool_names": [public_name(tool) for tool in EXPECTED_TOOLS],
        "configured_tool_count": len(configured_tools),
        "missing_config_tools": missing_config_tools,
        "unexpected_config_tools": unexpected_config_tools,
        "workspace_server": workspace_serena,
        "bridge": {
            "enabled": bool(bridge.get("enabled", False)),
            "auth_enabled": bool(bridge_auth.get("enabled", False)),
            "env_var": str(bridge_auth.get("env_var", "")),
            "endpoint": str(bridge.get("endpoint", "")),
        },
        "checks": checks,
    }

def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"SERENA MULTI-HOST: {report['status']}",
        f"- tools: {report['configured_tool_count']}/29",
        f"- workspace HTTP: {report['checks']['workspace_publishes_http_serena_local']}",
        f"- host template: {report['checks']['host_template_has_http_profile']}",
        f"- bridge auth: {report['checks']['bridge_config_auth_enabled']}",
        f"- contract doc: {report['checks']['contract_doc_lists_29_tools']}",
    ]
    if report["missing_config_tools"]:
        lines.append(f"- missing: {', '.join(report['missing_config_tools'])}")
    if report["unexpected_config_tools"]:
        lines.append(f"- unexpected: {', '.join(report['unexpected_config_tools'])}")
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica contrato multi-host de Serena MCP.")
    parser.add_argument("--json", action="store_true", help="Emitir JSON.")
    args = parser.parse_args()
    report = build_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report["status"] == "ok" else 1

if __name__ == "__main__":
    raise SystemExit(main())
