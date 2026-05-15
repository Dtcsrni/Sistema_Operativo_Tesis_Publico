from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import json
from html import escape
import os

from common import ROOT, canonical_file_status, ensure_generated_dir, extract_markdown_labeled_value, extract_markdown_section_bullets, list_markdown_entries, load_csv_rows, load_yaml_json, stable_generated_at, write_text_if_changed

def priority_rank(value: str) -> int:
    order = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    return order.get(value, 99)

def render_table(headers: list[str], rows: list[list[str]]) -> str:
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_html = []
    for row in rows:
        cells = "".join(f"<td>{escape(str(cell))}</td>" for cell in row)
        body_html.append(f"<tr>{cells}</tr>")
    return f'<div class="table-container"><table><thead><tr>{header_html}</tr></thead><tbody>{"".join(body_html)}</tbody></table></div>'

def render_table_html(headers: list[str], rows: list[list[str]]) -> str:
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_html = []
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        body_html.append(f"<tr>{cells}</tr>")
    return f'<div class="table-container"><table><thead><tr>{header_html}</tr></thead><tbody>{"".join(body_html)}</tbody></table></div>'

def relative_from_generated(relative_path: str) -> str:
    generated_dir = ROOT / "06_dashboard" / "generado"
    return Path(os.path.relpath(ROOT / relative_path, generated_dir)).as_posix()

def source_link(label: str, relative_path: str) -> str:
    href = relative_from_generated(relative_path)
    return f'<a class="trace-link" href="{escape(href)}" target="_blank" rel="noreferrer">{escape(label)}</a>'

def extract_reasoning_level(relative_path: str) -> str | None:
    return extract_markdown_labeled_value(relative_path, "Uso de IA", "Nivel de razonamiento utilizado")

def extract_session_objective(relative_path: str) -> str:
    path = ROOT / relative_path
    in_section = False
    lines: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if stripped == "## Objetivo de la sesión":
                in_section = True
                continue
            if in_section and stripped.startswith("## "):
                break
            if in_section and stripped:
                lines.append(stripped)

    return " ".join(lines).strip()

def is_meaningful_value(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.strip().lower()
    if not lowered:
        return False
    placeholders = {
        "sí | no",
        "bajo | medio | alto | mixto | no aplica",
        "acción 1",
        "acción 2",
        "acción 3",
    }
    return lowered not in placeholders

def contains_actual_waste_signal(value: str | None) -> bool:
    if not is_meaningful_value(value):
        return False
    lowered = value.lower()
    avoided_markers = [
        "habría sido ineficiente",
        "se evitó",
        "evitado",
        "no se invirtió",
        "se evitara",
    ]
    return not any(marker in lowered for marker in avoided_markers)

def high_reasoning_justified(relative_path: str, reasoning_level: str | None) -> bool:
    if reasoning_level != "alto":
        return False

    objective = extract_session_objective(relative_path).lower()
    justification = (extract_markdown_labeled_value(relative_path, "Uso de IA", "Justificación del nivel elegido") or "").lower()
    combined = f"{objective} {justification}"
    keywords = [
        "arquitectura",
        "hipotes",
        "metrica",
        "evidencia",
        "consolid",
        "contradic",
        "linea base",
        "intermitencia",
        "taxonom",
        "diseño",
        "diseno",
    ]
    return any(keyword in combined for keyword in keywords)

def build_usage_recommendation(
    *,
    total_logs: int,
    sessions_with_explicit_progress: int,
    high_reasoning_sessions: int,
    justified_high_reasoning_sessions: int,
    weekly_waste_opportunities: int,
    weekly_actual_waste_signals: int,
    overconsumption_risk: str,
    active_block_name: str,
) -> str:
    parts: list[str] = []

    if total_logs == 0:
        return (
            "No hay suficiente historial para emitir una recomendación sólida. "
            "Primero conviene acumular bitácoras y resúmenes semanales con registro explícito de economía de uso."
        )

    if sessions_with_explicit_progress == total_logs:
        parts.append(
            "La cobertura actual sugiere una buena disciplina operativa: todas las sesiones registradas explicitan el avance funcional logrado."
        )
    else:
        parts.append(
            "La prioridad inmediata es elevar la disciplina de registro, porque no todas las sesiones dejan claro qué avance funcional produjo el consumo realizado."
        )

    if high_reasoning_sessions == 0:
        parts.append(
            "Por ahora no hay señal de abuso de razonamiento alto; la estrategia dominante parece conservadora y adecuada para una fase todavía orientada a base operativa."
        )
    elif high_reasoning_sessions == justified_high_reasoning_sessions:
        parts.append(
            "Las pocas sesiones con razonamiento alto parecen alineadas con tareas que sí lo ameritan, así que no se observa sobreconsumo por sofisticación innecesaria."
        )
    else:
        parts.append(
            "Hay sesiones con razonamiento alto que no quedan suficientemente justificadas; conviene revisar si ese nivel estaba respondiendo a complejidad real o solo a hábito."
        )

    if weekly_actual_waste_signals > 0:
        parts.append(
            "Ya existe al menos una semana con gasto ineficiente realmente registrado, así que la siguiente revisión debe identificar qué tipo de tarea consumió de más y convertir ese hallazgo en regla operativa."
        )
    elif weekly_waste_opportunities > 0:
        parts.append(
            "Sí aparecen oportunidades de desperdicio detectadas, pero registradas como evitadas y no como fallas consumadas; eso indica que la economía de uso ya está operando como criterio preventivo."
        )
    else:
        parts.append(
            "Todavía no se registran oportunidades claras de desperdicio, lo cual puede ser bueno o simplemente reflejar historial insuficiente; hace falta más serie temporal para sacar conclusiones firmes."
        )

    parts.append(
        f"En el estado actual del proyecto, centrado en {active_block_name.lower()}, la recomendación operativa es mantener razonamiento medio como default y reservar razonamiento alto únicamente para arquitectura comparativa, delimitación metodológica, operacionalización de hipótesis, métricas y consolidaciones extensas."
    )
    parts.append(
        "Para tareas mecánicas o de traducción documental, el sistema debería insistir en bajo o medio; para decisiones fundacionales, conviene subir solo después de formular un objetivo concreto y una salida verificable."
    )

    if overconsumption_risk == "alto":
        parts.append(
            "Dado que el riesgo heurístico de sobreconsumo es alto, la siguiente semana debería imponer una revisión obligatoria antes de cualquier uso intensivo: objetivo puntual, justificación del nivel de razonamiento y criterio de cierre."
        )
    elif overconsumption_risk == "moderado":
        parts.append(
            "Como el riesgo heurístico de sobreconsumo es moderado, conviene auditar las próximas sesiones con más detalle para evitar que el razonamiento alto se vuelva el modo por defecto."
        )
    else:
        parts.append(
            "Como el riesgo heurístico de sobreconsumo es bajo, el foco no debe estar en restringir más el uso, sino en sostener esta disciplina mientras el proyecto entre a fases metodológicamente más exigentes."
        )

    return " ".join(parts)

def load_optional_json(relative_path: str, default: dict) -> dict:
    path = ROOT / relative_path
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)

def to_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback

def to_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback

def format_ratio(ratio: float) -> str:
    return f"{round(ratio * 100, 1)}%"

def format_usd(value: float) -> str:
    return f"${value:,.2f} USD"

def display_status(status: object) -> str:
    labels = {
        "ok": "OK",
        "degraded": "Degradado",
        "down": "Caído",
        "unknown": "Desconocido",
        "stale": "Stale",
        "blocked_human_validation": "Bloqueado por validación humana",
    }
    return labels.get(str(status), str(status or "Desconocido"))

def status_badge(status: object) -> str:
    normalized = escape(str(status or "unknown"))
    return f'<span class="noc-status noc-status--{normalized}">{escape(display_status(status))}</span>'

def render_noc_stat(label: str, value: object, status: object = "unknown") -> str:
    return (
        f'<article class="noc-stat noc-stat--{escape(str(status or "unknown"))}">'
        f'<span>{escape(label)}</span>'
        f'<strong>{escape(str(value))}</strong>'
        f'</article>'
    )

def render_noc_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        rows = [["Sin datos"] + [""] * (len(headers) - 1)]
    return render_table_html(headers, rows)

def render_noc_service_rows(snapshot: dict, domain: str | None = None) -> list[list[str]]:
    services = snapshot.get("services", [])
    if domain:
        services = [item for item in services if item.get("domain") == domain]
    return [
        [
            escape(str(item.get("id", "n/a"))),
            status_badge(item.get("status")),
            escape(str(item.get("criticality", "n/a"))),
            escape(str(item.get("last_check", "n/a"))),
            escape(str(item.get("latency_ms", 0))),
            escape(str(item.get("detail", ""))),
            escape(", ".join(str(dep) for dep in item.get("dependencies", [])) or "sin dependencias"),
        ]
        for item in services
    ]

