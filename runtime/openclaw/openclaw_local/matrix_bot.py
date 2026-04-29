from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request
from uuid import uuid4

from .session_layer import process_channel_text
from .storage import OpenClawStore
from .telegram_bot import dispatch_command


def matrix_configured() -> bool:
    return bool(
        os.getenv("OPENCLAW_MATRIX_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        and os.getenv("OPENCLAW_MATRIX_HOMESERVER", "").strip()
        and os.getenv("OPENCLAW_MATRIX_ACCESS_TOKEN", "").strip()
    )


def _matrix_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {os.getenv('OPENCLAW_MATRIX_ACCESS_TOKEN', '').strip()}",
        "Content-Type": "application/json",
    }


def _matrix_rooms() -> set[str]:
    raw = os.getenv("OPENCLAW_MATRIX_ROOM_IDS", "").replace(";", ",")
    return {item.strip() for item in raw.split(",") if item.strip()}


def _matrix_timeout_ms() -> int:
    try:
        value = int(os.getenv("OPENCLAW_MATRIX_POLL_TIMEOUT_MS", "15000").strip())
    except ValueError:
        value = 15000
    return max(1000, min(value, 60000))


def _matrix_user_id() -> str:
    return os.getenv("OPENCLAW_MATRIX_USER_ID", "").strip()


def _matrix_sync_url(since: str = "") -> str:
    base = os.getenv("OPENCLAW_MATRIX_HOMESERVER", "").rstrip("/")
    params = {"timeout": str(_matrix_timeout_ms())}
    if since:
        params["since"] = since
    return f"{base}/_matrix/client/v3/sync?{parse.urlencode(params)}"


def matrix_send_message(room_id: str, text: str) -> dict[str, Any]:
    if not matrix_configured():
        return {"status": "skipped", "reason": "matrix_not_configured"}
    base = os.getenv("OPENCLAW_MATRIX_HOMESERVER", "").rstrip("/")
    txn_id = f"ocm-{uuid4().hex}"
    url = f"{base}/_matrix/client/v3/rooms/{parse.quote(room_id, safe='')}/send/m.room.message/{txn_id}"
    payload = json.dumps({"msgtype": "m.text", "body": text[:4000]}, ensure_ascii=False).encode("utf-8")
    req = request.Request(url, data=payload, method="PUT")
    for key, value in _matrix_headers().items():
        req.add_header(key, value)
    try:
        with request.urlopen(req, timeout=max(5, _matrix_timeout_ms() // 1000)) as response:
            raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
    except (error.URLError, error.HTTPError, json.JSONDecodeError, OSError) as exc:
        return {"status": "error", "detail": f"{type(exc).__name__}:{exc}"}
    return {"status": "sent", "event_id": data.get("event_id", "")}


def matrix_fetch_sync(*, since: str = "") -> dict[str, Any]:
    if not matrix_configured():
        return {"status": "skipped", "reason": "matrix_not_configured"}
    req = request.Request(_matrix_sync_url(since))
    for key, value in _matrix_headers().items():
        req.add_header(key, value)
    try:
        with request.urlopen(req, timeout=max(5, _matrix_timeout_ms() // 1000 + 5)) as response:
            raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
    except (error.URLError, error.HTTPError, json.JSONDecodeError, OSError) as exc:
        return {"status": "error", "detail": f"{type(exc).__name__}:{exc}"}
    return {"status": "ok", "payload": data}


def process_matrix_event(event: dict[str, Any], *, room_id: str, repo_root: Path, store: OpenClawStore) -> dict[str, Any]:
    sender = str(event.get("sender", "")).strip()
    if sender == _matrix_user_id():
        return {"status": "ignored", "reason": "self_event"}
    text = str((event.get("content") or {}).get("body", "")).strip()
    if not text:
        return {"status": "ignored", "reason": "empty_body"}
    result = process_channel_text(
        store=store,
        repo_root=repo_root,
        channel="matrix",
        peer_id=room_id,
        text=text,
        dispatcher=lambda command, argument: dispatch_command(command, argument, repo_root=repo_root, store=store, chat_id=f"matrix:{room_id}"),
        operator_identity=sender or room_id,
    )
    response = dict(result["response"])
    outbound = str(response.get("text", "")).strip()
    if outbound:
        delivery = matrix_send_message(room_id, outbound)
    else:
        delivery = {"status": "skipped", "reason": "empty_response"}
    return {
        "status": response.get("status", "ok"),
        "session_id": result["session"]["session_id"],
        "delivery": delivery,
        "response": response,
    }


def poll_matrix_once(*, repo_root: Path, store: OpenClawStore) -> dict[str, Any]:
    if not matrix_configured():
        return {"status": "skipped", "reason": "matrix_not_configured"}
    state = store.get_cached_context("matrix:next_batch") or {}
    sync = matrix_fetch_sync(since=str(state.get("value", "")).strip())
    if sync.get("status") != "ok":
        return sync
    payload = sync["payload"]
    next_batch = str(payload.get("next_batch", "")).strip()
    if next_batch:
        store.cache_context("matrix:next_batch", {"value": next_batch})
    allowed_rooms = _matrix_rooms()
    processed = 0
    for room_id, room_payload in (payload.get("rooms", {}) or {}).get("join", {}).items():
        if allowed_rooms and room_id not in allowed_rooms:
            continue
        for event in ((room_payload.get("timeline") or {}).get("events") or []):
            if str(event.get("type", "")) != "m.room.message":
                continue
            process_matrix_event(event, room_id=room_id, repo_root=repo_root, store=store)
            processed += 1
    return {"status": "ok", "processed": processed, "next_batch": next_batch}


def run_matrix_loop(*, repo_root: Path, store: OpenClawStore, interval_seconds: int = 2) -> None:
    while True:
        try:
            poll_matrix_once(repo_root=repo_root, store=store)
        except Exception as exc:  # noqa: BLE001
            print(f"[DEBUG] matrix_loop_error:{exc}", flush=True)
        time.sleep(max(0.1, interval_seconds))
