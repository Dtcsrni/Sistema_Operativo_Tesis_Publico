from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any
from urllib import error, parse, request
from zoneinfo import ZoneInfo

from common import ROOT, dump_json, now_stamp


USAGE_ENDPOINT = "https://api.openai.com/v1/organization/usage/completions"
COSTS_ENDPOINT = "https://api.openai.com/v1/organization/costs"
LOOKBACK_DAYS = 31
SNAPSHOT_PATH = "00_sistema_tesis/config/token_usage_snapshot.json"


def load_json(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_snapshot(payload: dict[str, Any]) -> None:
    existing: dict[str, Any] = {}
    path = ROOT / SNAPSHOT_PATH
    if path.exists():
        existing = load_json(SNAPSHOT_PATH)
    comparable_payload = {key: value for key, value in payload.items() if key != "generated_at"}
    comparable_existing = {key: value for key, value in existing.items() if key != "generated_at"}
    if comparable_existing == comparable_payload and existing.get("generated_at"):
        payload["generated_at"] = existing["generated_at"]
    dump_json(SNAPSHOT_PATH, payload)


def require_config(mapping: dict[str, Any], dotted_path: str) -> Any:
    current: Any = mapping
    for key in dotted_path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise KeyError(f"Falta la clave obligatoria en token_budget.json: {dotted_path}")
        current = current[key]
    return current


def unix_now() -> int:
    return int(time.time())


def day_start_epoch(now_local: datetime) -> int:
    local_midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(local_midnight.timestamp())


def week_start_epoch(now_local: datetime) -> int:
    # ISO week starts on Monday.
    monday = now_local.date().fromordinal(now_local.date().toordinal() - now_local.weekday())
    monday_dt = datetime(monday.year, monday.month, monday.day, tzinfo=now_local.tzinfo)
    return int(monday_dt.timestamp())


def to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def api_get(url: str, headers: dict[str, str], params: dict[str, Any]) -> dict[str, Any]:
    encoded = parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = request.Request(f"{url}?{encoded}", headers=headers, method="GET")
    with request.urlopen(req, timeout=30) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def fetch_paginated(url: str, headers: dict[str, str], base_params: dict[str, Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    page: str | None = None
    while True:
        params = dict(base_params)
        if page:
            params["page"] = page
        payload = api_get(url, headers, params)
        data = payload.get("data", [])
        if isinstance(data, list):
            collected.extend(item for item in data if isinstance(item, dict))
        page = payload.get("next_page")
        if not page:
            break
    return collected


def extract_usage_totals(buckets: list[dict[str, Any]], window_start: int) -> dict[str, Any]:
    input_tokens = 0
    output_tokens = 0
    requests_count = 0
    model_breakdown: dict[str, int] = {}

    for bucket in buckets:
        bucket_start = to_int(bucket.get("start_time"))
        if bucket_start < window_start:
            continue

        results = bucket.get("results")
        if isinstance(results, list) and results:
            source_rows = [row for row in results if isinstance(row, dict)]
        else:
            source_rows = [bucket]

        for row in source_rows:
            in_tokens = to_int(row.get("input_tokens"))
            out_tokens = to_int(row.get("output_tokens"))
            reqs = to_int(row.get("num_model_requests"))
            input_tokens += in_tokens
            output_tokens += out_tokens
            requests_count += reqs
            model_name = str(row.get("model") or "unknown")
            model_breakdown[model_name] = model_breakdown.get(model_name, 0) + in_tokens + out_tokens

    total_tokens = input_tokens + output_tokens
    top_models = sorted(model_breakdown.items(), key=lambda item: item[1], reverse=True)[:6]
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "requests": requests_count,
        "top_models": [{"model": model, "tokens": tokens} for model, tokens in top_models],
    }


def extract_cost_totals(buckets: list[dict[str, Any]], window_start: int) -> dict[str, Any]:
    total_usd = 0.0
    line_items: dict[str, float] = {}

    for bucket in buckets:
        bucket_start = to_int(bucket.get("start_time"))
        if bucket_start < window_start:
            continue

        results = bucket.get("results")
        if isinstance(results, list) and results:
            source_rows = [row for row in results if isinstance(row, dict)]
        else:
            source_rows = [bucket]

        for row in source_rows:
            amount = row.get("amount")
            if isinstance(amount, dict):
                value = to_float(amount.get("value"))
                currency = str(amount.get("currency") or "usd").lower()
            else:
                value = to_float(row.get("amount_value"))
                currency = str(row.get("currency") or "usd").lower()
            if currency != "usd":
                continue
            total_usd += value
            line_item = str(row.get("line_item") or row.get("project_id") or "general")
            line_items[line_item] = line_items.get(line_item, 0.0) + value

    top_lines = sorted(line_items.items(), key=lambda item: item[1], reverse=True)[:6]
    return {
        "usd": round(total_usd, 6),
        "top_line_items": [{"line_item": name, "usd": round(value, 6)} for name, value in top_lines],
    }


def build_recommendations(
    *,
    daily_ratio: float,
    weekly_ratio: float,
    day_progress_ratio: float,
    week_progress_ratio: float,
    daily_remaining_tokens: int,
    weekly_remaining_tokens: int,
    warning_ratio: float,
    critical_ratio: float,
) -> list[str]:
    actions: list[str] = []

    if daily_ratio >= critical_ratio or weekly_ratio >= critical_ratio:
        actions.append("Activar modo conservador: solo tareas criticas de arquitectura, hipotesis, metricas o decisiones irreversibles.")
        actions.append("Congelar exploracion amplia y convertir cada solicitud en salida verificable concreta antes de abrir un nuevo frente.")
    elif daily_ratio >= warning_ratio or weekly_ratio >= warning_ratio:
        actions.append("Entrar a modo optimizado: mantener razonamiento medio por default y subir a alto solo si el costo del error es alto.")
        actions.append("Consolidar solicitudes por lote para reducir iteraciones redundantes y contexto repetido.")
    else:
        actions.append("Mantener modo productivo: priorizar cierres funcionales completos por sesion antes de refinar estilo o detalle no critico.")

    if daily_ratio > day_progress_ratio + 0.20:
        actions.append("Ritmo diario por encima de lo esperado: bajar profundidad en tareas mecanicas y posponer refinamientos no esenciales.")
    if weekly_ratio > week_progress_ratio + 0.15:
        actions.append("Ritmo semanal acelerado: reservar presupuesto restante para entregables vinculados al bloque activo y riesgos abiertos.")

    if daily_remaining_tokens <= 0:
        actions.append("Cuota diaria agotada: registrar pendientes y pasar a revision/planeacion sin consumo adicional cuando sea posible.")
    if weekly_remaining_tokens <= 0:
        actions.append("Cuota semanal agotada: ejecutar solo actividades sin inferencia y replanificar ventana de uso.")

    if not actions:
        actions.append("Sin alertas de cuota: sostener enfoque en avance funcional verificable por cada 1000 tokens.")
    return actions[:6]


def main() -> int:
    budget_cfg = load_json("00_sistema_tesis/config/token_budget.json")
    timezone_name = str(require_config(budget_cfg, "timezone"))
    tz = ZoneInfo(timezone_name)
    now_local = datetime.now(tz)
    now_epoch = unix_now()
    daily_start = day_start_epoch(now_local)
    weekly_start = week_start_epoch(now_local)
    lookback_start = now_epoch - LOOKBACK_DAYS * 24 * 60 * 60

    daily_tokens_budget = to_int(require_config(budget_cfg, "daily.tokens"))
    weekly_tokens_budget = to_int(require_config(budget_cfg, "weekly.tokens"))
    daily_usd_budget = to_float(require_config(budget_cfg, "daily.usd"))
    weekly_usd_budget = to_float(require_config(budget_cfg, "weekly.usd"))
    warning_ratio = to_float(require_config(budget_cfg, "alerts.warning_ratio"))
    critical_ratio = to_float(require_config(budget_cfg, "alerts.critical_ratio"))

    payload: dict[str, Any] = {
        "generated_at": now_stamp(),
        "timezone": timezone_name,
        "status": "degraded",
        "message": "",
        "source": {
            "usage_endpoint": USAGE_ENDPOINT,
            "costs_endpoint": COSTS_ENDPOINT,
            "lookback_days": LOOKBACK_DAYS,
        },
        "budgets": {
            "daily": {"tokens": daily_tokens_budget, "usd": daily_usd_budget},
            "weekly": {"tokens": weekly_tokens_budget, "usd": weekly_usd_budget},
        },
    }

    admin_key = os.getenv("OPENAI_ADMIN_KEY", "").strip()
    if not admin_key:
        payload["message"] = "OPENAI_ADMIN_KEY no configurada. No se pudo sincronizar uso real desde la API."
        payload["windows"] = {
            "daily": {"tokens_used": 0, "tokens_remaining": daily_tokens_budget, "usd_used": 0.0, "usd_remaining": daily_usd_budget, "requests": 0},
            "weekly": {"tokens_used": 0, "tokens_remaining": weekly_tokens_budget, "usd_used": 0.0, "usd_remaining": weekly_usd_budget, "requests": 0},
        }
        payload["recommendations"] = [
            "Configurar OPENAI_ADMIN_KEY para habilitar medicion exacta de consumo diario y semanal.",
            "Mientras tanto, usar el overlay local como presupuesto operativo estimado.",
        ]
        dump_snapshot(payload)
        print("[WARN] Snapshot de tokens generado sin sincronizacion API (falta OPENAI_ADMIN_KEY).")
        return 0

    headers = {
        "Authorization": f"Bearer {admin_key}",
        "Content-Type": "application/json",
    }

    try:
        usage_buckets = fetch_paginated(
            USAGE_ENDPOINT,
            headers,
            {
                "start_time": lookback_start,
                "bucket_width": "1d",
                "limit": LOOKBACK_DAYS,
            },
        )
        cost_buckets = fetch_paginated(
            COSTS_ENDPOINT,
            headers,
            {
                "start_time": lookback_start,
                "bucket_width": "1d",
                "limit": LOOKBACK_DAYS,
            },
        )
    except error.HTTPError as exc:
        payload["message"] = f"Error HTTP en API de uso/costos: {exc.code} {exc.reason}"
        payload["windows"] = {
            "daily": {"tokens_used": 0, "tokens_remaining": daily_tokens_budget, "usd_used": 0.0, "usd_remaining": daily_usd_budget, "requests": 0},
            "weekly": {"tokens_used": 0, "tokens_remaining": weekly_tokens_budget, "usd_used": 0.0, "usd_remaining": weekly_usd_budget, "requests": 0},
        }
        payload["recommendations"] = [
            "Revisar permisos del OPENAI_ADMIN_KEY para endpoints de organization usage/costs.",
            "Verificar que el key pertenezca a la organizacion correcta y tenga alcance admin.",
        ]
        dump_snapshot(payload)
        print(f"[WARN] Snapshot degradado por error HTTP: {exc.code} {exc.reason}")
        return 0
    except Exception as exc:  # noqa: BLE001
        payload["message"] = f"Fallo inesperado al consultar API de uso/costos: {exc}"
        payload["windows"] = {
            "daily": {"tokens_used": 0, "tokens_remaining": daily_tokens_budget, "usd_used": 0.0, "usd_remaining": daily_usd_budget, "requests": 0},
            "weekly": {"tokens_used": 0, "tokens_remaining": weekly_tokens_budget, "usd_used": 0.0, "usd_remaining": weekly_usd_budget, "requests": 0},
        }
        payload["recommendations"] = [
            "Reintentar sincronizacion en la siguiente corrida de build.",
            "Si persiste, registrar x-request-id y revisar conectividad/proxy.",
        ]
        dump_snapshot(payload)
        print(f"[WARN] Snapshot degradado por excepcion: {exc}")
        return 0

    daily_usage = extract_usage_totals(usage_buckets, daily_start)
    weekly_usage = extract_usage_totals(usage_buckets, weekly_start)
    daily_cost = extract_cost_totals(cost_buckets, daily_start)
    weekly_cost = extract_cost_totals(cost_buckets, weekly_start)

    daily_tokens_used = daily_usage["total_tokens"]
    weekly_tokens_used = weekly_usage["total_tokens"]
    daily_tokens_remaining = max(daily_tokens_budget - daily_tokens_used, 0)
    weekly_tokens_remaining = max(weekly_tokens_budget - weekly_tokens_used, 0)
    daily_usd_used = daily_cost["usd"]
    weekly_usd_used = weekly_cost["usd"]
    daily_usd_remaining = max(daily_usd_budget - daily_usd_used, 0.0)
    weekly_usd_remaining = max(weekly_usd_budget - weekly_usd_used, 0.0)

    day_elapsed_seconds = max(now_epoch - daily_start, 1)
    week_elapsed_seconds = max(now_epoch - weekly_start, 1)
    day_progress_ratio = min(day_elapsed_seconds / 86400, 1.0)
    week_progress_ratio = min(week_elapsed_seconds / (7 * 86400), 1.0)
    daily_ratio = daily_tokens_used / max(daily_tokens_budget, 1)
    weekly_ratio = weekly_tokens_used / max(weekly_tokens_budget, 1)

    recommendations = build_recommendations(
        daily_ratio=daily_ratio,
        weekly_ratio=weekly_ratio,
        day_progress_ratio=day_progress_ratio,
        week_progress_ratio=week_progress_ratio,
        daily_remaining_tokens=daily_tokens_remaining,
        weekly_remaining_tokens=weekly_tokens_remaining,
        warning_ratio=warning_ratio,
        critical_ratio=critical_ratio,
    )

    payload.update(
        {
            "status": "ok",
            "message": "Snapshot sincronizado desde Usage API y Costs API.",
            "windows": {
                "daily": {
                    "tokens_used": daily_tokens_used,
                    "tokens_remaining": daily_tokens_remaining,
                    "tokens_ratio": round(daily_ratio, 4),
                    "usd_used": round(daily_usd_used, 6),
                    "usd_remaining": round(daily_usd_remaining, 6),
                    "usd_ratio": round(daily_usd_used / max(daily_usd_budget, 0.000001), 4),
                    "requests": daily_usage["requests"],
                },
                "weekly": {
                    "tokens_used": weekly_tokens_used,
                    "tokens_remaining": weekly_tokens_remaining,
                    "tokens_ratio": round(weekly_ratio, 4),
                    "usd_used": round(weekly_usd_used, 6),
                    "usd_remaining": round(weekly_usd_remaining, 6),
                    "usd_ratio": round(weekly_usd_used / max(weekly_usd_budget, 0.000001), 4),
                    "requests": weekly_usage["requests"],
                },
            },
            "pace": {
                "daily_progress_ratio": round(day_progress_ratio, 4),
                "weekly_progress_ratio": round(week_progress_ratio, 4),
            },
            "alerts": {
                "warning_ratio": warning_ratio,
                "critical_ratio": critical_ratio,
                "daily_state": "critical" if daily_ratio >= critical_ratio else "warning" if daily_ratio >= warning_ratio else "ok",
                "weekly_state": "critical" if weekly_ratio >= critical_ratio else "warning" if weekly_ratio >= warning_ratio else "ok",
            },
            "model_breakdown": {
                "daily_top_models": daily_usage["top_models"],
                "weekly_top_models": weekly_usage["top_models"],
            },
            "cost_breakdown": {
                "daily_top_line_items": daily_cost["top_line_items"],
                "weekly_top_line_items": weekly_cost["top_line_items"],
            },
            "recommendations": recommendations,
        }
    )

    dump_snapshot(payload)
    output_path = ROOT / SNAPSHOT_PATH
    print(f"[OK] Snapshot de uso de tokens generado en: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
