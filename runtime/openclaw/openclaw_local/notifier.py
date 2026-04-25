from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, parse, request

from .matrix_bot import matrix_configured, matrix_send_message


def _env_enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def _telegram_config_from_env() -> dict[str, str] | None:
    if not _env_enabled("OPENCLAW_TELEGRAM_ENABLED", False):
        return None
    bot_token = os.getenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        return None
    return {"bot_token": bot_token, "chat_id": chat_id}


def _telegram_timeout_seconds() -> int:
    raw = os.getenv("OPENCLAW_TELEGRAM_TIMEOUT_SECONDS", "10").strip()
    try:
        value = int(raw)
    except ValueError:
        return 10
    return max(1, min(value, 60))


def send_telegram_message(
    *,
    bot_token: str,
    chat_id: str,
    text: str,
    timeout_seconds: int,
) -> tuple[bool, str]:
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    req = request.Request(endpoint, data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except error.URLError as exc:
        return False, f"telegram_request_failed:{exc}"

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return False, "telegram_response_not_json"

    if not data.get("ok", False):
        return False, f"telegram_api_error:{data.get('description', 'unknown')}"
    return True, "sent"


def dispatch_ready_notification(*, host: str, port: int, runtime_status: dict[str, Any]) -> dict[str, Any]:
    if not _env_enabled("OPENCLAW_TELEGRAM_READY_ON_START", True) and not _env_enabled("OPENCLAW_MATRIX_READY_ON_START", True):
        return {"status": "skipped", "reason": "ready_notification_disabled"}

    import time as _time
    cooldown_seconds = int(os.getenv("OPENCLAW_TELEGRAM_READY_COOLDOWN_SECONDS", "120").strip() or "120")
    state_dir = os.getenv("EDGE_IOT_STATE_DIR", "").strip()
    cooldown_file: str | None = None
    if state_dir:
        cooldown_file = os.path.join(state_dir, "last_ready_notification.txt")
    if cooldown_file:
        try:
            with open(cooldown_file, "r", encoding="utf-8") as fh:
                last_ts = float(fh.read().strip())
            if (_time.time() - last_ts) < cooldown_seconds:
                return {"status": "skipped", "reason": f"cooldown_activo:{int(cooldown_seconds - (_time.time() - last_ts))}s_restantes"}
        except (OSError, ValueError):
            pass  # archivo no existe o malformado → enviar normalmente

    state = str(runtime_status.get("state", "unknown"))
    active_runtime = str(runtime_status.get("active_runtime", "unknown"))
    chat_provider = os.getenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session").strip() or "web_session"
    chat_model = os.getenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4").strip() or "gpt-5.4"
    text = os.getenv(
        "OPENCLAW_TELEGRAM_READY_MESSAGE",
        "OpenClaw listo para ordenes.",
    ).strip()
    suffix = f"\nHost: {host}:{port}\nEstado: {state}\nRuntime base: {active_runtime}\nChat: {chat_provider} model={chat_model}"
    details: dict[str, Any] = {}
    ok = False
    channel = "telegram"

    if _env_enabled("OPENCLAW_MATRIX_READY_ON_START", True) and matrix_configured():
        room_id = os.getenv("OPENCLAW_MATRIX_READY_ROOM_ID", "").strip()
        if room_id:
            matrix_result = matrix_send_message(room_id, f"{text}{suffix}")
            details["matrix"] = matrix_result
            ok = ok or matrix_result.get("status") == "sent"
            channel = "matrix+telegram"

    cfg = _telegram_config_from_env()
    if _env_enabled("OPENCLAW_TELEGRAM_READY_ON_START", True) and cfg is not None:
        tg_ok, detail = send_telegram_message(
            bot_token=cfg["bot_token"],
            chat_id=cfg["chat_id"],
            text=f"{text}{suffix}",
            timeout_seconds=_telegram_timeout_seconds(),
        )
        details["telegram"] = {"status": "sent" if tg_ok else "error", "detail": detail}
        ok = ok or tg_ok

    # Guardar timestamp solo si el envío tuvo éxito
    if ok and cooldown_file:
        try:
            with open(cooldown_file, "w", encoding="utf-8") as fh:
                fh.write(str(_time.time()))
        except OSError:
            pass

    return {
        "status": "sent" if ok else "error",
        "channel": channel,
        "detail": details,
        "host": host,
        "port": port,
    }



def dispatch_test_notification(*, message: str) -> dict[str, Any]:
    details: dict[str, Any] = {}
    sent = False
    channel = "telegram"

    if matrix_configured():
        room_id = os.getenv("OPENCLAW_MATRIX_READY_ROOM_ID", "").strip()
        if room_id:
            result = matrix_send_message(room_id, message)
            details["matrix"] = result
            sent = sent or result.get("status") == "sent"
            channel = "matrix+telegram"

    cfg = _telegram_config_from_env()
    if cfg is not None:
        ok, detail = send_telegram_message(
            bot_token=cfg["bot_token"],
            chat_id=cfg["chat_id"],
            text=message,
            timeout_seconds=_telegram_timeout_seconds(),
        )
        details["telegram"] = {"status": "sent" if ok else "error", "detail": detail}
        sent = sent or ok

    if not details:
        return {"status": "skipped", "reason": "no_notification_channels_configured", "channel": "telegram"}
    return {
        "status": "sent" if sent else "error",
        "channel": channel,
        "detail": details,
    }
