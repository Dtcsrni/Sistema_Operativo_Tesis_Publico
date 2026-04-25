from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "runtime" / "openclaw"

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from openclaw_local.serena_adapter import REQUIRED_TOOLS, SerenaClient  # noqa: E402


def test_serena_adapter_healthcheck_works_over_stdio(monkeypatch) -> None:
    monkeypatch.delenv("OPENCLAW_SERENA_URL", raising=False)
    monkeypatch.setenv("OPENCLAW_SERENA_TRANSPORT", "stdio")
    client = SerenaClient.from_repo(ROOT)

    payload = client.healthcheck()

    assert payload["status"] == "ok"
    assert payload["transport"] == "stdio"
    assert REQUIRED_TOOLS.issubset(set(payload["tool_names"]))


def test_serena_adapter_fetch_compact_returns_references(monkeypatch) -> None:
    monkeypatch.delenv("OPENCLAW_SERENA_URL", raising=False)
    monkeypatch.setenv("OPENCLAW_SERENA_TRANSPORT", "stdio")
    client = SerenaClient.from_repo(ROOT)

    payload = client.fetch_compact(
        query="DEC-0022",
        paths=["00_sistema_tesis/decisiones/2026-04-08_DEC-0022_arquitectura_operativa_escritorio_primario_y_orange_pi_edge.md"],
        limit=3,
        context_lines=1,
    )

    assert payload["status"] == "ok"
    assert payload["references"]
    assert payload["matches"][0]["path"].endswith("DEC-0022_arquitectura_operativa_escritorio_primario_y_orange_pi_edge.md")


def test_serena_adapter_reports_unavailable_http_transport(monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_SERENA_TRANSPORT", "http")
    monkeypatch.setenv("OPENCLAW_SERENA_URL", "http://127.0.0.1:9/mcp")
    monkeypatch.setenv("OPENCLAW_SERENA_TIMEOUT_MS", "300")
    client = SerenaClient.from_repo(ROOT)

    payload = client.healthcheck()

    assert payload["status"] == "unavailable"
    assert payload["transport"] == "http"


def test_serena_adapter_healthcheck_detects_missing_tools(monkeypatch) -> None:
    monkeypatch.delenv("OPENCLAW_SERENA_URL", raising=False)
    monkeypatch.setenv("OPENCLAW_SERENA_TRANSPORT", "stdio")
    client = SerenaClient.from_repo(ROOT)

    def _fake_sequence(_: list[tuple[str, dict]]) -> dict:
        return {
            "server": {"name": "serena-local", "version": "1.0.0"},
            "protocol_version": "2025-03-26",
            "tool_names": ["context_fetch_compact"],
            "calls": [],
        }

    monkeypatch.setattr(client, "_run_sequence", _fake_sequence)

    payload = client.healthcheck()

    assert payload["status"] == "degraded"
    assert "governance.preflight" in payload["missing_tools"]


def test_serena_adapter_healthcheck_accepts_legacy_tool_aliases(monkeypatch) -> None:
    monkeypatch.delenv("OPENCLAW_SERENA_URL", raising=False)
    monkeypatch.setenv("OPENCLAW_SERENA_TRANSPORT", "stdio")
    client = SerenaClient.from_repo(ROOT)

    def _fake_sequence(_: list[tuple[str, dict]]) -> dict:
        return {
            "server": {"name": "serena-local", "version": "1.0.0"},
            "protocol_version": "2025-03-26",
            "tool_names": sorted(
                {
                    "context_fetch_compact",
                    "context_repo_map",
                    "context_fetch_changes",
                    "context_trace_lookup",
                    "context_session_brief",
                    "governance_preflight",
                    "artifacts_evaluate_serena",
                    "artifacts_write_derived",
                    "canon_prepare_change",
                    "canon_apply_controlled_change",
                    "trace_append_operation",
                }
            ),
            "calls": [],
        }

    monkeypatch.setattr(client, "_run_sequence", _fake_sequence)

    payload = client.healthcheck()

    assert payload["status"] == "ok"
    assert payload["missing_tools"] == []
