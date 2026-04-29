from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from .service import WebService

router = APIRouter()

def get_service(request: Request) -> WebService:
    return request.app.state.service

@router.get("/", response_class=HTMLResponse)
async def index(request: Request, service: WebService = Depends(get_service)):
    # Standard panels list
    panels = [
        "bandeja_de_tareas",
        "matriz_de_literatura",
        "matriz_de_afirmaciones",
        "diff_markdown_latex",
        "aprobaciones",
        "trazabilidad",
        "secretos_por_dominio",
        "host",
        "servicios",
        "benchmarks_locales",
    ]
    
    context = {
        "request": request,
        "title": "OpenClaw Workspace",
        "store": service.get_dashboard_data(),
        "approvals": service.list_approvals(),
        "panels": panels,
        "academic_packets": [], # Placeholder
        "secret_status": {}, # Placeholder
        "budget_status": {"global": {"daily": {}}}, # Placeholder
        "runtime_status": service.get_runtime_status(),
        "host": service.get_host_info(),
    }
    return request.app.state.templates.TemplateResponse("dashboard.html", context)

@router.post("/approvals/{task_id}", response_class=JSONResponse)
async def approve_task(task_id: str, request: Request, service: WebService = Depends(get_service)):
    payload = await request.json()
    status = payload.get("status", "approved")
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
