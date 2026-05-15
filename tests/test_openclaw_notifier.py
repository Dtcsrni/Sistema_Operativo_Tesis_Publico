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
    monkeypatch.setenv("OPENCLAW_TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4")
    monkeypatch.setenv("OPENCLAW_DATA_DIR", str(tmp_path / "data"))

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
    assert "Chat: web_session (modelo real se reporta al responder)" in captured["text"]
    assert "model=gpt-5.4" not in captured["text"]


def test_ready_notification_falls_back_to_bot_token_alias(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_TELEGRAM_ENABLED", "1")
    monkeypatch.delenv("OPENCLAW_TELEGRAM_TOKEN", raising=False)
    monkeypatch.setenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "token-bot")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("OPENCLAW_DATA_DIR", str(tmp_path / "data"))

    captured: dict[str, str] = {}

    def fake_send_telegram_message(*, bot_token: str, chat_id: str, text: str, timeout_seconds: int):
        captured["bot_token"] = bot_token
        captured["chat_id"] = chat_id
        return True, "sent"

    monkeypatch.setattr(notifier, "send_telegram_message", fake_send_telegram_message)

    result = notifier.dispatch_ready_notification(
        host="127.0.0.1",
        port=18789,
        runtime_status={"state": "ready", "active_runtime": "pc_native_llamacpp"},
    )

    assert result["status"] == "sent"
    assert captured["bot_token"] == "token-bot"
    assert captured["chat_id"] == "123"


def test_ready_notification_cooldown_uses_openclaw_data_dir(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("EDGE_IOT_STATE_DIR", raising=False)
    monkeypatch.delenv("OPENCLAW_READY_STATE_DIR", raising=False)
    monkeypatch.setenv("OPENCLAW_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_ID", "123")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_READY_COOLDOWN_SECONDS", "120")

    sent_messages: list[str] = []

    def fake_send_telegram_message(*, bot_token: str, chat_id: str, text: str, timeout_seconds: int):
        sent_messages.append(text)
        return True, "sent"

    monkeypatch.setattr(notifier, "send_telegram_message", fake_send_telegram_message)

    first = notifier.dispatch_ready_notification(
        host="127.0.0.1",
        port=18789,
        runtime_status={"state": "npu_experimental_ready", "active_runtime": "ollama_local"},
    )
    second = notifier.dispatch_ready_notification(
        host="127.0.0.1",
        port=18789,
        runtime_status={"state": "npu_experimental_ready", "active_runtime": "ollama_local"},
    )

    assert first["status"] == "sent"
    assert second["status"] == "skipped"
    assert str(second["reason"]).startswith("cooldown_activo:")
    assert len(sent_messages) == 1
    assert (tmp_path / "data" / "last_ready_notification.txt").exists()


def test_ready_notification_cooldown_has_tmp_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("EDGE_IOT_STATE_DIR", raising=False)
    monkeypatch.delenv("OPENCLAW_READY_STATE_DIR", raising=False)
    monkeypatch.delenv("OPENCLAW_DATA_DIR", raising=False)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_ID", "123")

    sent_messages: list[str] = []

    def fake_send_telegram_message(*, bot_token: str, chat_id: str, text: str, timeout_seconds: int):
        sent_messages.append(text)
        return True, "sent"

    monkeypatch.setattr(notifier, "send_telegram_message", fake_send_telegram_message)

    first = notifier.dispatch_ready_notification(
        host="127.0.0.1",
        port=18789,
        runtime_status={"state": "ready", "active_runtime": "ollama_local"},
    )
    second = notifier.dispatch_ready_notification(
        host="127.0.0.1",
        port=18789,
        runtime_status={"state": "ready", "active_runtime": "ollama_local"},
    )

    assert first["status"] == "sent"
    assert second["status"] == "skipped"
    assert len(sent_messages) == 1
    assert (tmp_path / "openclaw" / "last_ready_notification.txt").exists()