def render_noc_flow(flow: dict) -> str:
    prechecks = "".join(f"<li>{escape(str(item))}</li>" for item in flow.get("prechecks", []))
    return f"""
      <article class="noc-runbook-card">
        <div class="noc-runbook-card__header">
          <h3>{escape(str(flow.get("title", "Flujo operativo")))}</h3>
          {status_badge(flow.get("status"))}
        </div>
        <p>{escape(str(flow.get("objective", "")))}</p>
        <details>
          <summary>Prechecks y solicitud preparada</summary>
          <ul>{prechecks}</ul>
          <p><strong>Solicitud OpenClaw:</strong> {escape(str(flow.get("request", "")))}</p>
          <p><strong>Criterio OK:</strong> {escape(str(flow.get("ok_criteria", "")))}</p>
          <p><strong>Rollback:</strong> {escape(str(flow.get("rollback", "")))}</p>
        </details>
      </article>
    """

def render_observability_command_center(snapshot: dict) -> str:
    counts = snapshot.get("status_counts", {})
    runtime = snapshot.get("runtime", {})
    observability = snapshot.get("observability", {})
    publication = snapshot.get("publication", {})
    alerts = snapshot.get("alerts", [])
    nodes = snapshot.get("nodes", [])
    benchmarks = snapshot.get("benchmarks", [])
    compose_stack = snapshot.get("compose_stack", [])
    sources = snapshot.get("sources", [])
    flows = snapshot.get("flows", [])
    endpoints = runtime.get("endpoints", [])
    notification_policy = snapshot.get("notification_policy", {})

    alert_items = "".join(
        f"""
        <article class="noc-alert noc-alert--{escape(str(item.get('severity', 'unknown')))}">
          <span>{status_badge(item.get('severity'))}</span>
          <strong>{escape(str(item.get('impact', 'Sin impacto descrito')))}</strong>
          <p>{escape(str(item.get('evidence', 'Sin evidencia')))}</p>
          <small>{escape(str(item.get('owner', 'sin dueño')))} · {escape(str(item.get('next_step', 'Sin siguiente paso')))}</small>
        </article>
        """
        for item in alerts
    ) or '<p class="muted">No hay alertas priorizadas en el snapshot actual.</p>'

    node_cards = "".join(
        f"""
        <article class="noc-node-card">
          <div>
            <span>{escape(str(node.get('id', 'nodo')))}</span>
            <h3>{escape(str(node.get('label', 'Nodo')))}</h3>
          </div>
          {status_badge(node.get('status'))}
          <p>{escape(str(node.get('role', 'Sin rol registrado')))}</p>
          <small>Servicios: {escape(str(len(node.get('services', []))))} · Fuente: {escape(str(node.get('source', 'n/a')))}</small>
        </article>
        """
        for node in nodes
    )

    endpoint_rows = [
        [
            escape(str(item.get("id", "n/a"))),
            status_badge(item.get("status")),
            escape(str(item.get("label", ""))),
            escape(str(item.get("probe", {}).get("latency_ms", 0))),
            escape(str(item.get("probe", {}).get("detail", ""))),
            escape(str(item.get("source", ""))),
        ]
        for item in endpoints
    ]

    benchmark_rows = [
        [
            escape(str(item.get("node", "n/a"))),
            status_badge(item.get("status")),
            escape(str(item.get("latest_run_id", "n/a"))),
            escape(str(item.get("latest_validity", "unknown"))),
            escape(str(item.get("age_seconds", "n/a"))),
            escape(str(item.get("source", ""))),
        ]
        for item in benchmarks
    ]

    compose_rows = [
        [
            escape(str(item.get("id", "n/a"))),
            status_badge(item.get("status")),
            escape(str(item.get("image", "build-local"))),
            escape(", ".join(str(port) for port in item.get("ports", [])) or "sin puerto publicado"),
            escape(", ".join(str(dep) for dep in item.get("depends_on", [])) or "sin dependencias"),
            escape(str(item.get("detail", ""))),
        ]
        for item in compose_stack
    ]

    trace_rows = [
        [
            escape(str(item.get("path", "n/a"))),
            "sí" if item.get("exists") else "no",
            escape(str(item.get("updated_at", "n/a"))),
            f"<code>{escape(str(item.get('sha256', ''))[:16])}</code>",
        ]
        for item in sources
    ]

    return f"""
    <section id="observabilidad-distribuida" class="panel panel-highlight noc-shell" data-group="estado">
      <span class="eyebrow">Command Center</span>
      <h2>Observabilidad Distribuida SIOT</h2>
      <p class="lead">Vista privada de operación casi en tiempo real para PC, Edge, OpenClaw, agentes, publicación y trazabilidad. La UI centraliza control gobernado del stack en contenedores mediante solicitudes para OpenClaw con aprobación humana.</p>
      <div class="noc-kpi-row">
        {render_noc_stat("Estado global", display_status(snapshot.get("overall_status")), snapshot.get("overall_status"))}
        {render_noc_stat("OK", counts.get("ok", 0), "ok")}
        {render_noc_stat("Degradado", counts.get("degraded", 0), "degraded")}
        {render_noc_stat("Caído", counts.get("down", 0), "down")}
        {render_noc_stat("Stale", counts.get("stale", 0), "stale")}
        {render_noc_stat("Snapshot", snapshot.get("generated_at", "n/a"), "unknown")}
      </div>
      <div class="noc-banner noc-banner--{escape(str(snapshot.get("overall_status", "unknown")))}">
        <strong>Canal de notificaciones:</strong> {escape(str(notification_policy.get("inbox", "dashboard")))} ·
        Telegram se suprime cuando el dashboard registra heartbeat activo ({escape(str(notification_policy.get("dashboard_heartbeat_seconds", "n/a")))}s).
        <br><strong>Control:</strong> cola gobernada <code>runtime/observability/control_requests.jsonl</code>; sin Docker socket crudo ni comandos arbitrarios desde navegador.
      </div>
      <div class="noc-tabs" role="tablist" aria-label="Dominios de observabilidad SIOT">
        <button class="noc-tab is-active" type="button" data-noc-tab="resumen">Resumen</button>
        <button class="noc-tab" type="button" data-noc-tab="pc">PC Hub</button>
        <button class="noc-tab" type="button" data-noc-tab="edge">Edge</button>
        <button class="noc-tab" type="button" data-noc-tab="agentes">OpenClaw/Agentes</button>
        <button class="noc-tab" type="button" data-noc-tab="observabilidad">Observabilidad</button>
        <button class="noc-tab" type="button" data-noc-tab="flujos">Flujos</button>
        <button class="noc-tab" type="button" data-noc-tab="historico">Histórico</button>
        <button class="noc-tab" type="button" data-noc-tab="publicacion">Publicación</button>
        <button class="noc-tab" type="button" data-noc-tab="trazabilidad">Trazabilidad</button>
      </div>

      <div class="noc-tab-panel is-active" data-noc-panel="resumen">
        <div class="noc-grid">{node_cards}</div>
        <h3>Inbox operativo</h3>
        <div class="noc-alerts">{alert_items}</div>
      </div>

      <div class="noc-tab-panel" data-noc-panel="pc">
        <h3>Stack Docker Compose</h3>
        {render_noc_table(["Servicio Compose", "Estado", "Imagen", "Puertos", "Dependencias", "Detalle"], compose_rows)}
        <h3>Servicios PC Hub</h3>
        {render_noc_table(["Servicio", "Estado", "Criticidad", "Última revisión", "Latencia ms", "Detalle", "Dependencias"], render_noc_service_rows(snapshot, "sistema_tesis") + render_noc_service_rows(snapshot, "openclaw") + render_noc_service_rows(snapshot, "administrativo"))}
      </div>

      <div class="noc-tab-panel" data-noc-panel="edge">
        <h3>Servicios Edge</h3>
        {render_noc_table(["Servicio", "Estado", "Criticidad", "Última revisión", "Latencia ms", "Detalle", "Dependencias"], render_noc_service_rows(snapshot, "edge_iot"))}
      </div>

      <div class="noc-tab-panel" data-noc-panel="agentes">
        <div class="noc-kpi-row">
          {render_noc_stat("Orquestador", runtime.get("orchestrator", "OpenClaw"), runtime.get("openclaw_status", "unknown"))}
          {render_noc_stat("Runtime activo", runtime.get("active_runtime", "unknown"), runtime.get("openclaw_status", "unknown"))}
          {render_noc_stat("Serena", display_status(runtime.get("serena_status")), runtime.get("serena_status"))}
          {render_noc_stat("Caveman", display_status(runtime.get("caveman_status")), runtime.get("caveman_status"))}
          {render_noc_stat("Telegram", display_status(runtime.get("telegram_status")), runtime.get("telegram_status"))}
        </div>
        {render_noc_table(["Endpoint", "Estado", "Rol", "Latencia ms", "Detalle", "Fuente"], endpoint_rows)}
      </div>

      <div class="noc-tab-panel" data-noc-panel="observabilidad">
        <div class="noc-kpi-row">
          {render_noc_stat("Stack", observability.get("stack", "n/a"), observability.get("status", "unknown"))}
          {render_noc_stat("Modo", observability.get("mode", "n/a"), observability.get("status", "unknown"))}
          {render_noc_stat("Capas", len(observability.get("layers", [])), observability.get("status", "unknown"))}
        </div>
        <details open><summary>Capas y políticas</summary><pre><code>{escape(json.dumps(observability, ensure_ascii=False, indent=2))}</code></pre></details>
      </div>

      <div class="noc-tab-panel" data-noc-panel="flujos">
        <div class="noc-runbook-grid">{''.join(render_noc_flow(flow) for flow in flows)}</div>
      </div>

      <div class="noc-tab-panel" data-noc-panel="historico">
        <h3>Benchmarks e incidentes operativos</h3>
        {render_noc_table(["Nodo", "Estado", "Último run", "Validez", "Edad s", "Fuente"], benchmark_rows)}
      </div>

      <div class="noc-tab-panel" data-noc-panel="publicacion">
        <div class="noc-kpi-row">
          {render_noc_stat("Bundle público", display_status(publication.get("status")), publication.get("status"))}
          {render_noc_stat("Manifest", "sí" if publication.get("manifest_exists") else "no", publication.get("status"))}
          {render_noc_stat("Archivos", publication.get("files", 0), publication.get("status"))}
          {render_noc_stat("Edad s", publication.get("age_seconds", "n/a"), publication.get("status"))}
        </div>
        <p>Vista pública sanitizada: <code>06_dashboard/publico/observability_status_public.json</code>.</p>
      </div>

      <div class="noc-tab-panel" data-noc-panel="trazabilidad">
        <h3>Fuentes y hashes</h3>
        {render_noc_table(["Fuente", "Existe", "Actualizado", "SHA-256"], trace_rows)}
      </div>
    </section>
    """

