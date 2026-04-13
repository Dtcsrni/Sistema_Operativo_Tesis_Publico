from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .runtime_status import summarize_host

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

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> Any:
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
        context["request"] = request
        return templates.TemplateResponse("dashboard.html", context)

    @app.get("/health", response_class=JSONResponse)
    async def health() -> Any:
        return {
            "status": "ok",
            "store": store_summary,
            "host": summarize_host(),
            "runtime_status": runtime_status or {},
            "preflight": preflight or {},
            "secret_status": secret_status or {},
            "budget_status": budget_status or {},
        }

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
