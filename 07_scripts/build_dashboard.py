from __future__ import annotations

import json
from html import escape
import os
from pathlib import Path

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
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body_html)}</tbody></table>"


def render_table_html(headers: list[str], rows: list[list[str]]) -> str:
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_html = []
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        body_html.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body_html)}</tbody></table>"


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
    public_bundle = load_optional_json(publicacion["salida"]["manifest"], {})
    decisiones = list_markdown_entries("00_sistema_tesis/decisiones")[:5]
    reportes_semanales = list_markdown_entries("00_sistema_tesis/reportes_semanales")
    bitacoras = list_markdown_entries("00_sistema_tesis/bitacora")
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
            "Resumen general",
            " ".join(
                [
                    source_link("sistema_tesis.yaml", "00_sistema_tesis/config/sistema_tesis.yaml"),
                    source_link("dashboard.yaml", "00_sistema_tesis/config/dashboard.yaml"),
                ]
            ),
            "Estado global, fase actual y siguiente entregable",
        ],
        [
            "Seguridad e Integridad",
            " ".join(
                [
                    source_link("security_report.json", "00_sistema_tesis/config/security_report.json"),
                    source_link("integrity_manifest.json", "00_sistema_tesis/config/integrity_manifest.json"),
                ]
            ),
            "Reporte de auditoría unificada y estado de integridad",
        ],
        [
            "Bloque activo",
            " ".join(
                [
                    source_link("sistema_tesis.yaml", "00_sistema_tesis/config/sistema_tesis.yaml"),
                    source_link("bloques.yaml", "00_sistema_tesis/config/bloques.yaml"),
                ]
            ),
            "Bloque vigente, criterio de salida y dependencias",
        ],
        [
            "Hipótesis activas",
            " ".join(
                [
                    source_link("hipotesis.yaml", "00_sistema_tesis/config/hipotesis.yaml"),
                    source_link("bloques.yaml", "00_sistema_tesis/config/bloques.yaml"),
                ]
            ),
            "Hipótesis, evidencia disponible y bloques asociados",
        ],
        [
            "Economía de uso",
            " ".join(
                [
                    source_link("ia_gobernanza.yaml", "00_sistema_tesis/config/ia_gobernanza.yaml"),
                    source_link("bitacora/", "00_sistema_tesis/bitacora"),
                    source_link("reportes_semanales/", "00_sistema_tesis/reportes_semanales"),
                ]
            ),
            "Patrones de consumo, recomendación y matriz operativa",
        ],
        [
            "Política de modelos",
            source_link("ia_gobernanza.yaml", "00_sistema_tesis/config/ia_gobernanza.yaml"),
            "Modelo base por tramo de trabajo, nivel recomendado y criterio de escalamiento",
        ],
        [
            "Backlog y riesgos",
            " ".join(
                [
                    source_link("backlog.csv", "01_planeacion/backlog.csv"),
                    source_link("riesgos.csv", "01_planeacion/riesgos.csv"),
                    source_link("entregables.csv", "01_planeacion/entregables.csv"),
                ]
            ),
            "Trabajo pendiente, prioridades y mitigaciones",
        ],
        [
            "Operación humana y publicación",
            " ".join(
                [
                    source_link("manual_operacion_humana.md", "00_sistema_tesis/manual_operacion_humana.md"),
                    source_link("publicacion.yaml", "00_sistema_tesis/config/publicacion.yaml"),
                    source_link("bundle_publico/", publicacion["salida"]["directorio"]),
                ]
            ),
            "Ruta humana principal, separación privado/público y bundle sanitizado derivado",
        ],
        [
            "Presupuesto de tokens API",
            " ".join(
                [
                    source_link("token_budget.json", "00_sistema_tesis/config/token_budget.json"),
                    source_link("token_usage_snapshot.json", "00_sistema_tesis/config/token_usage_snapshot.json"),
                ]
            ),
            "Presupuestos diarios/semanales, consumo real sincronizado y recomendaciones de accion",
        ],
    ]

    token_overlay_html = f"""
  <aside class="token-overlay" id="token-overlay" data-default-budget="{daily_budget_tokens}" data-default-used="{daily_tokens_used}" aria-label="Presupuesto local de tokens">
    <div class="token-overlay__header">
      <div>
        <p class="token-overlay__eyebrow">Economía de tokens</p>
        <h2>Presupuesto visible</h2>
      </div>
      <button class="token-overlay__collapse" type="button" data-token-collapse aria-pressed="false">
        Ocultar
      </button>
    </div>
    <p class="token-overlay__disclaimer">
      Estimación local para sostener disciplina de uso. No muestra un presupuesto interno de Codex.
    </p>
    <div class="token-overlay__stats">
      <article>
        <span>Presupuesto</span>
        <strong data-token-budget-display>{daily_budget_tokens}</strong>
      </article>
      <article>
        <span>Consumido</span>
        <strong data-token-used-display>{daily_tokens_used}</strong>
      </article>
      <article>
        <span>Restante</span>
        <strong data-token-remaining-display>{daily_tokens_remaining}</strong>
      </article>
      <article>
        <span>Uso API hoy</span>
        <strong data-token-ratio-display>{format_ratio(daily_tokens_ratio)}</strong>
      </article>
    </div>
    <label class="token-overlay__field">
      <span>Presupuesto del día</span>
      <input data-token-budget-input type="number" min="0" step="100" value="{daily_budget_tokens}">
    </label>
    <label class="token-overlay__field">
      <span>Consumido acumulado</span>
      <input data-token-used-input type="number" min="0" step="50" value="{daily_tokens_used}">
    </label>
    <progress class="token-overlay__meter" data-token-meter value="{daily_tokens_used}" max="{daily_budget_tokens}">0%</progress>
    <p class="token-overlay__hint" data-token-hint>Meta: mantener la salida útil sin inflar el consumo.</p>
    <div class="token-overlay__actions">
      <button type="button" data-token-adjust="50">+50</button>
      <button type="button" data-token-adjust="250">+250</button>
      <button type="button" data-token-adjust="-100">-100</button>
      <button type="button" data-token-reset>Reiniciar</button>
    </div>
  </aside>
"""

    html = f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0f766e">
  <title>Dashboard | {escape(sistema["identidad_proyecto"]["nombre_corto"])}</title>
  <link rel="stylesheet" href="estilos.css">
  <link rel="manifest" href="manifest.webmanifest">
  <script defer src="app.js"></script>