def main() -> int:
    ensure_generated_dir()
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    hipotesis = load_yaml_json("00_sistema_tesis/config/hipotesis.yaml")["hipotesis"]
    bloques = load_yaml_json("00_sistema_tesis/config/bloques.yaml")["bloques"]
    dashboard = load_yaml_json("00_sistema_tesis/config/dashboard.yaml")
    publicacion = load_yaml_json("00_sistema_tesis/config/publicacion.yaml")
    gobernanza_ia = load_yaml_json("00_sistema_tesis/config/ia_gobernanza.yaml")
    backlog = load_csv_rows("01_planeacion/backlog.csv")
    riesgos = load_csv_rows("01_planeacion/riesgos.csv")
    security_report = load_yaml_json("00_sistema_tesis/config/security_report.json")
    token_budget_cfg = load_optional_json("00_sistema_tesis/config/token_budget.json", {})
    token_usage = load_optional_json("00_sistema_tesis/config/token_usage_snapshot.json", {})
    openclaw_status = load_optional_json("00_sistema_tesis/config/openclaw_status.json", {})
    observability_snapshot = load_optional_json(
        "00_sistema_tesis/config/observability_dashboard_snapshot.json",
        {
            "schema_version": "siot-observability-dashboard-v1",
            "generated_at": "snapshot no generado",
            "overall_status": "unknown",
            "status_counts": {},
            "nodes": [],
            "services": [],
            "compose_stack": [],
            "runtime": {},
            "observability": {},
            "benchmarks": [],
            "publication": {},
            "flows": [],
            "notification_policy": {},
            "alerts": [
                {
                    "severity": "unknown",
                    "owner": "sistema_tesis",
                    "impact": "Snapshot de observabilidad no generado",
                    "evidence": "Ejecuta python3 07_scripts/ops/build_observability_snapshot.py",
                    "next_step": "Generar snapshot antes de usar la vista operativa.",
                }
            ],
            "sources": [],
        },
    )
    public_bundle = load_optional_json(publicacion["salida"]["manifest"], {})
    decisiones = list_markdown_entries("00_sistema_tesis/decisiones")[:5]
    reportes_semanales = list_markdown_entries("00_sistema_tesis/reportes_semanales")
    bitacoras = list_markdown_entries("00_sistema_tesis/bitacora")
    
    # Pre-cargar narrativa para evitar CORS en file://
    # Incluir docs base + todas las decisiones
    narrativa_slugs = {
        "README_INICIO.md": "README Inicio",
        "00_sistema_tesis/manual_operacion_humana.md": "Manual Humano",
    }
    
    # Documentación del sistema
    docs_dir = ROOT / "00_sistema_tesis" / "documentacion_sistema"
    if docs_dir.exists():
        for f in docs_dir.glob("*.md"):
            rel = f.relative_to(ROOT).as_posix()
            narrativa_slugs[rel] = f.stem.replace("_", " ").title()
            
    # Decisiones
    dec_dir = ROOT / "00_sistema_tesis" / "decisiones"
    if dec_dir.exists():
        for f in dec_dir.glob("*.md"):
            rel = f.relative_to(ROOT).as_posix()
            # Usar el ID de la decisión como etiqueta si es posible
            label = f.stem.split("_")[1] if "_" in f.stem else f.stem
            narrativa_slugs[rel] = label

    narrativa_data = {}
    for rel_path in narrativa_slugs:
        abs_path = ROOT / rel_path
        if abs_path.exists():
            narrativa_data[rel_path] = abs_path.read_text(encoding="utf-8")
        else:
            narrativa_data[rel_path] = f"Error: No se encontró {rel_path}"

    file_status = canonical_file_status()
    generated_at = stable_generated_at(
        [
            "00_sistema_tesis/config/sistema_tesis.yaml",
            "00_sistema_tesis/config/hipotesis.yaml",
            "00_sistema_tesis/config/bloques.yaml",
            "00_sistema_tesis/config/dashboard.yaml",
            "00_sistema_tesis/config/publicacion.yaml",
            "00_sistema_tesis/config/ia_gobernanza.yaml",
            "00_sistema_tesis/config/security_report.json",
            "00_sistema_tesis/config/token_budget.json",
            "00_sistema_tesis/config/token_usage_snapshot.json",
            "00_sistema_tesis/config/openclaw_status.json",
            "00_sistema_tesis/config/observability_dashboard_snapshot.json",
            "01_planeacion/backlog.csv",
            "01_planeacion/riesgos.csv",
            "00_sistema_tesis/decisiones",
            "00_sistema_tesis/reportes_semanales",
            "00_sistema_tesis/bitacora",
            publicacion["salida"]["manifest"],
        ]
    )

    # Security Summary
    sec_summary = security_report.get("summary", {})
    sec_details = security_report.get("details", [])
    trust_score = int((sec_summary.get("passed", 0) / sec_summary.get("total", 1)) * 100) if sec_summary else 0
    
    active_block = next(item for item in bloques if item["id"] == sistema["bloque_activo"])
    active_hypotheses = [item for item in hipotesis if item["estado"] == "activa"]
    active_hypotheses.sort(key=lambda item: (priority_rank(item["prioridad"]), item["id"]))
    top_backlog = [item for item in backlog if item["estado"] in {"pendiente", "en_progreso"}]
    top_backlog.sort(key=lambda item: (priority_rank(item["prioridad"]), item["fecha_objetivo"]))
    open_risks = [item for item in riesgos if item["estado"] == "abierto"]
    latest_weekly_report = reportes_semanales[0] if reportes_semanales else None
    economy_bullets = extract_markdown_section_bullets(latest_weekly_report["archivo"], "Economía de uso") if latest_weekly_report else []
    weekly_reports_with_economy = sum(1 for item in reportes_semanales if extract_markdown_section_bullets(item["archivo"], "Economía de uso"))
    session_logs_with_economy = sum(1 for item in bitacoras if extract_markdown_section_bullets(item["archivo"], "Economía de uso"))
    reasoning_levels: dict[str, int] = {}
    sessions_with_explicit_progress = 0
    high_reasoning_sessions = 0
    justified_high_reasoning_sessions = 0
    for item in bitacoras:
        level = extract_reasoning_level(item["archivo"])
        if level:
            reasoning_levels[level] = reasoning_levels.get(level, 0) + 1
        progress_value = extract_markdown_labeled_value(item["archivo"], "Economía de uso", "Avance funcional logrado por este consumo")
        if is_meaningful_value(progress_value):
            sessions_with_explicit_progress += 1
        if level == "alto":
            high_reasoning_sessions += 1
            if high_reasoning_justified(item["archivo"], level):
                justified_high_reasoning_sessions += 1
    reasoning_summary = ", ".join(f"{level}={count}" for level, count in sorted(reasoning_levels.items())) or "sin datos"
    weekly_actual_waste_signals = sum(
        1
        for item in reportes_semanales
        if contains_actual_waste_signal(extract_markdown_labeled_value(item["archivo"], "Economía de uso", "Qué consumió de más para el valor obtenido"))
    )
    weekly_waste_opportunities = sum(
        1
        for item in reportes_semanales
        if is_meaningful_value(extract_markdown_labeled_value(item["archivo"], "Economía de uso", "Qué consumió de más para el valor obtenido"))
    )
    overconsumption_risk = "bajo"
    if high_reasoning_sessions > justified_high_reasoning_sessions or weekly_actual_waste_signals > 0:
        overconsumption_risk = "moderado"
    if high_reasoning_sessions > justified_high_reasoning_sessions and weekly_actual_waste_signals > 0:
        overconsumption_risk = "alto"
    usage_recommendation = build_usage_recommendation(
        total_logs=len(bitacoras),
        sessions_with_explicit_progress=sessions_with_explicit_progress,
        high_reasoning_sessions=high_reasoning_sessions,
        justified_high_reasoning_sessions=justified_high_reasoning_sessions,
        weekly_waste_opportunities=weekly_waste_opportunities,
        weekly_actual_waste_signals=weekly_actual_waste_signals,
        overconsumption_risk=overconsumption_risk,
        active_block_name=active_block["nombre"],
    )
    task_matrix = gobernanza_ia["economia_y_optimizacion_de_uso"]["matriz_operativa_por_tipo_de_tarea"]
    model_policy = gobernanza_ia["economia_y_optimizacion_de_uso"]["politica_de_modelos_y_razonamiento"]
    token_snapshot_status = str(token_usage.get("status") or "degraded")
    token_snapshot_message = str(token_usage.get("message") or "Sin datos de sincronizacion de API.")
    daily_budget_tokens = to_int(token_usage.get("budgets", {}).get("daily", {}).get("tokens"), to_int(token_budget_cfg.get("daily", {}).get("tokens"), 40000))
    weekly_budget_tokens = to_int(token_usage.get("budgets", {}).get("weekly", {}).get("tokens"), to_int(token_budget_cfg.get("weekly", {}).get("tokens"), 240000))
    daily_budget_usd = to_float(token_usage.get("budgets", {}).get("daily", {}).get("usd"), to_float(token_budget_cfg.get("daily", {}).get("usd"), 8.0))
    weekly_budget_usd = to_float(token_usage.get("budgets", {}).get("weekly", {}).get("usd"), to_float(token_budget_cfg.get("weekly", {}).get("usd"), 48.0))
    daily_window = token_usage.get("windows", {}).get("daily", {})
    weekly_window = token_usage.get("windows", {}).get("weekly", {})
    daily_tokens_used = to_int(daily_window.get("tokens_used"), 0)
    weekly_tokens_used = to_int(weekly_window.get("tokens_used"), 0)
    daily_tokens_remaining = to_int(daily_window.get("tokens_remaining"), max(daily_budget_tokens - daily_tokens_used, 0))
    weekly_tokens_remaining = to_int(weekly_window.get("tokens_remaining"), max(weekly_budget_tokens - weekly_tokens_used, 0))
    daily_tokens_ratio = to_float(daily_window.get("tokens_ratio"), (daily_tokens_used / max(daily_budget_tokens, 1)))
    weekly_tokens_ratio = to_float(weekly_window.get("tokens_ratio"), (weekly_tokens_used / max(weekly_budget_tokens, 1)))
    daily_usd_used = to_float(daily_window.get("usd_used"), 0.0)
    weekly_usd_used = to_float(weekly_window.get("usd_used"), 0.0)
    daily_usd_remaining = to_float(daily_window.get("usd_remaining"), max(daily_budget_usd - daily_usd_used, 0.0))
    weekly_usd_remaining = to_float(weekly_window.get("usd_remaining"), max(weekly_budget_usd - weekly_usd_used, 0.0))
    daily_requests = to_int(daily_window.get("requests"), 0)
    weekly_requests = to_int(weekly_window.get("requests"), 0)
    token_recommendations = token_usage.get("recommendations", [])
    if not token_recommendations:
        token_recommendations = ["Sin recomendaciones calculadas para esta corrida."]
    token_recommendation_items = [str(item) for item in token_recommendations[:6]]
    top_models_weekly = token_usage.get("model_breakdown", {}).get("weekly_top_models", [])
    top_models_lines = []
    for model_item in top_models_weekly[:5]:
        model_name = escape(str(model_item.get("model") or "unknown"))
        model_tokens = escape(str(to_int(model_item.get("tokens"), 0)))
        top_models_lines.append(f"{model_name}: {model_tokens}")
    token_top_models = " | ".join(top_models_lines) if top_models_lines else "sin datos"
    token_generated_at = str(token_usage.get("generated_at") or "n/a")
    token_source_tz = str(token_usage.get("timezone") or token_budget_cfg.get("timezone") or "n/a")
    source_explorer_rows = [
        [
            escape(item["clave"]),
            source_link(item["ruta"], item["ruta"]),
            escape("sí" if item["existe"] else "no"),
            escape(item["modificado"]),
        ]
        for item in file_status
    ]
    
    security_rows = [
        [
            escape(d["name"]),
            "PASS" if d["success"] else "FAIL",
            "CRÍTICA" if d["critical"] else "Normal",
            escape(d["output"].split('\n')[0])
        ]
        for d in sec_details
    ]

    traceability_rows = [
        [
            '<a href="#resumen-general" class="trace-link">Resumen general</a>',
            source_link("dashboard.yaml", "00_sistema_tesis/config/dashboard.yaml"),
            "Muestra el estado global y KPIs inmediatos.",
        ],
        [
            '<a href="#bloque-activo" class="trace-link">Bloque activo</a>',
            source_link("bloques.yaml", "00_sistema_tesis/config/bloques.yaml"),
            "Seguimiento del bloque de investigación actual.",
        ],
        [
            '<a href="#hipotesis-activas" class="trace-link">Hipótesis activas</a>',
            source_link("hipotesis.yaml", "00_sistema_tesis/config/hipotesis.yaml"),
            "Validación científica de supuestos de resiliencia.",
        ],
        [
            '<a href="#decisiones-recientes" class="trace-link">Decisiones recientes</a>',
            source_link("decisiones/", "00_sistema_tesis/decisiones"),
            "Registro de arquitectura y gobernanza (ADR).",
        ],
        [
            '<a href="#backlog-prioritario" class="trace-link">Backlog prioritario</a>',
            source_link("backlog.csv", "01_planeacion/backlog.csv"),
            "Tareas pendientes y roadmap de ejecución.",
        ],
        [
            '<a href="#riesgos-abiertos" class="trace-link">Riesgos abiertos</a>',
            source_link("riesgos.csv", "01_planeacion/riesgos.csv"),
            "Gestión proactiva de amenazas al proyecto.",
        ],
        [
            '<a href="#estado-archivos-canonicos" class="trace-link">Archivos canónicos</a>',
            source_link("sistema_tesis.yaml", "00_sistema_tesis/config/sistema_tesis.yaml"),
            "Verificación de integridad de las fuentes de verdad.",
        ],
    ]

    nodos_rows = [
        [
            id_nodo,
            data.get("rol", "n/a"),
            data.get("os", "n/a"),
            ", ".join(data.get("servicios", [])),
            data.get("hardware", "host/vm")
        ]
        for id_nodo, data in sistema.get("nodos_distribuidos", {}).items()
    ]

    html = f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0d0e0a">
  <title>Gobernanza | {escape(sistema["identidad_proyecto"]["nombre_corto"])}</title>
  <link rel="stylesheet" href="estilos.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css">
  <link rel="manifest" href="manifest.webmanifest">
  <script>
    window.SIOT_NARRATIVA = {json.dumps(narrativa_data, ensure_ascii=False)};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-bash.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-yaml.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-markdown.min.js"></script>
  <script defer src="app.js"></script>
