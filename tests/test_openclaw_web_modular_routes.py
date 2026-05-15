from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_OPENCLAW = ROOT / "runtime" / "openclaw"

if str(RUNTIME_OPENCLAW) not in sys.path:
    sys.path.insert(0, str(RUNTIME_OPENCLAW))

from openclaw_local.web_modular import create_app


class _StubStore:
    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, object]] = {}

    def audit_summary(self):
        return {
            "tasks": 0,
            "pending_approvals": 0,
            "evidence_records": 0,
            "academic_packets": 0,
            "source_records": 0,
        }

    def list_approvals(self, status=None):
        return []

    def get_runtime_status(self):
        return {"state": "ok"}

    def get_host_info(self):
        return {"name": "test-host"}

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    def save_session(self, session):
        data = session.to_dict()
        self.sessions[data["session_id"]] = data


def _build_app() -> TestClient:
    store = _StubStore()
    app = create_app(store=store, repo_root=ROOT, provider_registry={"providers": []})
    return TestClient(app)


def test_chat_compatibility_get_returns_helpful_payload() -> None:
    client = _build_app()

    response = client.get("/chat", params={"session": "agent:main:dashboard:test"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["route"] == "/chat"
    assert data["session"]["session_id"] == "agent:main:dashboard:test"
    assert "accepted_fields" in data


def test_health_endpoint_returns_ok() -> None:
    client = _build_app()

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "openclaw-gateway"


def test_chat_compatibility_post_delegates_to_service(monkeypatch) -> None:
    client = _build_app()

    def fake_send_session_message(session_key: str, text: str, operator_identity: str = "web", *, channel: str = "web", execution_profile: str = "", progress_callback=None):
        return {
            "session_key": session_key,
            "text": text,
            "operator_identity": operator_identity,
            "channel": channel,
        }

    monkeypatch.setattr(client.app.state.service, "send_session_message", fake_send_session_message)

    response = client.post("/chat", json={"session": "agent:main:dashboard:test", "text": "Hola"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["route"] == "/chat"
    assert data["result"]["text"] == "Hola"