</head>
<body>
{token_overlay_html}
  <header class="hero">
    <div>
      <p class="eyebrow">Sistema Operativo de la Tesis</p>
      <h1>{escape(sistema["titulo_vigente"])}</h1>
      <p class="lead">{escape(sistema["resumen_problema"])}</p>
    </div>
    <div class="hero-meta">
      <div class="meta-card">
        <span class="meta-label">Versión</span>
        <strong>{escape(sistema["version"])}</strong>
      </div>
      <div class="meta-card">
        <span class="meta-label">Estado global</span>
        <strong>{escape(sistema["estado_global"])}</strong>
      </div>
      <div class="meta-card">
        <span class="meta-label">Build</span>
        <strong>{escape(generated_at)}</strong>
      </div>
    </div>
  </header>

  <nav class="topnav">
    <a href="#resumen-general">Resumen</a>
    <a href="#que-revisar-siempre">Revisión</a>
    <a href="wiki/index.html">Wiki</a>
      <a href="#seguridad-integridad">Seguridad</a>
      <a href="#bloque-activo">Bloque</a>
    <a href="#hipotesis-activas">Hipótesis</a>
    <a href="#economia-uso">Economía</a>
    <a href="#politica-modelos">Modelos</a>
    <a href="#presupuesto-tokens-api">Cuota API</a>
    <a href="#matriz-tareas">Matriz</a>
    <a href="#backlog-prioritario">Backlog</a>
    <a href="#riesgos-abiertos">Riesgos</a>
    <a href="#fuentes-verdad">Fuentes</a>
    <a href="#trazabilidad-dashboard">Trazabilidad</a>
    <a href="#despliegue-orange-pi">Despliegue</a>
  </nav>

  <aside class="review-dock" id="review-dock" aria-label="Accesos rápidos de revisión">
    <a class="review-dock__item" href="#que-revisar-siempre" title="Qué revisar siempre">RV</a>
    <a class="review-dock__item" href="{escape(relative_from_generated('00_sistema_tesis/manual_operacion_humana.md'))}" target="_blank" rel="noreferrer" title="Manual humano">MH</a>
    <a class="review-dock__item" href="{escape(relative_from_generated('00_sistema_tesis/config/sistema_tesis.yaml'))}" target="_blank" rel="noreferrer" title="Sistema">SY</a>
    <a class="review-dock__item" href="{escape(relative_from_generated('01_planeacion/backlog.csv'))}" target="_blank" rel="noreferrer" title="Backlog">BL</a>
    <a class="review-dock__item" href="{escape(relative_from_generated('01_planeacion/riesgos.csv'))}" target="_blank" rel="noreferrer" title="Riesgos">RG</a>
    <a class="review-dock__item" href="wiki/index.html" title="Wiki">WK</a>
    <a class="review-dock__item" href="{escape(relative_from_generated(publicacion['salida']['directorio'] + '/index.md'))}" target="_blank" rel="noreferrer" title="Público">PB</a>
  </aside>

  <section class="toolbar">
    <div class="toolbar-block">
      <label for="panel-search">Filtrar paneles</label>
      <input id="panel-search" type="search" placeholder="Escribe tema, riesgo, hipótesis, tarea o fuente">
    </div>
    <div class="toolbar-block toolbar-actions">
      <button class="filter-btn is-active" data-filter="all" type="button">Todo</button>
      <button class="filter-btn" data-filter="estado" type="button">Estado</button>
      <button class="filter-btn" data-filter="ia" type="button">IA</button>
      <button class="filter-btn" data-filter="planeacion" type="button">Planeación</button>
      <button class="filter-btn" data-filter="fuentes" type="button">Fuentes</button>
    </div>
  </section>

  <main class="layout">
    <section id="resumen-general" class="panel panel-highlight" data-group="estado">
      <h2>Resumen general</h2>
      <div class="stats">
        <article><span>Bloque activo</span><strong>{escape(sistema["bloque_activo"])}</strong></article>
        <article><span>Fase actual</span><strong>{escape(sistema["fase_actual"])}</strong></article>
        <article><span>Siguiente entregable</span><strong>{escape(sistema["siguiente_entregable"])}</strong></article>
        <article><span>Riesgo principal</span><strong>{escape(sistema["riesgo_principal_abierto"])}</strong></article>
      </div>
      <p class="trace-row">Fuentes: {source_link("sistema_tesis.yaml", "00_sistema_tesis/config/sistema_tesis.yaml")} {source_link("dashboard.yaml", "00_sistema_tesis/config/dashboard.yaml")}</p>
      <p class="trace-row">Wiki verificable: <a class="trace-link" href="wiki/index.html">Abrir guía derivada</a></p>
      <p class="notice">{escape(dashboard["reglas"]["aviso_no_editar"])}</p>
    </section>

    <section id="operacion-humana" class="panel panel-highlight" data-group="estado">
      <h2>Operación humana y superficies</h2>
      <div class="stats">
        <article><span>IA</span><strong>opcional</strong></article>
        <article><span>Superficie privada</span><strong>canónica</strong></article>
        <article><span>Superficie pública</span><strong>sanitizada</strong></article>
        <article><span>Bundle público</span><strong>{escape(str(public_bundle.get("status", "pendiente")))}</strong></article>
      </div>
      <p class="lead">El sistema debe poder retomarse, auditarse y publicarse mediante rutas humanas explícitas. La base privada conserva la trazabilidad completa; la capa pública es un derivado sanitizado y no editable a mano.</p>
      <ul class="list">
        <li><strong>Retomar:</strong> `python 07_scripts/tesis.py status` y `python 07_scripts/tesis.py next`</li>
        <li><strong>Auditar:</strong> `python 07_scripts/tesis.py doctor` y `python 07_scripts/build_all.py`</li>
        <li><strong>Publicar:</strong> `python 07_scripts/tesis.py publish --build`</li>
      </ul>
      <p class="trace-row">Fuentes: {source_link("manual_operacion_humana.md", "00_sistema_tesis/manual_operacion_humana.md")} {source_link("publicacion.yaml", "00_sistema_tesis/config/publicacion.yaml")} {source_link("bundle_publico/", publicacion["salida"]["directorio"])}</p>
    </section>

    <section id="que-revisar-siempre" class="panel panel-highlight panel-sticky" data-group="estado">
      <div class="review-rail__header">
        <div>
          <h2>Qué revisar siempre</h2>
          <p class="lead">Rail de control para no perder el hilo. Úsalo al retomar, antes de auditar y antes de publicar.</p>
        </div>
        <button class="review-rail__toggle" type="button" data-review-toggle aria-expanded="true">Ocultar</button>
      </div>
      <div class="review-link-grid" data-review-content>
        <a class="review-link-card" href="{escape(relative_from_generated('00_sistema_tesis/manual_operacion_humana.md'))}" target="_blank" rel="noreferrer">
          <strong>Manual humano</strong>
          <span>Ruta principal de operación</span>
        </a>
        <a class="review-link-card" href="{escape(relative_from_generated('00_sistema_tesis/config/sistema_tesis.yaml'))}" target="_blank" rel="noreferrer">
          <strong>Sistema</strong>
          <span>Estado global y reglas base</span>
        </a>
        <a class="review-link-card" href="{escape(relative_from_generated('01_planeacion/backlog.csv'))}" target="_blank" rel="noreferrer">
          <strong>Backlog</strong>
          <span>Qué sigue exactamente</span>
        </a>
        <a class="review-link-card" href="{escape(relative_from_generated('01_planeacion/riesgos.csv'))}" target="_blank" rel="noreferrer">
          <strong>Riesgos</strong>
          <span>Qué puede romper el avance</span>
        </a>
        <a class="review-link-card" href="{escape(relative_from_generated('00_sistema_tesis/bitacora/matriz_trazabilidad.md'))}" target="_blank" rel="noreferrer">
          <strong>Trazabilidad</strong>
          <span>Validaciones y evidencia</span>
        </a>
        <a class="review-link-card" href="wiki/index.html">
          <strong>Wiki</strong>
          <span>Lectura derivada humana</span>
        </a>
        <a class="review-link-card" href="index.html">
          <strong>Dashboard</strong>
          <span>Vista operativa actual</span>
        </a>
        <a class="review-link-card" href="{escape(relative_from_generated(publicacion['salida']['directorio'] + '/index.md'))}" target="_blank" rel="noreferrer">
          <strong>Público</strong>
          <span>Bundle sanitizado</span>
        </a>
      </div>
      <p class="trace-row">Revisión mínima recomendada antes de retomar, auditar o publicar.</p>
    </section>

    <section id="seguridad-integridad" class="panel" data-group="ia">
      <h2>Seguridad e Integridad</h2>
      <div class="stats">
        <article><span>Trust Score</span><strong>{trust_score}%</strong></article>
        <article><span>Auditadas</span><strong>{sec_summary.get("total", 0)}</strong></article>
        <article><span>Exitosas</span><strong>{sec_summary.get("passed", 0)}</strong></article>
        <article><span>Críticas</span><strong>{sec_summary.get("critical_failures", 0)}</strong></article>
      </div>
      {render_table_html(["Auditoría", "Resultado", "Nivel", "Detalle"], security_rows)}
      <p class="trace-row">Insignias: 
        <img src="badges/security_status.svg" alt="Security Status">
        <img src="badges/integrity.svg" alt="Integrity Status">
        <img src="badges/ledger.svg" alt="Ledger Status">
      </p>
      <p class="trace-row">Fuentes: {source_link("security_report.json", "00_sistema_tesis/config/security_report.json")} {source_link("integrity_manifest.json", "00_sistema_tesis/config/integrity_manifest.json")}</p>
    </section>

    <section id="bloque-activo" class="panel" data-group="estado">
      <h2>Bloque activo</h2>
      <p class="tag">{escape(active_block["id"])} · {escape(active_block["tipo"])} · {escape(active_block["estado"])}</p>
      <h3>{escape(active_block["nombre"])}</h3>
      <p>{escape(active_block["descripcion"])}</p>
      <p><strong>Criterio de salida:</strong> {escape(active_block["criterio_salida"])}</p>
      <p><strong>Entregables:</strong> {escape(", ".join(active_block["entregables"]))}</p>
      <p class="trace-row">Fuentes: {source_link("sistema_tesis.yaml", "00_sistema_tesis/config/sistema_tesis.yaml")} {source_link("bloques.yaml", "00_sistema_tesis/config/bloques.yaml")}</p>
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
      <p class="trace-row">Fuentes: {source_link("hipotesis.yaml", "00_sistema_tesis/config/hipotesis.yaml")} {source_link("bloques.yaml", "00_sistema_tesis/config/bloques.yaml")}</p>
    </section>

    <section class="panel" data-group="fuentes">
      <h2>Decisiones recientes</h2>
      <ul class="list">
        {''.join(f"<li><strong>{escape(item['fecha'])}</strong> · {escape(item['titulo'])}<br><span>{escape(item['archivo'])}</span></li>" for item in decisiones)}
      </ul>
      <p class="trace-row">Fuente: {source_link("decisiones/", "00_sistema_tesis/decisiones")}</p>
    </section>

    <section id="economia-uso" class="panel" data-group="ia">
      <h2>Economía de uso</h2>
      <p class="tag">{"Fuente: " + escape(latest_weekly_report["titulo"]) if latest_weekly_report else "Sin resumen semanal"}</p>
      <ul class="list">
        {''.join(f"<li>{escape(item)}</li>" for item in economy_bullets) if economy_bullets else "<li>No hay señales semanales de economía de uso registradas todavía.</li>"}
      </ul>
      <p class="trace-row">Fuentes: {source_link("ia_gobernanza.yaml", "00_sistema_tesis/config/ia_gobernanza.yaml")} {source_link("bitacora/", "00_sistema_tesis/bitacora")} {source_link("reportes_semanales/", "00_sistema_tesis/reportes_semanales")}</p>
    </section>

    <section id="presupuesto-tokens-api" class="panel panel-highlight" data-group="ia">
      <h2>Presupuesto y Consumo API (diario/semanal)</h2>
      <p class="tag">Estado de sincronizacion: {escape(token_snapshot_status)} | {escape(token_generated_at)} | TZ: {escape(token_source_tz)}</p>
      <p>{escape(token_snapshot_message)}</p>
      {render_table(
          ["Metrica", "Diario", "Semanal"],
          [
              ["Tokens presupuesto", str(daily_budget_tokens), str(weekly_budget_tokens)],
              ["Tokens usados", str(daily_tokens_used), str(weekly_tokens_used)],
              ["Tokens restantes", str(daily_tokens_remaining), str(weekly_tokens_remaining)],
              ["Uso de tokens", format_ratio(daily_tokens_ratio), format_ratio(weekly_tokens_ratio)],
              ["Costo presupuesto", format_usd(daily_budget_usd), format_usd(weekly_budget_usd)],
              ["Costo usado", format_usd(daily_usd_used), format_usd(weekly_usd_used)],
              ["Costo restante", format_usd(daily_usd_remaining), format_usd(weekly_usd_remaining)],
              ["Solicitudes", str(daily_requests), str(weekly_requests)],
          ],
      )}
      <p><strong>Modelos con mayor consumo semanal:</strong> {token_top_models}</p>
      <h3>Acciones recomendadas antes de agotar cuota</h3>
      <ul class="list">
        {''.join(f"<li>{escape(item)}</li>" for item in token_recommendation_items)}
      </ul>
      <p class="trace-row">Fuentes: {source_link("token_budget.json", "00_sistema_tesis/config/token_budget.json")} {source_link("token_usage_snapshot.json", "00_sistema_tesis/config/token_usage_snapshot.json")}</p>
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
      <p class="trace-row">Fuentes: {source_link("bitacora/", "00_sistema_tesis/bitacora")} {source_link("reportes_semanales/", "00_sistema_tesis/reportes_semanales")}</p>
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
      <p class="trace-row">Fuentes: {source_link("bitacora/", "00_sistema_tesis/bitacora")} {source_link("reportes_semanales/", "00_sistema_tesis/reportes_semanales")}</p>
    </section>

    <section class="panel panel-highlight" data-group="ia">
      <h2>Recomendación operativa de uso</h2>
      <p>{escape(usage_recommendation)}</p>
      <p class="trace-row">Fuentes: {source_link("ia_gobernanza.yaml", "00_sistema_tesis/config/ia_gobernanza.yaml")} {source_link("bitacora/", "00_sistema_tesis/bitacora")} {source_link("reportes_semanales/", "00_sistema_tesis/reportes_semanales")}</p>
    </section>

    <section id="matriz-tareas" class="panel" data-group="ia">
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
      <h2>Politica de modelos y razonamiento</h2>
      <p class="lead">Regla operativa: un modelo base por tramo de trabajo. Cambia solo cuando cambie la clase de tarea o el costo del error.</p>
      {render_table(
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
      <p class="trace-row">Fuente: {source_link("ia_gobernanza.yaml", "00_sistema_tesis/config/ia_gobernanza.yaml")}</p>
    </section>

    <section id="backlog-prioritario" class="panel" data-group="planeacion">
      <h2>Backlog prioritario</h2>
      {render_table(
          ["Task", "Bloque", "Tarea", "Prioridad", "Estado", "Fecha objetivo"],
          [
              [item["task_id"], item["bloque"], item["tarea"], item["prioridad"], item["estado"], item["fecha_objetivo"]]
              for item in top_backlog[:8]
          ],
      )}
      <p class="trace-row">Fuentes: {source_link("backlog.csv", "01_planeacion/backlog.csv")} {source_link("entregables.csv", "01_planeacion/entregables.csv")}</p>
    </section>

    <section id="riesgos-abiertos" class="panel" data-group="planeacion">
      <h2>Riesgos abiertos</h2>
      {render_table(
          ["Risk", "Tipo", "Probabilidad", "Impacto", "Mitigación"],
          [
              [item["risk_id"], item["tipo"], item["probabilidad"], item["impacto"], item["mitigacion"]]
              for item in open_risks[:6]
          ],
      )}
      <p class="trace-row">Fuente: {source_link("riesgos.csv", "01_planeacion/riesgos.csv")}</p>
    </section>

    <section id="estado-archivos-canonicos" class="panel" data-group="fuentes">
      <h2>Estado de archivos canónicos</h2>
      {render_table(
          ["Clave", "Ruta", "Existe", "Última modificación"],
          [
              [item["clave"], item["ruta"], "sí" if item["existe"] else "no", item["modificado"]]
              for item in file_status
          ],
      )}
      <p class="trace-row">Fuente: {source_link("sistema_tesis.yaml", "00_sistema_tesis/config/sistema_tesis.yaml")}</p>
    </section>

    <section id="fuentes-verdad" class="panel panel-highlight" data-group="fuentes">
      <h2>Explorador de fuentes de verdad</h2>
      {render_table_html(["Clave", "Ruta canónica", "Existe", "Última modificación"], source_explorer_rows)}
    </section>

    <section id="trazabilidad-dashboard" class="panel" data-group="fuentes">
      <h2>Mapa de trazabilidad del dashboard</h2>
      {render_table_html(["Panel", "Fuentes", "Qué se lee"], traceability_rows)}
    </section>

    <section id="despliegue-orange-pi" class="panel panel-highlight" data-group="fuentes">
      <h2>Despliegue ligero y modo Orange Pi</h2>
      <p class="lead">La interfaz se genera como artefacto estático enriquecido, con manifiesto, service worker e icono, lista para servirse localmente en una Orange Pi 5 Plus con un servidor web mínimo.</p>
      <div class="deploy-grid">
        <article>
          <span>Artefactos de app</span>
          <p>{source_link("index.html", dashboard["salida"]["html"])} {source_link("estilos.css", dashboard["salida"]["css"])} {source_link("app.js", dashboard["salida"]["js"])} {source_link("manifest.webmanifest", dashboard["salida"]["manifest"])} {source_link("sw.js", dashboard["salida"]["service_worker"])} {source_link("icon.svg", dashboard["salida"]["icon"])}</p>
        </article>
        <article>
          <span>Servidor local</span>
          <pre class="code-block">cd 06_dashboard/generado
python -m http.server 8080</pre>
        </article>
        <article>
          <span>Instalación</span>
          <p>Abre `http://localhost:8080/` en Chromium, verifica el manifiesto y usa “Instalar aplicación” cuando el navegador lo ofrezca.</p>
        </article>
      </div>
    </section>
  </main>
</body>
</html>
"""

    css = """
:root {
  --bg: #f4f4f0;
  --surface: #ffffff;
  --surface-strong: #f0ebe1;
  --text: #1b2430;
  --muted: #52606d;
  --line: #d7d2c8;
  --accent: #0f766e;
  --accent-soft: #d8f0eb;
  --warning: #9a6700;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  color: var(--text);
  background:
    radial-gradient(circle at top right, rgba(15, 118, 110, 0.08), transparent 24rem),
    linear-gradient(180deg, #f8f6f1 0%, var(--bg) 100%);
}

.hero {
  padding: 2.5rem 1.25rem 1.5rem;
  display: grid;
  gap: 1rem;
  border-bottom: 1px solid var(--line);
}

.topnav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  padding: 0 1.25rem 1rem;
}

.topnav a,
.trace-link,
.filter-btn {
  text-decoration: none;
  font-family: "Segoe UI", Tahoma, sans-serif;
  transition: 160ms ease;
}

.topnav a {
  padding: 0.45rem 0.75rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--line);
  color: var(--muted);
}

.topnav a:hover,
.trace-link:hover,
.filter-btn:hover,
.filter-btn.is-active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.toolbar {
  padding: 0 1.25rem 1.25rem;
  display: grid;
  gap: 0.75rem;
}

.toolbar-block {
  display: grid;
  gap: 0.45rem;
}

.toolbar-block label {
  font-family: "Segoe UI", Tahoma, sans-serif;
  color: var(--muted);
  font-size: 0.82rem;
}

.toolbar input {
  width: 100%;
  padding: 0.95rem 1rem;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.86);
  font: inherit;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.filter-btn {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.5rem 0.8rem;
  background: rgba(255, 255, 255, 0.78);
  color: var(--muted);
  cursor: pointer;
}

.eyebrow {
  margin: 0 0 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
  color: var(--accent);
}

h1, h2, h3 { margin: 0 0 0.75rem; }
h1 { font-size: clamp(1.8rem, 4vw, 3rem); line-height: 1.15; max-width: 20ch; }
h2 { font-size: 1.2rem; }
h3 { font-size: 1.05rem; }

.lead {
  max-width: 72ch;
  color: var(--muted);
  line-height: 1.6;
}

.hero-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  gap: 0.75rem;
}