</head>
<body>
  <nav class="sidebar">
    <div class="sidebar-header">
      <div class="logo">{escape(sistema["identidad_proyecto"]["nombre_corto"])}</div>
      <div class="version">v{escape(sistema["version"])}</div>
    </div>
    <div class="sidebar-scroll">
      <div class="nav-group">
        <label>Principal</label>
        <a href="#resumen-general" class="nav-item">Resumen</a>
        <a href="#que-revisar-siempre" class="nav-item">Checklist</a>
        <a href="#seguridad-integridad" class="nav-item">Seguridad</a>
      </div>
      <div class="nav-group">
        <label>Investigación</label>
        <a href="#bloque-activo" class="nav-item">Bloque</a>
        <a href="#hipotesis-activas" class="nav-item">Hipótesis</a>
      </div>
      <div class="nav-group">
        <label>Operación</label>
        <a href="#observabilidad-distribuida" class="nav-item">Command Center</a>
        <a href="#economia-uso" class="nav-item">Economía</a>
        <a href="#fuentes-verdad" class="nav-item">Trazabilidad</a>
        <a href="#narrativa-sistema" class="nav-item">Narrativa</a>
        <a href="wiki/index.html" class="nav-item wiki-nav">Wiki →</a>
      </div>
    </div>
  </nav>
  <main class="content-wrapper">
    <header class="hero">
      <span class="eyebrow">Sistema Operativo de la Tesis</span>
      <h1>{escape(sistema["titulo_vigente"])}</h1>
      <p class="lead">{escape(sistema["resumen_problema"])}</p>
      
      <div class="stats" style="margin-top: 40px;">
        <article>
          <span>Versión</span>
          <strong>{escape(sistema["version"])}</strong>
        </article>
        <article>
          <span>Estado Global</span>
          <strong>{escape(sistema["estado_global"])}</strong>
        </article>
        <article>
          <span>Confianza Integridad</span>
          <strong>{trust_score}%</strong>
        </article>
        <article>
          <span>Generado</span>
          <strong>{escape(generated_at)}</strong>
        </article>
      </div>
    </header>

    <section class="toolbar" style="max-width: 1400px; margin: 0 auto 40px;">
      <div class="panel" style="display: flex; gap: 20px; align-items: center; padding: 16px 24px;">
        <input id="panel-search" type="search" placeholder="Buscar en la gobernanza..." style="flex: 1; background: transparent; border: none; color: white; font-size: 1rem; outline: none;">
        <div class="toolbar-actions">
          <button class="filter-btn is-active" data-filter="all" type="button">Todo</button>
          <button class="filter-btn" data-filter="estado" type="button">Estado</button>
          <button class="filter-btn" data-filter="ia" type="button">IA</button>
          <button class="filter-btn" data-filter="planeacion" type="button">Planeación</button>
          <button class="filter-btn" data-filter="fuentes" type="button">Fuentes</button>
        </div>
      </div>
    </section>

    <section id="resumen-general" class="panel panel-highlight" data-group="estado">
      <span class="eyebrow">Vista Ejecutiva</span>
      <h2>Resumen de Operación</h2>
      <div class="stats">
        <article><span>Bloque activo</span><strong>{escape(sistema["bloque_activo"])}</strong></article>
        <article><span>Fase actual</span><strong>{escape(sistema["fase_actual"])}</strong></article>
        <article><span>Siguiente entregable</span><strong>{escape(sistema["siguiente_entregable"])}</strong></article>
        <article><span>Riesgo principal</span><strong>{escape(sistema["riesgo_principal_abierto"])}</strong></article>
      </div>
      <div style="margin-top: 24px;">
          <p class="notice">{escape(dashboard["reglas"]["aviso_no_editar"])}</p>
      </div>
    </section>

    {render_observability_command_center(observability_snapshot)}

    <section id="que-revisar-siempre" class="panel panel-highlight panel-sticky" data-group="estado">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div>
          <span class="eyebrow">Protocolo</span>
          <h2>Checklist de Retoma</h2>
        </div>
        <button class="review-rail__toggle" type="button" data-review-toggle>Ocultar</button>
      </div>
      <div class="stats" data-review-content style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;">
        <a class="panel" href="../../00_sistema_tesis/manual_operacion_humana.md" style="text-decoration: none; color: inherit; display: flex; flex-direction: column;">
          <strong style="color: var(--accent); display: block; margin-bottom: 6px; font-size: 1.1rem;">Manual Humano</strong>
          <span style="font-size: 0.85rem; color: var(--text); font-weight: 500; margin-bottom: 4px;">Ruta de operación</span>
          <span style="font-size: 0.75rem; color: var(--muted); line-height: 1.4;">Protocolo de soberanía y guía de operación manual obligatoria para el tesista.</span>
        </a>
        <a class="panel" href="{escape(relative_from_generated('01_planeacion/backlog.csv'))}" target="_blank" style="text-decoration: none; color: inherit; display: flex; flex-direction: column;">
          <strong style="color: var(--accent); display: block; margin-bottom: 6px; font-size: 1.1rem;">Backlog</strong>
          <span style="font-size: 0.85rem; color: var(--text); font-weight: 500; margin-bottom: 4px;">Tareas pendientes</span>
          <span style="font-size: 0.75rem; color: var(--muted); line-height: 1.4;">Gestión de tareas, prioridades y estado operativo actual del proyecto de tesis.</span>
        </a>
        <a class="panel" href="{escape(relative_from_generated('00_sistema_tesis/bitacora/matriz_trazabilidad.md'))}" target="_blank" style="text-decoration: none; color: inherit; display: flex; flex-direction: column;">
          <strong style="color: var(--accent); display: block; margin-bottom: 6px; font-size: 1.1rem;">Trazabilidad</strong>
          <span style="font-size: 0.85rem; color: var(--text); font-weight: 500; margin-bottom: 4px;">Evidencia técnica</span>
          <span style="font-size: 0.75rem; color: var(--muted); line-height: 1.4;">Mapa de vínculos inmutables entre decisiones humanas y artefactos generados.</span>
        </a>
        <a class="panel" href="wiki/index.html" style="text-decoration: none; color: inherit; display: flex; flex-direction: column;">
          <strong style="color: var(--accent); display: block; margin-bottom: 6px; font-size: 1.1rem;">Wiki Local</strong>
          <span style="font-size: 0.85rem; color: var(--text); font-weight: 500; margin-bottom: 4px;">Documentación derivada</span>
          <span style="font-size: 0.75rem; color: var(--muted); line-height: 1.4;">Documentación técnica detallada y guías de referencia rápida verificables.</span>
        </a>
      </div>
    </section>

    <section id="seguridad-integridad" class="panel" data-group="ia">
      <span class="eyebrow">Auditoría</span>
      <h2>Seguridad e Integridad</h2>
      <div class="stats">
        <article><span>Índice de confianza</span><strong>{trust_score}%</strong></article>
        <article><span>Auditadas</span><strong>{sec_summary.get("total", 0)}</strong></article>
        <article><span>Exitosas</span><strong>{sec_summary.get("passed", 0)}</strong></article>
        <article><span>Críticas</span><strong>{sec_summary.get("critical_failures", 0)}</strong></article>
      </div>
      {render_table_html(["Auditoría", "Resultado", "Nivel", "Detalle"], security_rows)}
    </section>

    <section id="topologia-distribuida" class="panel" data-group="estado">
      <span class="eyebrow">Arquitectura</span>
      <h2>Topología Distribuida</h2>
      <p class="lead">Configuración de nodos soberanos y operativos del sistema.</p>
      {render_table(["Nodo", "Rol", "OS", "Servicios", "Hardware"], nodos_rows)}
    </section>

    <section id="bloque-activo" class="panel" data-group="estado">
      <span class="eyebrow">Fase Actual</span>
      <h2>{escape(active_block["nombre"])}</h2>
      <p class="tag">{escape(active_block["id"])} · {escape(active_block["tipo"])}</p>
      <p class="lead">{escape(active_block["descripcion"])}</p>
      <div style="margin-top: 20px;">
          <strong>Criterio de salida:</strong> <span>{escape(active_block["criterio_salida"])}</span>
      </div>
    </section>

    <section id="hipotesis-activas" class="panel" data-group="estado">
      <h2>Hipótesis activas</h2>
      {render_table(
          ["ID", "Hipótesis", "Prioridad", "Evidencia integrada", "Bloques"],
          [
              [
                  item["id"],
                  item["nombre_corto"],
                  item["prioridad"],
                  item["evidencia_disponible"]["integrada"],
                  "|".join(item["bloques_asociados"]),
              ]
              for item in active_hypotheses[:6]
          ],
      )}
    </section>

    <section id="decisiones-recientes" class="panel" data-group="fuentes">
      <h2>Decisiones recientes</h2>
      <ul class="list">
        {''.join(f"<li><strong>{escape(item['fecha'])}</strong> · <a href='{escape(relative_from_generated(item['archivo']))}' class='narrative-link'>{escape(item['titulo'])}</a></li>" for item in decisiones)}
      </ul>
    </section>

    <section id="economia-uso" class="panel" data-group="ia">
      <h2>Economía de uso</h2>
      <p class="tag">{"Fuente: " + escape(latest_weekly_report["titulo"]) if latest_weekly_report else "Sin resumen semanal"}</p>
      <ul class="list">
        {''.join(f"<li>{escape(item)}</li>" for item in economy_bullets) if economy_bullets else "<li>No hay señales semanales de economía de uso registradas todavía.</li>"}
      </ul>
    </section>

    <section class="panel" data-group="ia">
      <h2>Indicadores acumulados de uso</h2>
      {render_table(
          ["Indicador", "Valor"],
          [
              ["Resúmenes semanales con economía de uso", f"{weekly_reports_with_economy}/{len(reportes_semanales)}"],
              ["Bitácoras con economía de uso", f"{session_logs_with_economy}/{len(bitacoras)}"],
              ["Sesiones con avance funcional explícito", f"{sessions_with_explicit_progress}/{len(bitacoras)}"],
              ["Distribución de niveles de razonamiento", reasoning_summary],
              ["Cobertura mínima actual", "establecida" if weekly_reports_with_economy and session_logs_with_economy else "incompleta"],
          ],
      )}
    </section>

    <section class="panel" data-group="ia">
      <h2>Calidad del consumo</h2>
      {render_table(
          ["Indicador", "Valor"],
          [
              ["Sesiones con razonamiento alto", str(high_reasoning_sessions)],
              ["Sesiones donde ese nivel parece justificado", f"{justified_high_reasoning_sessions}/{high_reasoning_sessions}" if high_reasoning_sessions else "0/0"],
              ["Semanas con oportunidad de desperdicio identificada", f"{weekly_waste_opportunities}/{len(reportes_semanales)}"],
              ["Semanas con gasto ineficiente realmente registrado", f"{weekly_actual_waste_signals}/{len(reportes_semanales)}"],
              ["Riesgo heurístico de sobreconsumo", overconsumption_risk],
          ],
      )}
    </section>

    <section class="panel panel-highlight" data-group="ia">
      <h2>Recomendación operativa de uso</h2>
      <p>{escape(usage_recommendation)}</p>
    </section>

    <section id="matriz-tareas" class="panel" data-group="ia">
      <span class="eyebrow">Gobernanza IA</span>
      <h2>Matriz por tipo de tarea</h2>
      {render_table(
          ["Tipo de tarea", "Nivel recomendado", "Cuándo subir", "Cuándo bajar"],
          [
              [
                  item["tipo_de_tarea"],
                  item["nivel_recomendado"],
                  item["cuando_subir"],
                  item["cuando_bajar"],
              ]
              for item in task_matrix
          ],
      )}
      <p class="trace-row">Fuente: {source_link("ia_gobernanza.yaml", "00_sistema_tesis/config/ia_gobernanza.yaml")}</p>
    </section>

    <section id="politica-modelos" class="panel panel-highlight" data-group="ia">
      <span class="eyebrow">Estrategia</span>
      <h2>Política de modelos y razonamiento</h2>
      <p class="lead">Regla operativa: un modelo base por tramo de trabajo. Cambia solo cuando cambie la clase de tarea o el costo del error.</p>
      {render_table_html(
          ["Tipo de tarea", "Modelo recomendado", "Nivel", "Uso", "Cuando subir", "Cuando bajar"],
          [
              [
                  item["tipo_de_tarea"],
                  item["modelo_recomendado"],
                  item["nivel_recomendado"],
                  item["uso"],
                  item["cuando_subir"],
                  item["cuando_bajar"],
              ]
              for item in model_policy
          ],
      )}
    </section>

    <section id="backlog-prioritario" class="panel" data-group="planeacion">
      <span class="eyebrow">Planeación</span>
      <h2>Backlog prioritario</h2>
      {render_table(
          ["Tarea", "Bloque", "Descripción", "Prioridad", "Estado"],
          [
              [item["task_id"], item["bloque"], item["tarea"], item["prioridad"], item["estado"]]
              for item in top_backlog[:8]
          ],
      )}
    </section>

    <section id="fuentes-verdad" class="panel panel-highlight" data-group="fuentes">
      <span class="eyebrow">Trazabilidad</span>
      <h2>Explorador de fuentes de verdad</h2>
      {render_table_html(["Clave", "Ruta canónica", "Existe", "Modificado"], source_explorer_rows)}
    </section>

    <section id="narrativa-sistema" class="panel panel-highlight" data-group="fuentes">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid var(--line); padding-bottom: 15px;">
        <div>
          <span class="eyebrow" style="letter-spacing: 0.2em;">EXPLORADOR NARRATIVO</span>
          <h2 style="margin: 5px 0 0; border: none; padding: 0;">Contexto del Sistema</h2>
        </div>
        <select id="md-selector" class="filter-btn" style="background: var(--surface-strong); color: var(--accent); border: 1px solid var(--accent); padding: 8px 15px; border-radius: 8px; font-weight: 600; cursor: pointer;">
          {''.join(f'<option value="{path}">{escape(label)}</option>' for path, label in narrativa_slugs.items())}
        </select>
      </div>
      <div id="md-viewer" class="markdown-body">
        <p class="muted">Cargando narrativa...</p>
      </div>
    </section>
  </main>
