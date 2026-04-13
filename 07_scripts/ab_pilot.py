from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from common import ROOT, dump_json, now_stamp
from data_io import canonical_json, dump_jsonl_path, load_jsonl_path, load_structured_path

DEFAULT_PLAN_PATH = "00_sistema_tesis/config/ab_pilot_plan.json"
DEFAULT_REPORT_PATH = "00_sistema_tesis/config/ab_pilot_report.json"
DEFAULT_MARKDOWN_PATH = "06_dashboard/generado/ab_pilot_report.md"
DEFAULT_TRACE_PATH = "00_sistema_tesis/bitacora/audit_history/ab_pilot_runs.jsonl"
DEFAULT_CSV_TEMPLATE_PATH = "00_sistema_tesis/plantillas/ab_pilot_tasks_template.csv"

KNOWN_ROUTES = ("serena",)


@dataclass
class RouteAggregate:
    route: str
    tasks: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    acceptance_rate: float
    gate_failures: int
    rework_rate: float


@dataclass
class ExecutionContext:
    session_id: str
    step_id: str
    source_event_id: str


class ValidationError(ValueError):
    pass


def _sanitize_identifier(value: str, fallback: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return candidate or fallback


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Campo invalido para entero ({field_name}): {value}") from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Campo invalido para float ({field_name}): {value}") from exc


def _to_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "si"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValidationError(f"Campo invalido para bool ({field_name}): {value}")


def default_plan_payload() -> dict[str, Any]:
    return {
        "metadata": {
            "experiment_id": "ab-2026-04-template",
            "owner": "tesista",
            "created_at": now_stamp(),
            "notes": "Reemplazar datos de ejemplo con resultados reales del piloto.",
        },
        "criteria": {
            "primary_objective": "reduce_tokens_cost",
            "min_cost_reduction_pct": 25.0,
            "min_token_reduction_pct": 20.0,
            "min_acceptance_rate": 0.9,
            "max_gate_failures": 0,
        },
        "tasks": [
            {
                "task_id": "T-001",
                "task_type": "resumen_capitulo",
                "baseline_complexity": "media",
                "serena": {
                    "input_tokens": 1800,
                    "output_tokens": 700,
                    "cost_usd": 0.045,
                    "latency_ms": 4200,
                    "accepted": True,
                    "gate_failures": 0,
                    "rework": False,
                },
            }
        ],
    }


def default_csv_template_rows() -> list[dict[str, Any]]:
    return [
        {
            "task_id": "T-017",
            "task_type": "documentacion",
            "baseline_complexity": "baja",
            "serena_input_tokens": 1200,
            "serena_output_tokens": 500,
            "serena_cost_usd": 0.032,
            "serena_latency_ms": 3000,
            "serena_accepted": True,
            "serena_gate_failures": 0,
            "serena_rework": False,
        }
    ]


def default_execution_context() -> ExecutionContext:
    return ExecutionContext(
        session_id=str(os.getenv("SISTEMA_TESIS_SESSION_ID", "ab-pilot-local")).strip() or "ab-pilot-local",
        step_id=str(os.getenv("SISTEMA_TESIS_STEP_ID", "")).strip(),
        source_event_id=str(os.getenv("SISTEMA_TESIS_SOURCE_EVENT_ID", "")).strip(),
    )


def write_csv_template(csv_relative_path: str) -> Path:
    csv_path = ROOT / csv_relative_path
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "task_id",
        "task_type",
        "baseline_complexity",
        "serena_input_tokens",
        "serena_output_tokens",
        "serena_cost_usd",
        "serena_latency_ms",
        "serena_accepted",
        "serena_gate_failures",
        "serena_rework",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in default_csv_template_rows():
            writer.writerow(row)
    return csv_path


def init_plan(plan_relative_path: str) -> Path:
    return dump_json(plan_relative_path, default_plan_payload())


def _parse_csv_bool(row: dict[str, str], field_name: str) -> bool:
    return _to_bool(row.get(field_name, ""), field_name)