.meta-card, .panel {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(6px);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1rem;
  box-shadow: 0 8px 30px rgba(27, 36, 48, 0.05);
}

.meta-label, .tag, .notice, th {
  font-family: "Segoe UI", Tahoma, sans-serif;
}

.meta-label {
  display: block;
  color: var(--muted);
  font-size: 0.8rem;
  margin-bottom: 0.35rem;
}

.layout {
  padding: 1.25rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: 1rem;
}

.panel-highlight {
  grid-column: 1 / -1;
  background: linear-gradient(135deg, var(--surface) 0%, var(--surface-strong) 100%);
}

.panel-sticky {
  position: sticky;
  top: 1rem;
  align-self: start;
  z-index: 5;
}

.review-rail__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

.review-rail__toggle {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.84);
  color: var(--muted);
  cursor: pointer;
  font-family: "Segoe UI", Tahoma, sans-serif;
  padding: 0.45rem 0.75rem;
  transition: 160ms ease;
}

.review-rail__toggle:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}

.trace-row {
  margin: 0.9rem 0 0;
  color: var(--muted);
  font-family: "Segoe UI", Tahoma, sans-serif;
  font-size: 0.84rem;
  line-height: 1.5;
}

.trace-link {
  display: inline-flex;
  align-items: center;
  margin-right: 0.35rem;
  margin-top: 0.25rem;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid rgba(15, 118, 110, 0.16);
}

