from __future__ import annotations

from pathlib import Path

from canon import load_events
from common import ROOT, load_csv_rows, load_yaml_json, stable_generated_at, write_text_if_changed


OUTPUT_PATH = ROOT / "MEMORY.md"
SOURCE_PATHS = [
    "00_sistema_tesis/canon/events.jsonl",
    "00_sistema_tesis/config/sistema_tesis.yaml",
    "01_planeacion/backlog.csv",
    "01_planeacion/riesgos.csv",
    "01_planeacion/entregables.csv",
    "00_sistema_tesis/bitacora/log_conversaciones_ia.md",
    "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
]


def priority_rank(value: str) -> int:
    order = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    return order.get(value, 99)


def latest_human_validations(limit: int = 5) -> list[dict]:
    events = [event for event in load_events() if event.get("event_type") == "human_validation"]
    selected = list(reversed(events[-limit:]))
    entries: list[dict] = []
    for event in selected:
        matrix_row = dict(event.get("links", {}).get("matrix_row", {}))
        summary = str(matrix_row.get("summary") or event.get("payload", {}).get("matrix_row", {}).get("summary", "")).strip()
        reference = str(matrix_row.get("reference") or event.get("links", {}).get("reference", "[DEC-0014]")).strip()
        entries.append(
            {
                "step_id": str(event.get("event_id", "")).strip(),
                "date": str(matrix_row.get("date") or str(event.get("occurred_at", ""))[:10]).strip(),
                "summary": summary or "Validación humana registrada sin resumen adicional.",
                "reference": reference or "[DEC-0014]",
            }
        )
    return entries


def critical_pending_tasks(limit: int = 6) -> list[dict]:
    backlog = [item for item in load_csv_rows("01_planeacion/backlog.csv") if item["estado"] in {"pendiente", "en_progreso"}]
    backlog.sort(key=lambda item: (priority_rank(item["prioridad"]), item["fecha_objetivo"], item["task_id"]))
    return backlog[:limit]


def open_risks(limit: int = 4) -> list[dict]:
    risks = [item for item in load_csv_rows("01_planeacion/riesgos.csv") if item["estado"] == "abierto"]
    risks.sort(key=lambda item: (priority_rank(item["impacto"]), priority_rank(item["probabilidad"]), item["risk_id"]))
    return risks[:limit]


def render_memory() -> str:
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    deliverables = load_csv_rows("01_planeacion/entregables.csv")
    generated_at = stable_generated_at(SOURCE_PATHS)
    deliverable = next(
        (item for item in deliverables if item["deliverable_id"] == sistema["siguiente_entregable"]),
        None,
    )
    validations = latest_human_validations()
    tasks = critical_pending_tasks()
    risks = open_risks()

    lines = [
        "# MEMORY",
        "",
        "> Este `MEMORY.md` es un artefacto derivado. No lo edites manualmente.",
        "> Fuente de verdad: `00_sistema_tesis/canon/events.jsonl` + backlog + riesgos + trazabilidad canónica.",
        "",
        "## Estado actual",
        "",
        f"- **Generado:** `{generated_at}`",
        f"- **Versión del sistema:** `{sistema['version']}`",
        f"- **Estado global:** `{sistema['estado_global']}`",
        f"- **Bloque activo:** `{sistema['bloque_activo']}`",
        f"- **Fase actual:** `{sistema['fase_actual']}`",
        f"- **Riesgo principal abierto:** `{sistema['riesgo_principal_abierto']}`",
        "",
        "## Entregable activo",
        "",
        f"- **ID:** `{sistema['siguiente_entregable']}`",
        f"- **Nombre:** {deliverable['nombre'] if deliverable else 'No encontrado en entregables.csv'}",
        f"- **Estado:** `{deliverable['estado'] if deliverable else 'n/a'}`",
        "",
        "## Últimos cambios validados",
        "",
    ]

    for item in validations:
        lines.append(
            f"- **{item['step_id']}** · `{item['date']}` · {item['summary']} · soporte {item['reference']}"
        )

    lines.extend(
        [
            "",
            "## Próximos pendientes críticos",
            "",
        ]
    )

    for item in tasks:
        lines.append(
            f"- **{item['task_id']}** · `{item['bloque']}` · {item['tarea']} · prioridad `{item['prioridad']}` · estado `{item['estado']}`"
        )

    lines.extend(
        [
            "",
            "## Riesgos prioritarios",
            "",
        ]
    )

    for item in risks:
        lines.append(
            f"- **{item['risk_id']}** · {item['riesgo']} · probabilidad `{item['probabilidad']}` · impacto `{item['impacto']}`"
        )

    lines.extend(
        [
            "",
            "## Referencias base",
            "",
            "- `00_sistema_tesis/canon/events.jsonl`",
            "- `00_sistema_tesis/bitacora/log_conversaciones_ia.md`",
            "- `00_sistema_tesis/bitacora/matriz_trazabilidad.md`",
            "- `01_planeacion/backlog.csv`",
            "- `01_planeacion/entregables.csv`",
            "- `01_planeacion/riesgos.csv`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    write_text_if_changed(OUTPUT_PATH, render_memory())
    print(f"MEMORY generado en: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