def _parse_csv_task(row: dict[str, str], index: int) -> dict[str, Any]:
    task_id = str(row.get("task_id", "")).strip()
    task_type = str(row.get("task_type", "")).strip()
    baseline_complexity = str(row.get("baseline_complexity", "")).strip() or "media"
    if not task_id:
        raise ValidationError(f"CSV row {index}: task_id es obligatorio")
    if not task_type:
        raise ValidationError(f"CSV row {index}: task_type es obligatorio")

    task: dict[str, Any] = {
        "task_id": task_id,
        "task_type": task_type,
        "baseline_complexity": baseline_complexity,
    }

    task["serena"] = {
        "input_tokens": _to_int(row.get("serena_input_tokens"), f"CSV row {index}: serena_input_tokens"),
        "output_tokens": _to_int(row.get("serena_output_tokens"), f"CSV row {index}: serena_output_tokens"),
        "cost_usd": _to_float(row.get("serena_cost_usd"), f"CSV row {index}: serena_cost_usd"),
        "latency_ms": _to_int(row.get("serena_latency_ms"), f"CSV row {index}: serena_latency_ms"),
        "accepted": _parse_csv_bool(row, "serena_accepted"),
        "gate_failures": _to_int(row.get("serena_gate_failures"), f"CSV row {index}: serena_gate_failures"),
        "rework": _parse_csv_bool(row, "serena_rework"),
    }

    return task


def build_plan_from_csv(
    csv_relative_path: str,
    plan_relative_path: str,
    *,
    experiment_id: str | None = None,
    owner: str = "tesista",
) -> Path:
    csv_path = ROOT / csv_relative_path
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe el CSV de entrada: {csv_relative_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        raise ValidationError("El CSV de entrada no contiene filas")

    tasks = [_parse_csv_task(row, index) for index, row in enumerate(rows, start=1)]
    inferred_id = _sanitize_identifier(Path(csv_relative_path).stem or "ab-pilot", "ab-pilot")
    payload = {
        "metadata": {
            "experiment_id": experiment_id or f"ab-{inferred_id}",
            "owner": owner,
            "created_at": now_stamp(),
            "notes": f"Plan generado desde CSV: {csv_relative_path}",
        },
        "criteria": default_plan_payload()["criteria"],
        "tasks": tasks,
    }
    return dump_json(plan_relative_path, payload)


def _validate_task(task: dict[str, Any], index: int) -> None:
    if not isinstance(task.get("task_id"), str) or not task["task_id"].strip():
        raise ValidationError(f"tasks[{index}].task_id es obligatorio")
    if not isinstance(task.get("task_type"), str) or not task["task_type"].strip():
        raise ValidationError(f"tasks[{index}].task_type es obligatorio")

    if "serena" not in task or not isinstance(task["serena"], dict):
        raise ValidationError(f"tasks[{index}].serena es obligatorio")

    payload = task["serena"]
    _to_int(payload.get("input_tokens"), f"tasks[{index}].serena.input_tokens")
    _to_int(payload.get("output_tokens"), f"tasks[{index}].serena.output_tokens")
    _to_float(payload.get("cost_usd"), f"tasks[{index}].serena.cost_usd")
    _to_int(payload.get("latency_ms"), f"tasks[{index}].serena.latency_ms")
    _to_bool(payload.get("accepted"), f"tasks[{index}].serena.accepted")
    _to_int(payload.get("gate_failures"), f"tasks[{index}].serena.gate_failures")
    _to_bool(payload.get("rework"), f"tasks[{index}].serena.rework")


def load_plan(plan_relative_path: str) -> dict[str, Any]:
    plan_path = ROOT / plan_relative_path
    if not plan_path.exists():
        raise FileNotFoundError(
            f"No existe plan A/B en {plan_relative_path}. Ejecuta init primero."
        )

    payload = load_structured_path(plan_path)
    if not isinstance(payload, dict):
        raise ValidationError("El plan debe ser un objeto JSON")
    if "tasks" not in payload or not isinstance(payload["tasks"], list):
        raise ValidationError("El plan debe incluir la lista tasks")
    if not payload["tasks"]:
        raise ValidationError("El plan requiere al menos una tarea")

    for index, task in enumerate(payload["tasks"]):
        if not isinstance(task, dict):
            raise ValidationError(f"tasks[{index}] debe ser objeto")
        _validate_task(task, index)

    return payload


def common_routes(tasks: list[dict[str, Any]]) -> list[str]:
    if not tasks:
        return []
    return ["serena"] if all("serena" in task for task in tasks) else []


def _task_type_label(task: dict[str, Any]) -> str:
    raw_value = str(task.get("task_type") or "sin_tipo").strip()
    return raw_value or "sin_tipo"


def aggregate_route(tasks: list[dict[str, Any]], route: str) -> RouteAggregate:
    task_count = len(tasks)
    input_tokens = 0
    output_tokens = 0
    total_cost = 0.0
    total_latency = 0
    accepted_count = 0
    gate_failures = 0
    rework_count = 0

    for task in tasks:
        data = task[route]
        in_tokens = _to_int(data.get("input_tokens"), f"{route}.input_tokens")
        out_tokens = _to_int(data.get("output_tokens"), f"{route}.output_tokens")
        cost_usd = _to_float(data.get("cost_usd"), f"{route}.cost_usd")
        latency_ms = _to_int(data.get("latency_ms"), f"{route}.latency_ms")
        accepted = _to_bool(data.get("accepted"), f"{route}.accepted")
        failures = _to_int(data.get("gate_failures"), f"{route}.gate_failures")
        rework = _to_bool(data.get("rework"), f"{route}.rework")

        input_tokens += in_tokens
        output_tokens += out_tokens
        total_cost += cost_usd
        total_latency += latency_ms
        accepted_count += 1 if accepted else 0
        gate_failures += failures
        rework_count += 1 if rework else 0

    total_tokens = input_tokens + output_tokens
    avg_latency_ms = (float(total_latency) / task_count) if task_count else 0.0
    acceptance_rate = (float(accepted_count) / task_count) if task_count else 0.0
    rework_rate = (float(rework_count) / task_count) if task_count else 0.0

    return RouteAggregate(
        route=route,
        tasks=task_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 6),
        avg_latency_ms=round(avg_latency_ms, 2),
        acceptance_rate=round(acceptance_rate, 4),
        gate_failures=gate_failures,
        rework_rate=round(rework_rate, 4),
    )