.deploy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
  gap: 0.75rem;
}

.review-link-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem;
  margin-top: 1rem;
}

.review-link-grid.is-collapsed {
  display: none;
}

.review-link-card {
  display: grid;
  gap: 0.2rem;
  padding: 0.9rem;
  border-radius: 14px;
  text-decoration: none;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(15, 118, 110, 0.18);
  color: var(--text);
  transition: 160ms ease;
}

.review-link-card strong {
  font-family: "Segoe UI", Tahoma, sans-serif;
  color: var(--accent);
  font-size: 0.88rem;
}

.review-link-card span {
  color: var(--muted);
  font-family: "Segoe UI", Tahoma, sans-serif;
  font-size: 0.82rem;
  line-height: 1.35;
}

.review-link-card:hover {
  transform: translateY(-1px);
  border-color: var(--accent);
  box-shadow: 0 10px 24px rgba(15, 118, 110, 0.08);
}

.review-dock {
  position: fixed;
  left: 1rem;
  top: 9.5rem;
  z-index: 18;
  display: grid;
  gap: 0.45rem;
}

.review-dock__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 999px;
  border: 1px solid rgba(15, 118, 110, 0.18);
  background: rgba(255, 255, 255, 0.9);
  color: var(--accent);
  text-decoration: none;
  font-family: "Segoe UI", Tahoma, sans-serif;
  font-size: 0.78rem;
  font-weight: 700;
  box-shadow: 0 8px 20px rgba(27, 36, 48, 0.08);
  transition: 160ms ease;
}