</body>
</html>
"""

    css = """
:root {
  --bg: #020617; /* Deep Midnight */
  --surface: rgba(15, 23, 42, 0.75);
  --surface-strong: rgba(30, 41, 59, 0.9);
  --text: #f8fafc;
  --muted: #94a3b8;
  --line: rgba(148, 163, 184, 0.2);
  
  /* Bluish Semantic Palette (Less Purple) */
  --accent: #2dd4bf;        /* Aquamarine */
  --accent-soft: rgba(45, 212, 191, 0.1);
  --warning: #fcd34d;       /* Amber */
  --warning-soft: rgba(252, 211, 77, 0.1);
  --danger: #fb7185;        /* Soft Coral/Rose */
  --danger-soft: rgba(251, 113, 133, 0.1);
  --info: #38bdf8;          /* Sky Blue */
  --info-soft: rgba(56, 189, 248, 0.1);
  --purple: #3b82f6;        /* Electric Blue (Shifted from Purple) */
  --purple-soft: rgba(59, 130, 246, 0.1);
  --chartreuse: #a3e635;    /* Electric Lime */
  
  --link: #0ea5e9;
  --sidebar-w: 260px;
  --glass-blur: blur(20px);
  --glass-saturate: saturate(160%);
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: 'Inter', system-ui, sans-serif;
  color: var(--text);
  background: var(--bg);
  background-image: 
    radial-gradient(circle at 10% 10%, rgba(56, 189, 248, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 90% 90%, rgba(59, 130, 246, 0.06) 0%, transparent 50%);
  background-attachment: fixed;
  display: flex;
  min-height: 100vh;
}

a {
  color: var(--accent);
  text-decoration: none;
  transition: all 0.2s;
  border-bottom: 1px solid transparent;
}

a:hover {
  opacity: 0.8;
  border-bottom-color: var(--accent);
}

.panel a {
  color: inherit;
}

/* Sidebar Layout */
.sidebar {
  width: var(--sidebar-w);
  background: rgba(17, 24, 39, 0.8);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  z-index: 100;
}

.sidebar-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--line);
}

