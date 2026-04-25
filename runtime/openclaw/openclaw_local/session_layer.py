from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .contracts import SessionEnvelope, SessionMessage
from .policies import load_provider_registry
from .runtime_status import probe_runtime_status
from .storage import OpenClawStore


DispatchHandler = Callable[[str, str], dict[str, Any]]


def parse_channel_command(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    if not cleaned:
        return "chat", ""
    if not cleaned.startswith("/"):
        return "chat", cleaned
    head, _, tail = cleaned.partition(" ")
    command = head.split("@", 1)[0].lstrip("/").strip().lower()
    if command == "investigar":
        command = "investiga"
    return command or "chat", tail.strip()


def session_defaults() -> dict[str, Any]:
    return {
        "target_node": os.getenv("OPENCLAW_DEFAULT_TARGET_NODE", "auto").strip() or "auto",
        "provider_policy": os.getenv("OPENCLAW_PROVIDER_POLICY", "hybrid_controlled").strip() or "hybrid_controlled",
        "premium_auto": _env_flag("OPENCLAW_PREMIUM_AUTO", default=False),
    }


def ensure_channel_session(
    *,
    store: OpenClawStore,
    channel: str,
    peer_id: str,
    operator_identity: str,
    title_hint: str,
) -> dict[str, Any]:
    cache_key = f"session:active:{channel}:{peer_id}"
    cached = store.get_cached_context(cache_key) or {}
    if cached.get("session_id"):
        session = store.get_session(str(cached["session_id"]))
        if session is not None:
            return session

    now = datetime.now(UTC).isoformat()
    defaults = session_defaults()
    session = SessionEnvelope(
        session_id=f"OCS-{uuid4().hex[:12]}",
        channel=channel,
        peer_id=peer_id,
        operator_identity=operator_identity or peer_id,
        target_node=str(defaults["target_node"]),
        provider_policy=str(defaults["provider_policy"]),
        premium_auto=bool(defaults["premium_auto"]),
        status="active",
        title=title_hint[:120] or f"{channel}:{peer_id}",
        task_profile="interactive",
        payload={"created_from": channel},
        created_at=now,
        updated_at=now,
    )
    store.save_session(session)
    store.cache_context(cache_key, {"session_id": session.session_id, "updated_at": now})
    return session.to_dict()


def touch_session(
    *,
    store: OpenClawStore,
    session: dict[str, Any],
    title_hint: str = "",
    payload_update: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = dict(session.get("payload") or {})
    if payload_update:
        payload.update(payload_update)
    updated = SessionEnvelope(
        session_id=str(session["session_id"]),
        channel=str(session["channel"]),
        peer_id=str(session["peer_id"]),
        operator_identity=str(session.get("operator_identity", session.get("peer_id", ""))),
        target_node=str(session.get("target_node", "auto")),
        provider_policy=str(session.get("provider_policy", "hybrid_controlled")),
        premium_auto=bool(session.get("premium_auto", False)),
        status=str(session.get("status", "active")),
        title=(title_hint[:120] or str(session.get("title", "")) or f"{session['channel']}:{session['peer_id']}"),
        task_profile=str(session.get("task_profile", "interactive")),
        payload=payload,
        created_at=str(session["created_at"]),
        updated_at=datetime.now(UTC).isoformat(),
    )
    store.save_session(updated)
    return updated.to_dict()


def record_session_message(
    *,
    store: OpenClawStore,
    session_id: str,
    direction: str,
    channel: str,
    command: str,
    text: str,
    provider: str,
    model: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message = SessionMessage(
        message_id=f"OCM-{uuid4().hex[:12]}",
        session_id=session_id,
        direction=direction,
        channel=channel,
        command=command,
        text=text,
        provider=provider,
        model=model,
        status=status,
        payload=payload or {},
        created_at=datetime.now(UTC).isoformat(),
    )
    store.save_session_message(message)
    return message.to_dict()


def process_channel_text(
    *,
    store: OpenClawStore,
    repo_root: Path,
    channel: str,
    peer_id: str,
    text: str,
    dispatcher: DispatchHandler,
    operator_identity: str = "",
) -> dict[str, Any]:
    command, argument = parse_channel_command(text)
    session = ensure_channel_session(
        store=store,
        channel=channel,
        peer_id=peer_id,
        operator_identity=operator_identity,
        title_hint=argument or text or f"{channel}:{peer_id}",
    )
    session = touch_session(
        store=store,
        session=session,
        title_hint=argument or text or str(session.get("title", "")),
        payload_update={"last_command": command, "last_text": text[:500]},
    )
    inbound = record_session_message(
        store=store,
        session_id=str(session["session_id"]),
        direction="inbound",
        channel=channel,
        command=command,
        text=text,
        provider="user",
        model="user",
        status="received",
        payload={"argument": argument},
    )
    response = dispatcher(command, argument)
    provider = str(response.get("provider") or response.get("selected_provider") or "openclaw")
    model = str(response.get("model") or response.get("selected_model") or "sin_modelo")
    outbound = record_session_message(
        store=store,
        session_id=str(session["session_id"]),
        direction="outbound",
        channel=channel,
        command=command,
        text=str(response.get("text", "")),
        provider=provider,
        model=model,
        status=str(response.get("status", "ok")),
        payload={"raw_response": response},
    )
    session = touch_session(
        store=store,
        session=session,
        payload_update={
            "last_status": str(response.get("status", "ok")),
            "last_provider": provider,
            "last_model": model,
            "last_message_id": outbound["message_id"],
        },
    )
    return {
        "session": session,
        "inbound": inbound,
        "outbound": outbound,
        "response": response,
    }


def build_nodes_summary(repo_root: Path) -> list[dict[str, Any]]:
    runtime = probe_runtime_status(repo_root)
    desktop_base = os.getenv("OPENCLAW_DESKTOP_RUNTIME_BASE_URL", os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434")).strip()
    edge_base = os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip()
    edge_runtime = "ollama_local" if runtime.get("ollama", {}).get("ready") else "local"
    matrix_base = os.getenv("OPENCLAW_MATRIX_HOMESERVER", "http://127.0.0.1:6167").strip()
    matrix_enabled = _env_flag("OPENCLAW_MATRIX_ENABLED", default=False) and bool(
        os.getenv("OPENCLAW_MATRIX_HOMESERVER", "").strip() and os.getenv("OPENCLAW_MATRIX_ACCESS_TOKEN", "").strip()
    )
    return [
        {
            "id": "desktop",
            "role": "control_plane_heavy",
            "runtime": os.getenv("OPENCLAW_DESKTOP_RUNTIME", "llamacpp").strip() or "llamacpp",
            "base_url": desktop_base,
            "native_host": os.getenv("OPENCLAW_DESKTOP_NATIVE_HOST", "windows").strip() or "windows",
            "enabled": _env_flag("OPENCLAW_DESKTOP_COMPUTE_ENABLED", default=True),
        },
        {
            "id": "edge",
            "role": os.getenv("OPENCLAW_EDGE_ROLE", "relay_light_runtime").strip() or "relay_light_runtime",
            "runtime": edge_runtime,
            "base_url": edge_base,
            "enabled": True,
        },
        {
            "id": "matrix",
            "role": os.getenv("OPENCLAW_MATRIX_ROLE", "remote_control_plane").strip() or "remote_control_plane",
            "runtime": "matrix_bot" if matrix_enabled else "unconfigured",
            "base_url": matrix_base,
            "enabled": matrix_enabled,
        },
    ]


def build_provider_summary(repo_root: Path) -> list[dict[str, Any]]:
    providers = load_provider_registry(repo_root).get("providers", [])
    return [
        {
            "id": str(item.get("id", "")),
            "mode": str(item.get("mode", "")),
            "session_mode": str(item.get("session_mode", "")),
            "model_class": str(item.get("model_class", "")),
        }
        for item in providers
    ]


def _env_flag(name: str, *, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "si", "sí"}
