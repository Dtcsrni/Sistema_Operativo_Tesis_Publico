from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .runtime_status import summarize_host
from .session_layer import build_nodes_summary, build_provider_summary, ensure_channel_session, process_channel_text, touch_session

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.templating import Jinja2Templates
except ImportError:  # pragma: no cover - optional runtime dependency
    FastAPI = None
    HTMLResponse = None
    JSONResponse = None
    Jinja2Templates = None
    Request = object


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def fastapi_available() -> bool:
    return FastAPI is not None and Jinja2Templates is not None


def web_stack_name() -> str:
    return "fastapi" if fastapi_available() else "stdlib"


def build_dashboard_context(
    store_summary: dict[str, Any],
    provider_registry: dict[str, Any],
    *,
    academic_packets: list[dict[str, Any]] | None = None,
    approvals: list[dict[str, Any]] | None = None,
    runtime_status: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    secret_status: dict[str, Any] | None = None,
    budget_status: dict[str, Any] | None = None,
    billing_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    packets = academic_packets or []
    pending_approvals = approvals or []
    runtime = runtime_status or {}
    secrets = secret_status or {}
    budget = budget_status or {}
    billing = billing_history or []
    return {
        "title": "Espacio de trabajo local de OpenClaw",
        "host": summarize_host(),
        "store": store_summary,
        "providers": provider_registry.get("providers", []),
        "academic_packets": packets[:10],
        "approvals": pending_approvals[:10],
        "runtime_status": runtime,
        "preflight": preflight or {},
        "secret_status": secrets,
        "budget_status": budget,
        "billing_history": billing[:10],
        "panels": [
            "bandeja_de_tareas",
            "matriz_de_literatura",
            "matriz_de_afirmaciones",
            "diff_markdown_latex",
            "aprobaciones",
            "trazabilidad",
            "costos",
            "secretos_por_dominio",
            "host",
            "servicios",
            "benchmarks_locales",
        ],
    }


def create_app(
    store_summary: dict[str, Any],
    provider_registry: dict[str, Any],
    *,
    repo_root: Path | None = None,
    store: Any | None = None,
    academic_packets: list[dict[str, Any]] | None = None,
    approvals: list[dict[str, Any]] | None = None,
    runtime_status: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    secret_status: dict[str, Any] | None = None,
    budget_status: dict[str, Any] | None = None,
    billing_history: list[dict[str, Any]] | None = None,
) -> Any:
    if not fastapi_available():
        raise RuntimeError("FastAPI y Jinja2 no están disponibles en el entorno.")

    app = FastAPI(title="Espacio de trabajo local de OpenClaw")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    root = repo_root or Path(__file__).resolve().parents[3]

    def _live_store_summary() -> dict[str, Any]:
        if store is None:
            return store_summary
        return store.audit_summary()

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> Any:
        context = build_dashboard_context(
            _live_store_summary(),
            provider_registry,
            academic_packets=academic_packets,
            approvals=store.list_pending_approvals() if store is not None else approvals,
            runtime_status=runtime_status,
            preflight=preflight,
            secret_status=secret_status,
            budget_status=budget_status,
            billing_history=store.list_billing_records(limit=10) if store is not None else billing_history,
        )
        context["request"] = request
        return templates.TemplateResponse("dashboard.html", context)

    @app.get("/health", response_class=JSONResponse)
    async def health() -> Any:
        return {
            "status": "ok",
            "store": _live_store_summary(),
            "host": summarize_host(),
            "runtime_status": runtime_status or {},
            "preflight": preflight or {},
            "secret_status": secret_status or {},
            "budget_status": budget_status or {},
        }

    @app.get("/nodes", response_class=JSONResponse)
    async def nodes() -> Any:
        return {"status": "ok", "nodes": build_nodes_summary(root)}

    @app.get("/providers", response_class=JSONResponse)
    async def providers() -> Any:
        return {"status": "ok", "providers": build_provider_summary(root)}

    @app.get("/sessions", response_class=JSONResponse)
    async def sessions() -> Any:
        if store is None:
            return {"status": "error", "reason": "store_not_available"}
        return {"status": "ok", "sessions": store.list_sessions(limit=100)}

    @app.post("/sessions", response_class=JSONResponse)
    async def create_session(request: Request) -> Any:
        if store is None:
            return {"status": "error", "reason": "store_not_available"}
        payload = await request.json()
        channel = str(payload.get("channel", "web_local")).strip() or "web_local"
        peer_id = str(payload.get("peer_id", "web")).strip() or "web"
        operator_identity = str(payload.get("operator_identity", peer_id)).strip() or peer_id
        title_hint = str(payload.get("title", "")).strip() or f"{channel}:{peer_id}"
        session = ensure_channel_session(
            store=store,
            channel=channel,
            peer_id=peer_id,
            operator_identity=operator_identity,
            title_hint=title_hint,
        )
        if payload.get("title") or payload.get("payload"):
            session = touch_session(store=store, session=session, title_hint=title_hint, payload_update=dict(payload.get("payload") or {}))
        return {"status": "ok", "session": session}

    @app.get("/sessions/{session_id}", response_class=JSONResponse)
    async def session_detail(session_id: str) -> Any:
        if store is None:
            return {"status": "error", "reason": "store_not_available"}
        session = store.get_session(session_id)
        if session is None:
            return {"status": "not_found", "session_id": session_id}
        return {"status": "ok", "session": session, "messages": store.list_session_messages(session_id, limit=100)}

    @app.post("/sessions/{session_id}/messages", response_class=JSONResponse)
    async def session_message(session_id: str, request: Request) -> Any:
        if store is None:
            return {"status": "error", "reason": "store_not_available"}
        session = store.get_session(session_id)
        if session is None:
            return {"status": "not_found", "session_id": session_id}
        payload = await request.json()
        text = str(payload.get("text", "")).strip()
        if not text:
            return {"status": "error", "reason": "empty_text"}
        store.cache_context(
            f"session:active:{session['channel']}:{session['peer_id']}",
            {"session_id": session_id, "updated_at": session.get("updated_at", "")},
        )
        from .telegram_bot import dispatch_command  # noqa: WPS433

        result = process_channel_text(
            store=store,
            repo_root=root,
            channel=str(session["channel"]),
            peer_id=str(session["peer_id"]),
            text=text,
            dispatcher=lambda command, argument: dispatch_command(command, argument, repo_root=root, store=store, chat_id=f"web:{session['peer_id']}"),
            operator_identity=str(session.get("operator_identity", session.get("peer_id", "web"))),
        )
        return {"status": "ok", **result}

    @app.post("/sessions/{session_id}/approve", response_class=JSONResponse)
    async def approve_session(session_id: str, request: Request) -> Any:
        if store is None:
            return {"status": "error", "reason": "store_not_available"}
        session = store.get_session(session_id)
        if session is None:
            return {"status": "not_found", "session_id": session_id}
        payload = await request.json()
        approval_id = str(payload.get("approval_id", "")).strip()
        decision = str(payload.get("status", "approved")).strip() or "approved"
        if approval_id:
            store.mark_approval(approval_id, decision)
        return {"status": "ok", "session_id": session_id, "approval_id": approval_id, "decision": decision}

    @app.get("/traces/{trace_id}", response_class=JSONResponse)
    async def trace_detail(trace_id: str) -> Any:
        if store is None:
            return {"status": "error", "reason": "store_not_available"}
        for item in store.list_request_traces(limit=200):
            if str(item.get("trace_id", "")) == trace_id:
                return {"status": "ok", "trace": item}
        return {"status": "not_found", "trace_id": trace_id}

    return app


def render_dashboard_html(
    store_summary: dict[str, Any],
    provider_registry: dict[str, Any],
    *,
    academic_packets: list[dict[str, Any]] | None = None,
    approvals: list[dict[str, Any]] | None = None,
    runtime_status: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    secret_status: dict[str, Any] | None = None,
    budget_status: dict[str, Any] | None = None,
    billing_history: list[dict[str, Any]] | None = None,
) -> str:
    context = build_dashboard_context(
        store_summary,
        provider_registry,
        academic_packets=academic_packets,
        approvals=approvals,
        runtime_status=runtime_status,
        preflight=preflight,
        secret_status=secret_status,
        budget_status=budget_status,
        billing_history=billing_history,
    )
    providers = "".join(
        f"<li>{provider['id']} · {provider['mode']}</li>"
        for provider in context["providers"]
    )
    panels = "".join(f"<li>{panel}</li>" for panel in context["panels"])
    packets = "".join(
        f"<li>{packet['mode']} · {packet['task_id']} · {packet.get('summary', '')}</li>"
        for packet in context["academic_packets"]
    ) or "<li>Sin paquetes académicos</li>"
    approvals_html = "".join(
        f"<li>{item['task_id']} · {item['step_id_expected']} · {item['diff_summary']}</li>"
        for item in context["approvals"]
    ) or "<li>Sin aprobaciones pendientes</li>"
    secrets_html = "".join(
        f"<li>{domain} · red={payload.get('network_mode', 'sin_dato')} · faltantes={sum(1 for provider in payload.get('providers', {}).values() if provider.get('status') == 'missing')}</li>"
        for domain, payload in context["secret_status"].get("domains", {}).items()
    ) or "<li>Sin estado de secretos</li>"
    budget_global = context["budget_status"].get("global", {})
    budget_domains_html = "".join(
        f"<li>{domain} · accion={payload.get('action', 'sin_dato')} · diario={payload.get('daily', {}).get('status', 'sin_dato')}</li>"
        for domain, payload in context["budget_status"].get("domains", {}).items()
    ) or "<li>Sin estado presupuestal</li>"
    billing_html = "".join(
        f"<li>{item.get('domain', 'sin_dominio')} · {item.get('provider', 'sin_proveedor')} · {item.get('estimated_cost_usd', 0.0)} USD · {item.get('billing_mode', 'estimated')}</li>"
        for item in context["billing_history"]
    ) or "<li>Sin registros de costo</li>"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{context['title']}</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 0; background: #f3efe6; color: #1f2421; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
    .card {{ background: #fffaf2; border: 1px solid #d8c9b8; border-radius: 18px; padding: 18px; }}
    .metric {{ font-size: 1.75rem; color: #8a3b12; }}
  </style>
</head>
<body>
  <main>
    <h1>{context['title']}</h1>
    <p>Espacio de trabajo local de OpenClaw para tareas, aprobaciones, costos y trazabilidad.</p>
    <section class="grid">
      <article class="card"><h2>Cola Operativa</h2><div class="metric">{context['store']['tasks']}</div></article>
      <article class="card"><h2>Aprobaciones</h2><div class="metric">{context['store']['pending_approvals']}</div></article>
      <article class="card"><h2>Evidencia</h2><div class="metric">{context['store']['evidence_records']}</div></article>
      <article class="card"><h2>Paquetes Académicos</h2><div class="metric">{context['store']['academic_packets']}</div></article>
      <article class="card"><h2>Despliegue</h2><div class="metric">{context['runtime_status'].get('state', 'sin_dato')}</div></article>
    </section>
    <section class="grid" style="margin-top: 16px;">
      <article class="card"><h3>Paneles</h3><ul>{panels}</ul></article>
      <article class="card"><h3>Proveedores</h3><ul>{providers}</ul></article>
      <article class="card"><h3>Stack web</h3><p>{web_stack_name()}</p><p>DB: {context['store']['db_path']}</p><p>Runtime activo: {context['runtime_status'].get('active_runtime', 'local')}</p></article>
      <article class="card"><h3>Paquetes recientes</h3><ul>{packets}</ul></article>
      <article class="card"><h3>Aprobaciones</h3><ul>{approvals_html}</ul></article>
      <article class="card"><h3>Preflight</h3><p>{context['preflight'].get('status', 'sin_dato')}</p></article>
      <article class="card"><h3>Secretos por dominio</h3><ul>{secrets_html}</ul></article>
      <article class="card"><h3>Presupuesto global</h3><p>Acción: {budget_global.get('action', 'sin_dato')}</p><p>Diario: {budget_global.get('daily', {}).get('status', 'sin_dato')}</p><p>Semanal: {budget_global.get('weekly', {}).get('status', 'sin_dato')}</p></article>
      <article class="card"><h3>Presupuesto por dominio</h3><ul>{budget_domains_html}</ul></article>
      <article class="card"><h3>Costos recientes</h3><ul>{billing_html}</ul></article>
    </section>
  </main>
</body>
</html>"""


def serve_workspace(
    host: str,
    port: int,
    store_summary: dict[str, Any],
    provider_registry: dict[str, Any],
    *,
    repo_root: Path | None = None,
    store: Any | None = None,
    academic_packets: list[dict[str, Any]] | None = None,
    approvals: list[dict[str, Any]] | None = None,
    runtime_status: dict[str, Any] | None = None,
    preflight: dict[str, Any] | None = None,
    secret_status: dict[str, Any] | None = None,
    budget_status: dict[str, Any] | None = None,
    billing_history: list[dict[str, Any]] | None = None,
) -> None:
    if fastapi_available():
        import uvicorn  # noqa: WPS433

        app = create_app(
            store_summary,
            provider_registry,
            repo_root=repo_root,
            store=store,
            academic_packets=academic_packets,
            approvals=approvals,
            runtime_status=runtime_status,
            preflight=preflight,
            secret_status=secret_status,
            budget_status=budget_status,
            billing_history=billing_history,
        )
        uvicorn.run(app, host=host, port=port)
        return

    html = render_dashboard_html(
        store_summary,
        provider_registry,
        academic_packets=academic_packets,
        approvals=approvals,
        runtime_status=runtime_status,
        preflight=preflight,
        secret_status=secret_status,
        budget_status=budget_status,
        billing_history=billing_history,
    )
    health = json.dumps(
        {
            "status": "ok",
            "store": store_summary,
            "host": summarize_host(),
            "runtime_status": runtime_status or {},
            "preflight": preflight or {},
            "secret_status": secret_status or {},
            "budget_status": budget_status or {},
        }
    ).encode("utf-8")
    html_bytes = html.encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(health)
                return
            if self.path in {"/", "/index.html"}:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_bytes)
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()