.sidebar-header .logo {
  font-weight: 800;
  font-size: 1.25rem;
  color: #fff;
  letter-spacing: -0.02em;
}

.sidebar-header .version {
  font-size: 0.7rem;
  color: var(--muted);
  margin-top: 0.2rem;
}

.sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 0;
}

.nav-group {
  margin-bottom: 1.5rem;
}

.nav-group label {
  display: block;
  padding: 0 1.5rem 0.5rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
}

.nav-item {
  display: block;
  padding: 0.6rem 1.5rem;
  color: var(--text);
  text-decoration: none;
  font-size: 0.9rem;
  transition: 120ms ease;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background: var(--surface-strong);
  color: #fff;
}

.nav-item.active {
  background: var(--accent-soft);
  color: #fff;
  border-left-color: var(--accent);
}

.wiki-nav {
  color: var(--warning);
}

.content-wrapper {
  margin-left: var(--sidebar-w);
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
}

/* Enhanced Glassmorphism for Panels */
.panel {
  background: var(--surface);
  backdrop-filter: var(--glass-blur) var(--glass-saturate);
  -webkit-backdrop-filter: var(--glass-blur) var(--glass-saturate);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.2);
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.panel:hover {
  border-color: rgba(255, 255, 255, 0.15);
}

.panel-highlight {
  background: linear-gradient(135deg, rgba(17, 24, 39, 0.8) 0%, rgba(31, 41, 55, 0.9) 100%);
  border-color: var(--line);
  position: relative;
  overflow: hidden;
}

.panel-highlight::after {
  content: "";
  position: absolute;
  top: 0; right: 0;
  width: 150px; height: 150px;
  background: radial-gradient(circle at 100% 0%, var(--accent-soft) 0%, transparent 70%);
  pointer-events: none;
}

