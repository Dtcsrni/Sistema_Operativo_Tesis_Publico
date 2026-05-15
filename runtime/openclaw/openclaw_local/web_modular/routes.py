import asyncio
import os
from datetime import UTC, datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
from .service import WebService

router = APIRouter()

def get_service(request: Request) -> WebService:
    return request.app.state.service


def _gateway_expected_token() -> str:
    return os.getenv("OPENCLAW_GATEWAY_TOKEN", "").strip()


async def _send_error(websocket: WebSocket, message_id: str | int | None, code: int, message: str) -> None:
    await websocket.send_json(
        {
            "type": "res",
            "id": message_id,
            "ok": False,
            "error": {"code": code, "message": message},
        }
    )


def _get_param(params: dict[str, object], *keys: str, default: object = "") -> object:
    for key in keys:
        value = params.get(key)
        if value not in (None, ""):
            return value
    return default


async def _handle_rpc(service: WebService, method: str, params: dict[str, object], websocket: WebSocket | None = None) -> object:
    if method == "sessions.list":
        limit = int(_get_param(params, "limit", default=100) or 100)
        return service.list_sessions(limit=limit)

    if method == "sessions.create":
        channel = str(_get_param(params, "channel", default="web") or "web")
        peer = str(_get_param(params, "peer", "peer_id", "session_key", default="") or "")
        return service.create_session(channel, peer or None)

    if method in {"sessions.send", "chat.send"}:
        session_key = str(_get_param(params, "session_key", "sessionKey", "session_id", default="web") or "web")
        text = str(_get_param(params, "content", "message", default="") or "").strip()
        channel = str(_get_param(params, "channel", default="web") or "web").strip() or "web"
        execution_profile = str(_get_param(params, "execution_profile", "executionProfile", default="") or "").strip()
        if not execution_profile and (session_key.startswith("agent:") or "mission-control-" in session_key):
            execution_profile = "mission_control_agent"
            channel = "mission-control"
        if not text:
            raise ValueError("content_required")

        loop = asyncio.get_running_loop()
        def on_progress(*args):
            if len(args) >= 3:
                token_count, delta, stream_type = args[:3]
            elif len(args) == 2:
                token_count, delta = args
                stream_type = "agent"
            elif len(args) == 1:
                token_count = 0
                delta = args[0]
                stream_type = "agent"
            else:
                return

            delta_text = "" if delta is None else str(delta)
            print(f"[DEBUG] on_progress: {token_count} tokens, type={stream_type}, delta_len={len(delta_text)}")
            if websocket:
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({
                        "type": "event",
                        "event": "agent",
                        "payload": {
                            "sessionKey": session_key,
                            "stream": stream_type,
                            "data": delta_text,
                            "ts": datetime.now(UTC).isoformat()
                        }
                    }),
                    loop
                )

        return await run_in_threadpool(
            service.send_session_message,
            session_key,
            text,
            operator_identity="gateway",
            channel=channel,
            execution_profile=execution_profile,
            progress_callback=on_progress
        )

    if method in {"sessions.history", "chat.history"}:
        session_id = str(_get_param(params, "session_id", "sessionKey", default="") or "")
        if not session_id:
            raise ValueError("session_id_required")
        limit = int(_get_param(params, "limit", default=100) or 100)
        return service.list_session_messages(session_id, limit=limit)

    if method == "agents.list":
        return {"requester": "gateway", "allowAny": True, "agents": service.list_agents()}

    if method == "node.list":
        return service.list_nodes()

    if method == "node.describe":
        node_id = str(_get_param(params, "node_id", "id", default="") or "")
        nodes = service.list_nodes()
        for node in nodes:
            if str(node.get("id", "")) == node_id:
                return node
        raise LookupError("node_not_found")

    if method == "models.list":
        return {"models": service.list_models()}

    if method == "config.get":
        return {"config": service.get_config_snapshot()}

    raise LookupError(f"method_not_found:{method}")


@router.websocket("/")
@router.websocket("/ws")
async def websocket_gateway(websocket: WebSocket):
    service: WebService = websocket.app.state.service
    expected_token = _gateway_expected_token()
    provided_token = str(websocket.query_params.get("token", "")).strip()

    await websocket.accept()

    if expected_token and provided_token != expected_token:
        await _send_error(websocket, None, 403, "invalid_token")
        await websocket.close(code=1008, reason="invalid_token")
        return

    challenge_nonce = uuid4().hex
    await websocket.send_json(
        {
            "type": "event",
            "event": "connect.challenge",
            "payload": {"nonce": challenge_nonce},
        }
    )

    authenticated = False
    try:
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                continue

            message_type = str(message.get("type", "")).strip().lower()
            message_id = message.get("id")
            method = str(message.get("method", "")).strip()
            params = message.get("params") if isinstance(message.get("params"), dict) else {}

            if message_type != "req" or not method:
                continue

            if method == "connect":
                auth = params.get("auth") if isinstance(params.get("auth"), dict) else {}
                request_token = str(auth.get("token", "")).strip() if isinstance(auth, dict) else ""
                if expected_token and request_token != expected_token:
                    await _send_error(websocket, message_id, 403, "invalid_token")
                    continue
                authenticated = True
                await websocket.send_json(
                    {
                        "type": "res",
                        "id": message_id,
                        "ok": True,
                        "payload": {
                            "connected": True,
                            "authenticated": True,
                            "nonce": challenge_nonce,
                            "session_id": "gateway",
                        },
                    }
                )
                continue

            if not authenticated:
                await _send_error(websocket, message_id, 401, "not_authenticated")
                continue

            try:
                payload = await _handle_rpc(service, method, params, websocket=websocket)
                await websocket.send_json(
                    {
                        "type": "res",
                        "id": message_id,
                        "ok": True,
                        "payload": payload,
                    }
                )
            except ValueError as exc:
                await _send_error(websocket, message_id, 400, str(exc))
            except LookupError as exc:
                await _send_error(websocket, message_id, 404, str(exc))
            except Exception as exc:
                await _send_error(websocket, message_id, 500, f"internal_error:{exc}")
    except WebSocketDisconnect:
        return