.review-dock__item:hover {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
  transform: translateY(-1px);
}

.deploy-grid article {
  padding: 0.9rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--line);
}

.deploy-grid span {
  display: block;
  color: var(--muted);
  font-family: "Segoe UI", Tahoma, sans-serif;
  font-size: 0.8rem;
  margin-bottom: 0.35rem;
}

.code-block {
  margin: 0;
  padding: 0.9rem;
  border-radius: 12px;
  background: #112321;
  color: #f7f6f0;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.88rem;
  overflow-x: auto;
}

.panel.is-hidden {
  display: none;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 0.75rem;
  margin: 1rem 0;
}

.stats article {
  padding: 0.85rem;
  border-radius: 12px;
  background: var(--accent-soft);
  border: 1px solid rgba(15, 118, 110, 0.18);
}

.stats span {
  display: block;
  color: var(--muted);
  font-family: "Segoe UI", Tahoma, sans-serif;
  font-size: 0.82rem;
  margin-bottom: 0.3rem;
}

.stats strong {
  font-size: 1rem;
}

.tag {
  display: inline-block;
  margin-bottom: 0.75rem;
  color: var(--accent);
  background: var(--accent-soft);
  border-radius: 999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.8rem;
}

    .notice {
      margin: 0.75rem 0 0;
      color: var(--warning);
    }

    .token-overlay {
      position: fixed;
      top: 1rem;
      right: 1rem;
      z-index: 30;
      width: min(22rem, calc(100vw - 2rem));
      padding: 0.95rem;
      border-radius: 18px;
      border: 1px solid rgba(15, 118, 110, 0.22);
      background: rgba(255, 255, 255, 0.94);
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 40px rgba(27, 36, 48, 0.16);
    }

    .token-overlay.is-collapsed {
      width: 14rem;
    }

    .token-overlay.is-collapsed .token-overlay__stats,
    .token-overlay.is-collapsed .token-overlay__field,
    .token-overlay.is-collapsed .token-overlay__meter,
    .token-overlay.is-collapsed .token-overlay__hint,
    .token-overlay.is-collapsed .token-overlay__actions,
    .token-overlay.is-collapsed .token-overlay__disclaimer {
      display: none;
    }

    .token-overlay__header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 0.75rem;
    }

    .token-overlay__eyebrow {
      margin: 0 0 0.3rem;
      color: var(--accent);
      font-family: "Segoe UI", Tahoma, sans-serif;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .token-overlay__collapse,
    .token-overlay__actions button {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.84);
      color: var(--muted);
      cursor: pointer;
      font-family: "Segoe UI", Tahoma, sans-serif;
      transition: 160ms ease;
    }

    .token-overlay__collapse {
      padding: 0.4rem 0.7rem;
      font-size: 0.8rem;
    }

    .token-overlay__disclaimer,
    .token-overlay__hint,
    .token-overlay__field span {
      color: var(--muted);
      font-family: "Segoe UI", Tahoma, sans-serif;
      font-size: 0.82rem;
      line-height: 1.45;
    }

    .token-overlay__disclaimer {
      margin: 0.65rem 0 0.9rem;
    }

    .token-overlay__stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.55rem;
    }

    .token-overlay__stats article {
      padding: 0.7rem;
      border-radius: 12px;
      background: var(--accent-soft);
      border: 1px solid rgba(15, 118, 110, 0.14);
    }

    .token-overlay__stats span {
      display: block;
      margin-bottom: 0.25rem;
      color: var(--muted);
      font-family: "Segoe UI", Tahoma, sans-serif;
      font-size: 0.76rem;
    }

    .token-overlay__stats strong {
      font-size: 1rem;
    }

    .token-overlay__field {
      display: grid;
      gap: 0.35rem;
      margin-top: 0.7rem;
    }

    .token-overlay__field input {
      width: 100%;
      padding: 0.55rem 0.7rem;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fff;
      font: inherit;
    }

    .token-overlay__meter {
      width: 100%;
      height: 0.8rem;
      margin-top: 0.75rem;
      border: 0;
      border-radius: 999px;
      overflow: hidden;
    }

    .token-overlay__meter::-webkit-progress-bar {
      background: #e8e3d8;
      border-radius: 999px;
    }

    .token-overlay__meter::-webkit-progress-value {
      background: linear-gradient(90deg, #0f766e, #4f9f93);
      border-radius: 999px;
    }

    .token-overlay__meter::-moz-progress-bar {
      background: linear-gradient(90deg, #0f766e, #4f9f93);
      border-radius: 999px;
    }

    .token-overlay__actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      margin-top: 0.75rem;
    }

    .token-overlay__actions button {
      padding: 0.42rem 0.65rem;
      font-size: 0.8rem;
    }

    .token-overlay__actions button:hover,
    .token-overlay__collapse:hover {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-family: "Segoe UI", Tahoma, sans-serif;
      font-size: 0.92rem;
}

th, td {
  text-align: left;
  padding: 0.6rem 0.5rem;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}

th {
  color: var(--muted);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.list {
  margin: 0;
  padding-left: 1rem;
}

.list li {
  margin-bottom: 0.9rem;
  line-height: 1.45;
}

    .list span {
      color: var(--muted);
      font-family: "Segoe UI", Tahoma, sans-serif;
      font-size: 0.88rem;
    }

    @media (max-width: 640px) {
      .hero, .layout { padding: 1rem; }
      .panel-sticky {
        position: static;
      }
      .review-rail__header {
        display: grid;
      }
      .review-link-grid {
        grid-template-columns: 1fr;
      }
      .review-dock {
        left: 0.75rem;
        top: auto;
        bottom: 1rem;
        grid-auto-flow: column;
      }
      .token-overlay {
        right: 0.75rem;
        left: 0.75rem;
        width: auto;
      }
      table { display: block; overflow-x: auto; }
    }
"""

    js = """
const panels = [...document.querySelectorAll('.panel')];
const searchInput = document.getElementById('panel-search');
const filterButtons = [...document.querySelectorAll('.filter-btn')];
const tokenOverlay = document.getElementById('token-overlay');
const reviewToggle = document.querySelector('[data-review-toggle]');
const reviewContent = document.querySelector('[data-review-content]');
const tokenBudgetDisplay = document.querySelector('[data-token-budget-display]');
const tokenUsedDisplay = document.querySelector('[data-token-used-display]');
const tokenRemainingDisplay = document.querySelector('[data-token-remaining-display]');
const tokenRatioDisplay = document.querySelector('[data-token-ratio-display]');
const tokenBudgetInput = document.querySelector('[data-token-budget-input]');
const tokenUsedInput = document.querySelector('[data-token-used-input]');
const tokenMeter = document.querySelector('[data-token-meter]');
const tokenHint = document.querySelector('[data-token-hint]');
const tokenCollapse = document.querySelector('[data-token-collapse]');
const tokenAdjustButtons = [...document.querySelectorAll('[data-token-adjust]')];
const tokenResetButton = document.querySelector('[data-token-reset]');
const TOKEN_STORE_KEY = 'codex-token-budget-overlay';
const REVIEW_RAIL_STORE_KEY = 'codex-review-rail';
const TOKEN_DEFAULT_BUDGET = Number(tokenOverlay?.dataset.defaultBudget || 0);
const TOKEN_DEFAULT_USED = Number(tokenOverlay?.dataset.defaultUsed || 0);
let reviewRailCollapsed = false;

function clampTokenValue(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  return Math.max(0, Math.round(parsed));
}

function todayKey() {
  return new Date().toLocaleDateString('en-CA');
}

function loadReviewRailState() {
  try {
    return localStorage.getItem(REVIEW_RAIL_STORE_KEY) === 'collapsed';
  } catch {
    return false;
  }
}

function renderReviewRailState() {
  if (!reviewToggle || !reviewContent) {
    return;
  }
  reviewContent.classList.toggle('is-collapsed', reviewRailCollapsed);
  reviewToggle.setAttribute('aria-expanded', String(!reviewRailCollapsed));
  reviewToggle.textContent = reviewRailCollapsed ? 'Mostrar' : 'Ocultar';
  try {
    localStorage.setItem(REVIEW_RAIL_STORE_KEY, reviewRailCollapsed ? 'collapsed' : 'expanded');
  } catch {}
}

function loadTokenState() {
  const fallback = {
    budget: TOKEN_DEFAULT_BUDGET,
    used: TOKEN_DEFAULT_USED,
    collapsed: false,
    date: todayKey(),
  };

  try {
    const raw = localStorage.getItem(TOKEN_STORE_KEY);
    if (!raw) {
      return fallback;
    }

    const parsed = JSON.parse(raw);
    const currentDate = todayKey();
    if (parsed.date !== currentDate) {
      return { ...fallback, budget: clampTokenValue(parsed.budget) || TOKEN_DEFAULT_BUDGET, date: currentDate };
    }

    return {
      budget: clampTokenValue(parsed.budget) || TOKEN_DEFAULT_BUDGET,
      used: clampTokenValue(parsed.used),
      collapsed: Boolean(parsed.collapsed),
      date: currentDate,
    };
  } catch {
    return fallback;
  }
}

let tokenState = loadTokenState();

function saveTokenState() {
  localStorage.setItem(TOKEN_STORE_KEY, JSON.stringify(tokenState));
}

function renderTokenState() {
  const budget = clampTokenValue(tokenState.budget) || TOKEN_DEFAULT_BUDGET;
  const used = Math.min(clampTokenValue(tokenState.used), budget);
  const remaining = Math.max(budget - used, 0);
  const ratio = budget > 0 ? Math.round((used / budget) * 100) : 0;
  const mode = remaining === 0 ? 'límite alcanzado' : remaining < budget * 0.2 ? 'modo bajo' : remaining < budget * 0.5 ? 'modo medio' : 'modo amplio';

  tokenState = { ...tokenState, budget, used, date: todayKey() };
  if (tokenOverlay) {
    tokenOverlay.classList.toggle('is-collapsed', Boolean(tokenState.collapsed));
  }
  if (tokenCollapse) {
    tokenCollapse.setAttribute('aria-pressed', String(Boolean(tokenState.collapsed)));
    tokenCollapse.textContent = tokenState.collapsed ? 'Mostrar' : 'Ocultar';
  }
  if (tokenBudgetDisplay) tokenBudgetDisplay.textContent = String(budget);
  if (tokenUsedDisplay) tokenUsedDisplay.textContent = String(used);
  if (tokenRemainingDisplay) tokenRemainingDisplay.textContent = String(remaining);
  if (tokenRatioDisplay) tokenRatioDisplay.textContent = `${ratio}%`;
  if (tokenBudgetInput) tokenBudgetInput.value = String(budget);
  if (tokenUsedInput) tokenUsedInput.value = String(used);
  if (tokenMeter) {
    tokenMeter.max = String(budget || 1);
    tokenMeter.value = String(used);
    tokenMeter.setAttribute('aria-valuetext', `${remaining} restantes de ${budget}`);
  }
  if (tokenHint) {
    tokenHint.textContent = `${mode}: mantiene visible el margen útil mientras trabajas.`;
  }
  saveTokenState();
}

function updateTokenState(patch) {
  tokenState = {
    ...tokenState,
    ...patch,
    budget: clampTokenValue(patch.budget ?? tokenState.budget),
    used: clampTokenValue(patch.used ?? tokenState.used),
  };
  renderTokenState();
}

function normalize(value) {
  return (value || '').toLowerCase().normalize('NFD').replace(/\\p{Diacritic}/gu, '');
}

function applyFilters() {
  const query = normalize(searchInput?.value);
  const activeFilter = document.querySelector('.filter-btn.is-active')?.dataset.filter || 'all';
  panels.forEach((panel) => {
    const groupMatches = activeFilter === 'all' || panel.dataset.group === activeFilter;
    const textMatches = !query || normalize(panel.innerText).includes(query);
    panel.classList.toggle('is-hidden', !(groupMatches && textMatches));
  });
}

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    filterButtons.forEach((item) => item.classList.remove('is-active'));
    button.classList.add('is-active');
    applyFilters();
  });
});

searchInput?.addEventListener('input', applyFilters);
applyFilters();

tokenBudgetInput?.addEventListener('change', () => {
  updateTokenState({ budget: tokenBudgetInput.value });
});

tokenUsedInput?.addEventListener('change', () => {
  updateTokenState({ used: tokenUsedInput.value });
});

tokenAdjustButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const delta = clampTokenValue(button.dataset.tokenAdjust);
    const signedDelta = button.dataset.tokenAdjust?.startsWith('-') ? -delta : delta;
    updateTokenState({ used: tokenState.used + signedDelta });
  });
});

tokenResetButton?.addEventListener('click', () => {
  updateTokenState({ used: 0 });
});

tokenCollapse?.addEventListener('click', () => {
  tokenState = { ...tokenState, collapsed: !tokenState.collapsed };
  renderTokenState();
});

reviewRailCollapsed = loadReviewRailState();
reviewToggle?.addEventListener('click', () => {
  reviewRailCollapsed = !reviewRailCollapsed;
  renderReviewRailState();
});

renderTokenState();
renderReviewRailState();

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