/* Group-Specific Accents for Visibility */
.panel[data-group="resumen"] { --group-color: var(--info); }
.panel[data-group="estado"]  { --group-color: var(--accent); }
.panel[data-group="ia"]      { --group-color: var(--purple); }
.panel[data-group="planeacion"] { --group-color: var(--warning); }
.panel[data-group="fuentes"] { --group-color: #6366f1; } /* Indigo */

.panel {
  border-left: 4px solid var(--line); /* Default border */
}

.panel[data-group] {
  border-left-color: var(--group-color);
}

.panel .eyebrow {
  color: var(--group-color) !important;
  font-weight: 700;
}

.panel h2 {
  background: linear-gradient(to right, #fff, var(--group-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.hero h1 {
  background: linear-gradient(135deg, #fff 0%, var(--info) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero {
  margin-bottom: 2rem;
}

h1, h2, h3 { 
  margin: 0 0 1rem; 
  color: #fff;
}

h1 { font-size: 2.2rem; }
h2 { font-size: 1.4rem; border-bottom: 1px solid var(--line); padding-bottom: 0.5rem; }

.lead {
  color: var(--muted);
  font-size: 1.1rem;
  line-height: 1.6;
}

/* Trace Links */
.trace-link {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background: var(--surface-strong);
  color: var(--accent);
  text-decoration: none;
  font-size: 0.85rem;
  border: 1px solid var(--line);
  transition: 120ms ease;
}

.trace-link:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}

/* Tables */
.table-container {
  overflow-x: auto;
  margin-top: 1rem;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--line);
}

th {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--muted);
  letter-spacing: 0.05em;
}

/* SIOT Distributed Observability Command Center */
.noc-shell {
  border-left-color: var(--danger);
  background:
    linear-gradient(135deg, rgba(127, 29, 29, 0.2), transparent 35%),
    linear-gradient(180deg, rgba(2, 6, 23, 0.96), rgba(15, 23, 42, 0.92));
}

.noc-kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
  margin: 1rem 0;
}

.noc-stat, .noc-node-card, .noc-alert, .noc-runbook-card {
  background: rgba(2, 6, 23, 0.72);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.9rem;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02);
}

.noc-stat span {
  color: var(--muted);
  display: block;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.noc-stat strong {
  display: block;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 1rem;
  margin-top: 0.35rem;
  word-break: break-word;
}

.noc-status {
  border: 1px solid currentColor;
  border-radius: 999px;
  display: inline-flex;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  padding: 0.18rem 0.48rem;
  text-transform: uppercase;
  white-space: nowrap;
}

.noc-status--ok, .noc-stat--ok { color: var(--chartreuse); }
.noc-status--degraded, .noc-stat--degraded { color: var(--warning); }
.noc-status--down, .noc-stat--down { color: var(--danger); }
.noc-status--stale, .noc-stat--stale { color: #f97316; }
.noc-status--unknown, .noc-stat--unknown { color: var(--muted); }
.noc-status--blocked_human_validation, .noc-stat--blocked_human_validation { color: var(--info); }

.noc-banner {
  border: 1px solid var(--line);
  border-radius: 10px;
  margin: 1rem 0;
  padding: 0.8rem 1rem;
  background: rgba(15, 23, 42, 0.82);
}

.noc-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin: 1rem 0;
  position: sticky;
  top: 0;
  z-index: 20;
  padding: 0.5rem 0;
  background: rgba(2, 6, 23, 0.88);
  backdrop-filter: blur(10px);
}

.noc-tab {
  background: rgba(15, 23, 42, 0.94);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--text);
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 800;
  padding: 0.48rem 0.78rem;
  text-transform: uppercase;
}

.noc-tab.is-active {
  background: var(--danger);
  border-color: var(--danger);
  color: #fff;
}

.noc-tab-panel {
  display: none;
}

.noc-tab-panel.is-active {
  display: block;
}

.noc-grid, .noc-alerts, .noc-runbook-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 0.8rem;
  margin: 1rem 0;
}

.noc-node-card {
  border-left: 4px solid var(--accent);
}

.noc-alert {
  border-left: 4px solid var(--muted);
}

.noc-alert--down { border-left-color: var(--danger); }
.noc-alert--degraded { border-left-color: var(--warning); }
.noc-alert--stale { border-left-color: #f97316; }
.noc-alert small, .noc-node-card small {
  color: var(--muted);
}

.noc-runbook-card details {
  margin-top: 0.75rem;
}

.noc-runbook-card summary {
  color: var(--accent);
  cursor: pointer;
  font-weight: 800;
}

.noc-runbook-card__header {
  align-items: center;
  display: flex;
  gap: 0.75rem;
  justify-content: space-between;
}

/* Token Overlay */
.token-overlay {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  width: 280px;
  background: rgba(22, 27, 34, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1.25rem;
  z-index: 200;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

.token-overlay.is-collapsed {
  height: 60px;
  overflow: hidden;
}

.token-overlay__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.token-overlay__eyebrow {
  font-size: 0.65rem;
  text-transform: uppercase;
  color: var(--accent);
  font-weight: 700;
}

.token-overlay__stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.token-overlay__stats article {
  background: var(--surface-strong);
  padding: 0.5rem;
  border-radius: 8px;
}

.token-overlay__stats span {
  display: block;
  font-size: 0.6rem;
  color: var(--muted);
}

.token-overlay__stats strong {
  font-size: 1rem;
  color: #fff;
}

.token-overlay__meter {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: var(--line);
  margin-bottom: 1rem;
}

.token-overlay__meter::-webkit-progress-value { background: var(--accent); }

.token-overlay__actions {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.token-overlay__actions button, .token-overlay__collapse {
  background: var(--surface-strong);
  border: 1px solid var(--line);
  color: var(--text);
  padding: 0.3rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  cursor: pointer;
}

.token-overlay__actions button:hover {
  background: var(--accent);
  color: #fff;
}

@media (max-width: 768px) {
  .sidebar { width: 0; display: none; }
  .content-wrapper { margin-left: 0; padding: 1rem; }
}

/* Premium Markdown Body Styles */
.markdown-body {
  line-height: 1.6;
  color: var(--text);
}

.markdown-body h1, .markdown-body h2, .markdown-body h3 {
  margin-top: 2rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--line);
  padding-bottom: 0.3rem;
}

.markdown-body blockquote {
  border-left: 4px solid var(--accent);
  background: var(--accent-soft);
  padding: 1rem 1.5rem;
  margin: 1.5rem 0;
  border-radius: 0 12px 12px 0;
  font-style: italic;
}

.markdown-body code {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  background: var(--surface-strong);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-size: 0.85em;
  color: var(--accent);
}

.markdown-body pre {
  background: #0f172a !important;
  padding: 1.5rem;
  border-radius: 12px;
  overflow-x: auto;
  border: 1px solid var(--line);
  margin: 1.5rem 0;
}

.markdown-body pre code {
  background: transparent;
  padding: 0;
  color: inherit;
  font-size: 0.9rem;
}

.markdown-body table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1.5rem 0;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--line);
}

.markdown-body th {
  background: linear-gradient(135deg, var(--surface-strong) 0%, var(--surface) 100%);
  color: var(--accent);
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}

.markdown-body tr:last-child td {
  border-bottom: none;
}

.markdown-body tr:hover td {
  background: rgba(255, 255, 255, 0.03);
}

.markdown-body ul, .markdown-body ol {
  padding-left: 1.5rem;
  margin: 1rem 0;
}

.markdown-body li {
  margin-bottom: 0.5rem;
}

.markdown-body {
  font-size: 1.05rem;
  line-height: 1.7;
  color: #e2e8f0;
}

.markdown-body h1, .markdown-body h2, .markdown-body h3 {
  margin-top: 2rem;
  color: var(--accent);
}

.markdown-body h1 { font-size: 1.8rem; border-bottom: 2px solid var(--accent-soft); padding-bottom: 0.5rem; }
.markdown-body h2 { font-size: 1.4rem; border-bottom: 1px solid var(--line); padding-bottom: 0.3rem; }

.markdown-body blockquote {
  border-left: 4px solid var(--accent);
  background: var(--accent-soft);
  padding: 1rem 1.5rem;
  margin: 1.5rem 0;
  border-radius: 0 8px 8px 0;
  color: #fff;
  font-style: italic;
}

.markdown-body code {
  background: var(--surface-strong);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-size: 0.9em;
  color: var(--warning);
}

.markdown-body pre code {
  background: transparent;
  color: inherit;
  padding: 0;
}

.markdown-body table {
  display: block;
  width: 100%;
  overflow-x: auto;
  border-collapse: collapse;
  margin: 1.5rem 0;
}

.markdown-body th {
  background: var(--surface-strong);
}

.markdown-body img {
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid var(--line);
  margin: 1rem 0;
}

.mermaid {
  background: rgba(2, 6, 23, 0.5);
  padding: 1.5rem;
  border-radius: 16px;
  border: 1px solid var(--line);
  display: flex;
  justify-content: center;
  margin: 2rem 0;
  backdrop-filter: var(--glass-blur);
}

/* Scrollbar Sidebar */
.sidebar-scroll::-webkit-scrollbar {
  width: 5px;
}
.sidebar-scroll::-webkit-scrollbar-thumb {
  background: var(--line);
  border-radius: 10px;
}
.sidebar-scroll::-webkit-scrollbar-track {
  background: transparent;
}
"""

    js = """
const panels = [...document.querySelectorAll('.panel')];
const searchInput = document.getElementById('panel-search');
const filterButtons = [...document.querySelectorAll('.filter-btn')];
const reviewToggle = document.querySelector('[data-review-toggle]');
const reviewContent = document.querySelector('[data-review-content]');
const mdSelector = document.getElementById('md-selector');
const mdViewer = document.getElementById('md-viewer');
const REVIEW_RAIL_STORE_KEY = 'siot-review-rail';

let reviewRailCollapsed = false;

// Diagnóstico de carga
function checkLibraries() {
  const status = {
    marked: typeof marked !== 'undefined',
    mermaid: typeof mermaid !== 'undefined',
    Prism: typeof Prism !== 'undefined'
  };
  console.log('SIOT Dashboard - Status:', status);
  return status;
}

// Configuración de Mermaid
try {
  if (typeof mermaid !== 'undefined') {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      themeVariables: {
        fontFamily: 'Inter, system-ui, sans-serif',
        primaryColor: '#2dd4bf',
        primaryTextColor: '#fff',
        primaryBorderColor: '#14b8a6',
        lineColor: '#94a3b8',
        secondaryColor: '#3b82f6',
        tertiaryColor: '#0f172a'
      }
    });
  }
} catch (e) {
  console.error('Error inicializando Mermaid:', e);
}

