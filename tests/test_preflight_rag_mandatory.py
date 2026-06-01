from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "07_scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "07_scripts"))

import preflight_rag_mandatory as preflight  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "", json_payload: dict | None = None):
        self.status_code = status_code
        self.text = text
        self._json_payload = json_payload or {}

    def json(self):
        return self._json_payload


def test_run_preflight_reports_schema_missing_when_graphql_lacks_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    import pytest

    monkeypatch.setattr(preflight.requests, "get", lambda *args, **kwargs: _FakeResponse(200, json_payload={"version": "1.31.4"}))
    monkeypatch.setattr(
        preflight.requests,
        "post",
        lambda *args, **kwargs: _FakeResponse(
            422,
            text='{"error":[{"message":"no graphql provider present, this is most likely because no schema is present. Import a schema first!"}]}'
        ),
    )

    result = preflight.run_preflight(task_id="TEST-1", question="prueba", requires_rag=True)

    assert result["preflight_ok"] is False
    assert result["status"] == "RAG_SCHEMA_MISSING"
    assert result["chunks_recovered"] == 0