def aggregate_by_task_type(tasks: list[dict[str, Any]]) -> dict[str, dict[str, RouteAggregate]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        grouped.setdefault(_task_type_label(task), []).append(task)

    summary: dict[str, dict[str, RouteAggregate]] = {}
    for task_type, bucket in sorted(grouped.items()):
        summary[task_type] = {"serena": aggregate_route(bucket, "serena")}
    return summary


def aggregate_routes(tasks: list[dict[str, Any]]) -> dict[str, RouteAggregate]:
    if not tasks:
        raise ValidationError("No hay tareas para comparar")
    return {"serena": aggregate_route(tasks, "serena")}


def pct_delta(reference: float, candidate: float) -> float:
    if reference == 0:
        return 0.0
    return round(((reference - candidate) / reference) * 100.0, 2)


def pick_winner(*, serena: RouteAggregate, criteria: dict[str, Any]) -> tuple[str, list[str]]:
    min_acceptance_rate = _to_float(criteria.get("min_acceptance_rate", 0), "criteria.min_acceptance_rate")
    max_gate_failures = _to_int(criteria.get("max_gate_failures", 0), "criteria.max_gate_failures")

    if serena.acceptance_rate >= min_acceptance_rate and serena.gate_failures <= max_gate_failures:
        return "serena", ["Serena cumple los umbrales de calidad y gate."]
    return "serena", ["Serena es la única ruta evaluada; se conserva como línea base operativa."]


def summarize_route_set(task_type: str, route_aggregates: dict[str, RouteAggregate], criteria: dict[str, Any]) -> dict[str, Any]:
    winner, reasons = pick_winner(serena=route_aggregates["serena"], criteria=criteria)
    return {
        "task_type": task_type,
        "winner": winner,
        "reasons": reasons,
        "serena": _aggregate_to_dict(route_aggregates["serena"]),
    }


def _aggregate_to_dict(aggregate: RouteAggregate) -> dict[str, Any]:
    return {
        "route": aggregate.route,
        "tasks": aggregate.tasks,
        "input_tokens": aggregate.input_tokens,
        "output_tokens": aggregate.output_tokens,
        "total_tokens": aggregate.total_tokens,
        "total_cost_usd": aggregate.total_cost_usd,
        "avg_latency_ms": aggregate.avg_latency_ms,
        "acceptance_rate": aggregate.acceptance_rate,
        "gate_failures": aggregate.gate_failures,
        "rework_rate": aggregate.rework_rate,
    }


def _render_markdown(
    *,
    experiment_id: str,
    context: ExecutionContext,
    route_aggregates: dict[str, RouteAggregate],
    winner: str,
    reasons: list[str],
    by_task_type: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "# Reporte Piloto Serena",
        "",
        f"- generated_at: {now_stamp()}",
        f"- experiment_id: {experiment_id}",
        f"- session_id: {context.session_id}",
        f"- step_id: {context.step_id or 'sin_step_id'}",
        f"- source_event_id: {context.source_event_id or 'sin_source_event_id'}",
        f"- winner: {winner}",
        "",
        "## Resumen Serena",
        "",
    ]
    aggregate = route_aggregates["serena"]
    lines.extend([
        "### serena",
        "",
        f"- tareas: {aggregate.tasks}",
        f"- input_tokens: {aggregate.input_tokens}",
        f"- output_tokens: {aggregate.output_tokens}",
        f"- total_tokens: {aggregate.total_tokens}",
        f"- costo total (USD): {aggregate.total_cost_usd:.6f}",
        f"- latencia promedio (ms): {aggregate.avg_latency_ms:.2f}",
        f"- acceptance rate: {aggregate.acceptance_rate:.4f}",
        f"- gate failures: {aggregate.gate_failures}",
        f"- rework rate: {aggregate.rework_rate:.4f}",
        "",
        "## Criterio",
        "",
        "- Serena es la única ruta activa en este piloto.",
        "- La evaluación conserva trazabilidad, costo y latencia por tarea.",
        "",
    ])
    lines.extend(f"- {reason}" for reason in reasons)
    lines.append("")
    lines.extend([
        "## Desglose por tipo de tarea",
        "",
    ])
    for task_type, data in by_task_type.items():
        lines.extend([
            f"### {task_type}",
            "",
            f"- winner: {data['winner']}",
            f"- serena: costo {data['serena']['total_cost_usd']:.6f} USD, tokens {data['serena']['total_tokens']}, latencia {data['serena']['avg_latency_ms']:.2f} ms",
        ])
        for reason in data["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")
    return "\n".join(lines)


def _build_trace_record(
    *,
    context: ExecutionContext,
    report_payload: dict[str, Any],
    report_relative_path: str,
    markdown_relative_path: str,
    trace_relative_path: str,
) -> dict[str, Any]:
    digest = hashlib.sha256(canonical_json(report_payload).encode("utf-8")).hexdigest()
    return {
        "generated_at": report_payload["generated_at"],
        "experiment_id": report_payload["experiment_id"],
        "session_id": context.session_id,
        "step_id": context.step_id,
        "source_event_id": context.source_event_id,
        "trace_path": trace_relative_path,
        "report_path": report_relative_path,
        "markdown_path": markdown_relative_path,
        "report_hash": digest,
        "winner": report_payload["summary"]["winner"],
        "route_summary": report_payload["summary"],
    }


def append_trace_record(trace_relative_path: str, trace_record: dict[str, Any]) -> Path:
    trace_path = ROOT / trace_relative_path
    rows = load_jsonl_path(trace_path)
    rows.append(trace_record)
    dump_jsonl_path(trace_path, rows)
    return trace_path


def evaluate_plan(
    plan_relative_path: str,
    report_relative_path: str,
    markdown_relative_path: str,
    trace_relative_path: str,
    context: ExecutionContext,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    payload = load_plan(plan_relative_path)
    metadata = payload.get("metadata", {})
    criteria = payload.get("criteria", {})
    tasks = payload["tasks"]

    route_aggregates = aggregate_routes(tasks)
    winner, reasons = pick_winner(serena=route_aggregates["serena"], criteria=criteria)
    by_task_type_raw = aggregate_by_task_type(tasks)
    by_task_type = {
        task_type: summarize_route_set(task_type, summary, criteria)
        for task_type, summary in by_task_type_raw.items()
    }

    report_payload = {
        "generated_at": now_stamp(),
        "experiment_id": str(metadata.get("experiment_id") or "ab-pilot"),
        "execution_context": {
            "session_id": context.session_id,
            "step_id": context.step_id,
            "source_event_id": context.source_event_id,
        },
        "criteria": criteria,
        "summary": {
            **{route: _aggregate_to_dict(route_aggregate) for route, route_aggregate in route_aggregates.items()},
            "winner": winner,
            "reasons": reasons,
        },
        "by_task_type": by_task_type,
    }

    report_path = dump_json(report_relative_path, report_payload)

    markdown = _render_markdown(
        experiment_id=report_payload["experiment_id"],
        context=context,
        route_aggregates=route_aggregates,
        winner=winner,
        reasons=reasons,
        by_task_type=by_task_type,
    )
    markdown_path = ROOT / markdown_relative_path
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")

    trace_record = _build_trace_record(
        context=context,
        report_payload=report_payload,
        report_relative_path=report_relative_path,
        markdown_relative_path=markdown_relative_path,
        trace_relative_path=trace_relative_path,
    )
    trace_path = append_trace_record(trace_relative_path, trace_record)

    return report_path, markdown_path, trace_path, report_payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Piloto Serena")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_cmd = subparsers.add_parser("init", help="Crear plantilla inicial del plan A/B")
    init_cmd.add_argument("--plan", default=DEFAULT_PLAN_PATH, help="Ruta relativa del plan A/B")

    csv_cmd = subparsers.add_parser("from-csv", help="Generar un plan A/B desde un CSV de tareas")
    csv_cmd.add_argument("--csv", default=DEFAULT_CSV_TEMPLATE_PATH, help="Ruta relativa del CSV de entrada")
    csv_cmd.add_argument("--plan", default=DEFAULT_PLAN_PATH, help="Ruta relativa del plan A/B")
    csv_cmd.add_argument("--experiment-id", default="", help="Identificador opcional del experimento")
    csv_cmd.add_argument("--owner", default="tesista", help="Propietario del plan generado")
    csv_cmd.add_argument("--template", action="store_true", help="Crear una plantilla CSV en vez de leer una existente")

    eval_cmd = subparsers.add_parser("evaluate", help="Evaluar plan A/B y generar reporte")
    eval_cmd.add_argument("--plan", default=DEFAULT_PLAN_PATH, help="Ruta relativa del plan A/B")
    eval_cmd.add_argument("--report", default=DEFAULT_REPORT_PATH, help="Ruta relativa JSON de salida")
    eval_cmd.add_argument("--markdown", default=DEFAULT_MARKDOWN_PATH, help="Ruta relativa Markdown de salida")
    eval_cmd.add_argument("--trace", default=DEFAULT_TRACE_PATH, help="Ruta relativa JSONL de trazas")
    eval_cmd.add_argument("--session-id", default="", help="Identificador de sesion para trazabilidad")
    eval_cmd.add_argument("--step-id", default="", help="VAL-STEP asociado a la corrida")
    eval_cmd.add_argument("--source-event-id", default="", help="Evento fuente asociado a la corrida")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        created = init_plan(args.plan)
        print(f"Plan A/B creado en: {created}")
        return 0

    if args.command == "from-csv":
        if args.template:
            created = write_csv_template(args.csv)
            print(f"Plantilla CSV creada en: {created}")
            return 0
        created = build_plan_from_csv(
            csv_relative_path=args.csv,
            plan_relative_path=args.plan,
            experiment_id=args.experiment_id or None,
            owner=args.owner,
        )
        print(f"Plan Serena generado desde CSV en: {created}")
        return 0

    if args.command == "evaluate":
        context = ExecutionContext(
            session_id=str(args.session_id or os.getenv("SISTEMA_TESIS_SESSION_ID", "ab-pilot-local")).strip() or "ab-pilot-local",
            step_id=str(args.step_id or os.getenv("SISTEMA_TESIS_STEP_ID", "")).strip(),
            source_event_id=str(args.source_event_id or os.getenv("SISTEMA_TESIS_SOURCE_EVENT_ID", "")).strip(),
        )
        report_path, markdown_path, trace_path, report_payload = evaluate_plan(
            plan_relative_path=args.plan,
            report_relative_path=args.report,
            markdown_relative_path=args.markdown,
            trace_relative_path=args.trace,
            context=context,
        )
        winner = report_payload["summary"]["winner"]
        print(f"Reporte JSON generado en: {report_path}")
        print(f"Reporte Markdown generado en: {markdown_path}")
        print(f"Traza JSONL generada en: {trace_path}")
        print(f"Ruta recomendada: {winner}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