function loadReviewRailState() {
  try {
    return localStorage.getItem(REVIEW_RAIL_STORE_KEY) === 'collapsed';
  } catch {
    return false;
  }
}

function renderReviewRailState() {
  if (!reviewContent || !reviewToggle) return;
  reviewContent.style.display = reviewRailCollapsed ? 'none' : 'grid';
  reviewToggle.textContent = reviewRailCollapsed ? 'Mostrar' : 'Ocultar';
  try {
    localStorage.setItem(REVIEW_RAIL_STORE_KEY, reviewRailCollapsed ? 'collapsed' : 'expanded');
  } catch {}
}

function normalize(value) {
  return (value || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function applyFilters() {
  const query = normalize(searchInput?.value);
  const activeFilter = document.querySelector('.filter-btn.is-active')?.dataset.filter || 'all';
  panels.forEach((panel) => {
    const groupMatches = activeFilter === 'all' || panel.dataset.group === activeFilter;
    const textMatches = !query || normalize(panel.innerText).includes(query);
    panel.style.display = (groupMatches && textMatches) ? '' : 'none';
  });
}

function initializeNocTabs() {
  const tabs = [...document.querySelectorAll('[data-noc-tab]')];
  const tabPanels = [...document.querySelectorAll('[data-noc-panel]')];
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.nocTab;
      tabs.forEach((item) => item.classList.toggle('is-active', item === tab));
      tabPanels.forEach((panel) => {
        panel.classList.toggle('is-active', panel.dataset.nocPanel === target);
      });
    });
  });
}

function jumpToNarrative(path) {
  const viewerSection = document.getElementById('narrativa-sistema');
  if (mdSelector && window.SIOT_NARRATIVA && window.SIOT_NARRATIVA[path]) {
    mdSelector.value = path;
    loadMarkdown(path);
    viewerSection?.scrollIntoView({ behavior: 'smooth' });
    return true;
  }
  return false;
}

async function loadMarkdown(path) {
  if (!mdViewer) return;
  try {
    mdViewer.innerHTML = '<p class="muted">Cargando ' + path + '...</p>';
    if (!window.SIOT_NARRATIVA) throw new Error('No se encontraron datos de narrativa (window.SIOT_NARRATIVA)');
    
    const text = window.SIOT_NARRATIVA[path];
    if (!text) throw new Error('No se encontró el contenido para ' + path);
    
    // 1. Renderizar Markdown a HTML
    if (typeof marked === 'undefined') throw new Error('Marked.js no está disponible');
    mdViewer.innerHTML = marked.parse(text);
    
    // 2. Preparar bloques de Mermaid
    mdViewer.querySelectorAll('pre code.language-mermaid').forEach(code => {
      const pre = code.parentElement;
      const div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = code.textContent;
      pre.replaceWith(div);
    });

    // 3. Resaltar sintaxis con Prism
    if (typeof Prism !== 'undefined') {
      Prism.highlightAllUnder(mdViewer);
    }
    
    // 4. Corregir rutas de imágenes
    mdViewer.querySelectorAll('img').forEach(img => {
      const src = img.getAttribute('src');
      if (src && !src.startsWith('http') && !src.startsWith('data:') && !src.startsWith('/')) {
        // Si la ruta es interna al dashboard, quitar el prefijo
        if (src.startsWith('06_dashboard/generado/')) {
          img.src = src.replace('06_dashboard/generado/', '');
        } else {
          // Si es relativa a la raíz, subir niveles
          img.src = '../../' + src;
        }
      }
    });

    // 5. Renderizar diagramas de Mermaid
    if (typeof mermaid !== 'undefined') {
      await mermaid.run({
        nodes: mdViewer.querySelectorAll('.mermaid'),
      });
    }
    
  } catch (err) {
    console.error('Error cargando markdown:', err);
    mdViewer.innerHTML = '<div class="panel danger"><strong>Error de renderizado:</strong> ' + err.message + '</div>';
  }
}

// Inicialización principal
document.addEventListener('DOMContentLoaded', () => {
  const libStatus = checkLibraries();
  
  if (!libStatus.marked) {
    const err = document.createElement('div');
    err.className = 'panel danger';
    err.innerHTML = '<strong>Error crítico:</strong> Las librerías de renderizado no cargaron. Verifica tu conexión.';
    document.querySelector('main')?.prepend(err);
  }

  mdSelector?.addEventListener('change', (e) => loadMarkdown(e.target.value));

  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      filterButtons.forEach((item) => item.classList.remove('is-active'));
      button.classList.add('is-active');
      applyFilters();
    });
  });

  searchInput?.addEventListener('input', applyFilters);

  reviewRailCollapsed = loadReviewRailState();
  reviewToggle?.addEventListener('click', () => {
    reviewRailCollapsed = !reviewRailCollapsed;
    renderReviewRailState();
  });

  renderReviewRailState();
  initializeNocTabs();

  // Intercepción de enlaces MD
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;
    const href = link.getAttribute('href');
    if (href && (href.endsWith('.md') || link.classList.contains('narrative-trigger'))) {
      const cleanPath = href.split('#')[0].replace(/^(\.\.\/)+/, '');
      const knownPath = Object.keys(window.SIOT_NARRATIVA || {}).find(k => k === cleanPath || k.endsWith(cleanPath));
      if (knownPath) {
        if (jumpToNarrative(knownPath)) {
          e.preventDefault();
        }
      }
    }
  });

  // Carga inicial de narrativa
  if (mdSelector) loadMarkdown(mdSelector.value);
});

if ('serviceWorker' in navigator && window.location.protocol.startsWith('http')) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  });
}
"""

    manifest = """{
  "name": "Sistema Operativo de la Tesis IoT Pachuca",
  "short_name": "Tesis IoT",
  "start_url": "./index.html",
  "display": "standalone",
  "background_color": "#f4f4f0",
  "theme_color": "#0f766e",
  "icons": [
    {
      "src": "./icon.svg",
      "sizes": "any",
      "type": "image/svg+xml",
      "purpose": "any maskable"
    }
  ]
}"""

    service_worker = """
const CACHE_NAME = 'tesis-dashboard-v1';
const ASSETS = ['./', './index.html', './estilos.css', './app.js', './manifest.webmanifest', './sw.js', './icon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
"""

    icon = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="40" fill="#f4f4f0"/>
  <rect x="24" y="24" width="208" height="208" rx="32" fill="#0f766e"/>
  <path d="M64 78h128" stroke="#d8f0eb" stroke-width="14" stroke-linecap="round"/>
  <path d="M64 128h92" stroke="#d8f0eb" stroke-width="14" stroke-linecap="round"/>
  <path d="M64 178h128" stroke="#d8f0eb" stroke-width="14" stroke-linecap="round"/>
  <circle cx="184" cy="128" r="18" fill="#f4f4f0"/>
</svg>
"""

    html_path = ROOT / "06_dashboard" / "generado" / "index.html"
    css_path = ROOT / "06_dashboard" / "generado" / "estilos.css"
    js_path = ROOT / dashboard["salida"]["js"]
    manifest_path = ROOT / dashboard["salida"]["manifest"]
    sw_path = ROOT / dashboard["salida"]["service_worker"]
    icon_path = ROOT / dashboard["salida"]["icon"]
    write_text_if_changed(html_path, html)
    write_text_if_changed(css_path, css.strip() + "\n")
    write_text_if_changed(js_path, js.strip() + "\n")
    write_text_if_changed(manifest_path, manifest.strip() + "\n")
    write_text_if_changed(sw_path, service_worker.strip() + "\n")
    write_text_if_changed(icon_path, icon.strip() + "\n")

    print(f"Dashboard generado en {html_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
