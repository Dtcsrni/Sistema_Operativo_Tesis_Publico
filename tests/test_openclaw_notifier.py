from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "runtime" / "openclaw"

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from openclaw_local import notifier  # noqa: E402


def test_ready_notification_separates_base_runtime_from_chat_provider(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4")

    captured: dict[str, str] = {}

    def fake_send_telegram_message(*, bot_token: str, chat_id: str, text: str, timeout_seconds: int):
        captured["bot_token"] = bot_token
        captured["chat_id"] = chat_id
        captured["text"] = text
        return True, "sent"

    monkeypatch.setattr(notifier, "send_telegram_message", fake_send_telegram_message)

    result = notifier.dispatch_ready_notification(
        host="127.0.0.1",
        port=18789,
        runtime_status={"state": "npu_experimental_ready", "active_runtime": "ollama_local"},
    )

    assert result["status"] == "sent"
    assert captured["bot_token"] == "token"
    assert captured["chat_id"] == "123"
    assert "Runtime base: ollama_local" in captured["text"]
    assert "Chat: web_session model=gpt-5.4" in captured["text"]