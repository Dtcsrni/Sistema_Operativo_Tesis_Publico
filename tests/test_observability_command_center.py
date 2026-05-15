from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "07_scripts"))
sys.path.insert(0, str(ROOT / "07_scripts" / "ops"))

from build_dashboard import main as build_dashboard_main  # noqa: E402
from observability_snapshot import build_snapshot  # noqa: E402


def test_observability_snapshot_models_compose_and_governed_control() -> None:
    snapshot = build_snapshot(public=False)

    assert snapshot["schema_version"] == "siot-observability-dashboard-v1"
    assert snapshot["access"]["control_mode"] == "governed_request_queue"
    assert snapshot["access"]["executes_actions"] is False
    assert snapshot["control_policy"]["direct_docker_socket"] is False
    assert snapshot["control_policy"]["requires_human_approval_for_mutation"] is True
    assert any(service["id"] == "tablero-gobernanza" for service in snapshot["compose_stack"])
    assert any(service["id"] == "observabilidad-command-center" for service in snapshot["compose_stack"])
    assert snapshot["notification_policy"]["telegram_suppression"] == "suppress_when_dashboard_heartbeat_active"


def test_public_observability_snapshot_is_sanitized() -> None:
    public_snapshot = build_snapshot(public=True)

    assert public_snapshot["mode"] == "public"
    assert public_snapshot["access"]["auth"] == "sanitized_public"
    rendered = json.dumps(public_snapshot, ensure_ascii=False)
    assert "OPENCLAW_GATEWAY_TOKEN" not in rendered
    assert "SIOT_OBSERVABILITY_TOKEN" not in rendered
    assert "http://127.0.0.1" not in rendered
    assert "host.docker.internal" not in rendered


def test_dashboard_renders_distributed_observability_command_center() -> None:
    build_dashboard_main()
    html = (ROOT / "06_dashboard" / "generado" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "06_dashboard" / "generado" / "app.js").read_text(encoding="utf-8")

    assert 'id="observabilidad-distribuida"' in html
    assert "Observabilidad Distribuida SIOT" in html
    assert "Stack Docker Compose" in html
    assert "runtime/observability/control_requests.jsonl" in html
    assert "data-noc-tab=\"pc\"" in html
    assert "initializeNocTabs" in js


def test_compose_declares_observability_command_center_with_token() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "observabilidad-command-center:" in compose
    assert "SIOT_OBSERVABILITY_TOKEN=${SIOT_OBSERVABILITY_TOKEN:-}" in compose
    assert "./runtime/observability:/app/runtime/observability" in compose
    assert "serve_observability_dashboard.py" in compose
    assert "SIOT_OBSERVABILITY_TOKEN=change-me-local-only" in env_example