@router.api_route("/chat", methods=["GET", "POST"], response_class=JSONResponse)
async def chat_compatibility(request: Request, service: WebService = Depends(get_service)):
    payload: dict[str, object] = {}
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
        if isinstance(body, dict):
            payload = body

    query = request.query_params

    def pick(*keys: str, default: str = "") -> str:
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                return str(value).strip()
            query_value = query.get(key)
            if query_value not in (None, ""):
                return str(query_value).strip()
        return default

    session_key = pick("session", "session_id", "sessionKey", default="web") or "web"
    channel = pick("channel", default="web") or "web"
    text = pick("text", "message", "prompt", "q", "content")
    session = service.create_session(channel=channel, peer=session_key)

    if not text:
        return {
            "status": "ok",
            "route": "/chat",
            "session": session,
            "accepted_methods": ["GET", "POST"],
            "accepted_fields": ["session", "session_id", "text", "message", "prompt", "q", "content"],
            "message": "Ruta de compatibilidad activa. Envía texto con POST o agrega text/message/prompt en la query.",
        }

    result = await run_in_threadpool(
        service.send_session_message,
        session_key,
        text,
        operator_identity="gateway",
        channel=channel,
    )
    return {
        "status": "ok",
        "route": "/chat",
        "session": session,
        "result": result,
    }

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, service: WebService = Depends(get_service)):
    panels = [
        "dashboard",
        "aprobaciones",
        "host",
    ]
    context = {
        "request": request,
        "title": "OpenClaw",
        "store": service.get_dashboard_data(),
        "approvals": service.list_approvals(),
        "panels": panels,
        "runtime_status": service.get_runtime_status(),
        "host": service.get_host_info(),
    }
    return request.app.state.templates.TemplateResponse(request, "dashboard.html", context)


@router.get("/health", response_class=JSONResponse)
async def health(service: WebService = Depends(get_service)):
    return {
        "status": "ok",
        "service": "openclaw-gateway",
        "store": service.get_dashboard_data(),
        "runtime_status": service.get_runtime_status(),
        "host": service.get_host_info(),
    }

@router.get("/approvals", response_class=JSONResponse)
async def list_approvals(status: str = "pending", service: WebService = Depends(get_service)):
    normalized_status = status.strip().lower() if isinstance(status, str) else "pending"
    allowed_status = normalized_status if normalized_status in {"pending", "approved", "rejected", "failed", "all"} else "pending"
    approvals = service.list_approvals(status=None if allowed_status == "all" else allowed_status)
    return {
        "status": "ok",
        "approvals": approvals,
        "pending_count": len([item for item in approvals if item.get("status") == "pending"]) if allowed_status == "all" else len(approvals),
    }


@router.delete("/approvals", response_class=JSONResponse)
async def clear_pending_approvals(service: WebService = Depends(get_service)):
    cleared = service.clear_pending_approvals(status="rejected")
    return {"status": "ok", "cleared": cleared}


@router.post("/approvals/{task_id}", response_class=JSONResponse)
async def approve_task(task_id: str, request: Request, service: WebService = Depends(get_service)):
    payload = await request.json()
    requested_status = str(payload.get("status", "approved")).strip().lower()
    status = requested_status if requested_status in {"approved", "rejected", "failed"} else "approved"
    if task_id.startswith("APR-"):
        success = service.mark_approval(task_id, status)
    else:
        success = service.approve_task(task_id, status)
    return {"status": "ok" if success else "error"}


@router.get("/nodes", response_class=JSONResponse)
async def nodes(service: WebService = Depends(get_service)):
    return {"nodes": service.list_nodes()}


@router.get("/providers", response_class=JSONResponse)
async def providers(service: WebService = Depends(get_service)):
    return {"providers": service.list_providers()}


@router.get("/routing/adaptive", response_class=JSONResponse)
async def adaptive_routing(service: WebService = Depends(get_service)):
    return service.adaptive_routing()


@router.get("/sessions", response_class=JSONResponse)
async def sessions(limit: int = 50, service: WebService = Depends(get_service)):
    return {"sessions": service.list_sessions(limit=limit)}


@router.get("/sessions/{session_id}", response_class=JSONResponse)
async def session_detail(session_id: str, service: WebService = Depends(get_service)):
    session = service.get_session(session_id)
    if session is None:
        return JSONResponse({"status": "error", "error": "session_not_found"}, status_code=404)
    return session


@router.post("/sessions/{session_id}/messages", response_class=JSONResponse)
async def session_message(session_id: str, request: Request, service: WebService = Depends(get_service)):
    payload = await request.json()
    text = str(payload.get("text", "")).strip()
    if not text:
        return JSONResponse({"status": "error", "error": "text_required"}, status_code=400)
    return service.process_session_message(session_id, text, operator_identity=str(payload.get("operator_identity", "web")))


@router.get("/traces/{trace_id}", response_class=JSONResponse)
async def trace_detail(trace_id: str, service: WebService = Depends(get_service)):
    trace = service.get_trace(trace_id)
    if trace is None:
        return JSONResponse({"status": "error", "error": "trace_not_found"}, status_code=404)
    return trace


@router.get("/sources", response_class=JSONResponse)
async def sources(limit: int = 50, service: WebService = Depends(get_service)):
    return service.list_sources(limit=limit)
