from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import BillingRecord, BudgetSnapshot


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def build_budget_snapshot(
    *,
    store: Any,
    repo_root: Path,
    budget_policy: dict[str, Any],
) -> BudgetSnapshot:
    token_budget = load_json(repo_root / "00_sistema_tesis" / "config" / "token_budget.json", {})
    token_snapshot = load_json(repo_root / "00_sistema_tesis" / "config" / "token_usage_snapshot.json", {})
    now = datetime.now(UTC)
    local_windows = store.aggregate_billing_windows(now=now)
    warning_ratio = float(token_budget.get("alerts", {}).get("warning_ratio", 0.75))
    critical_ratio = float(token_budget.get("alerts", {}).get("critical_ratio", 0.9))

    global_daily_budget_tokens = int(token_budget.get("daily", {}).get("tokens", 40000))
    global_weekly_budget_tokens = int(token_budget.get("weekly", {}).get("tokens", 240000))
    global_daily_budget_usd = float(token_budget.get("daily", {}).get("usd", 8.0))
    global_weekly_budget_usd = float(token_budget.get("weekly", {}).get("usd", 48.0))

    snapshot_daily = token_snapshot.get("windows", {}).get("daily", {})
    snapshot_weekly = token_snapshot.get("windows", {}).get("weekly", {})
    global_daily_tokens_used = int(snapshot_daily.get("tokens_used", 0)) + int(local_windows["global"]["daily"]["estimated_tokens"])
    global_weekly_tokens_used = int(snapshot_weekly.get("tokens_used", 0)) + int(local_windows["global"]["weekly"]["estimated_tokens"])
    global_daily_usd_used = float(snapshot_daily.get("usd_used", 0.0)) + float(local_windows["global"]["daily"]["estimated_cost_usd"])
    global_weekly_usd_used = float(snapshot_weekly.get("usd_used", 0.0)) + float(local_windows["global"]["weekly"]["estimated_cost_usd"])

    domains_payload: dict[str, Any] = {}
    for domain, item in budget_policy.get("domains", {}).items():
        daily_ratio = float(item.get("daily_ratio", 0.0))
        weekly_ratio = float(item.get("weekly_ratio", 0.0))
        daily_budget_tokens = int(global_daily_budget_tokens * daily_ratio)
        weekly_budget_tokens = int(global_weekly_budget_tokens * weekly_ratio)
        daily_budget_usd = round(global_daily_budget_usd * daily_ratio, 4)
        weekly_budget_usd = round(global_weekly_budget_usd * weekly_ratio, 4)
        domain_daily_used_tokens = int(local_windows["domains"].get(domain, {}).get("daily", {}).get("estimated_tokens", 0))
        domain_weekly_used_tokens = int(local_windows["domains"].get(domain, {}).get("weekly", {}).get("estimated_tokens", 0))
        domain_daily_used_usd = float(local_windows["domains"].get(domain, {}).get("daily", {}).get("estimated_cost_usd", 0.0))
        domain_weekly_used_usd = float(local_windows["domains"].get(domain, {}).get("weekly", {}).get("estimated_cost_usd", 0.0))
        daily_status = classify_budget_status(domain_daily_used_tokens, daily_budget_tokens, warning_ratio, critical_ratio)
        weekly_status = classify_budget_status(domain_weekly_used_tokens, weekly_budget_tokens, warning_ratio, critical_ratio)
        domains_payload[domain] = {
            "daily": {
                "budget_tokens": daily_budget_tokens,
                "used_tokens": domain_daily_used_tokens,
                "remaining_tokens": max(daily_budget_tokens - domain_daily_used_tokens, 0),
                "budget_usd": daily_budget_usd,
                "used_usd": round(domain_daily_used_usd, 4),
                "remaining_usd": round(max(daily_budget_usd - domain_daily_used_usd, 0.0), 4),
                "status": daily_status,
            },
            "weekly": {
                "budget_tokens": weekly_budget_tokens,
                "used_tokens": domain_weekly_used_tokens,
                "remaining_tokens": max(weekly_budget_tokens - domain_weekly_used_tokens, 0),
                "budget_usd": weekly_budget_usd,
                "used_usd": round(domain_weekly_used_usd, 4),
                "remaining_usd": round(max(weekly_budget_usd - domain_weekly_used_usd, 0.0), 4),
                "status": weekly_status,
            },
            "action": resolve_domain_action(daily_status, weekly_status),
            "providers": list(item.get("providers", [])),
        }

    payload = {
        "global": {
            "daily": {
                "budget_tokens": global_daily_budget_tokens,
                "used_tokens": global_daily_tokens_used,
                "remaining_tokens": max(global_daily_budget_tokens - global_daily_tokens_used, 0),
                "budget_usd": global_daily_budget_usd,
                "used_usd": round(global_daily_usd_used, 4),
                "remaining_usd": round(max(global_daily_budget_usd - global_daily_usd_used, 0.0), 4),
                "status": classify_budget_status(global_daily_tokens_used, global_daily_budget_tokens, warning_ratio, critical_ratio),
            },
            "weekly": {
                "budget_tokens": global_weekly_budget_tokens,
                "used_tokens": global_weekly_tokens_used,
                "remaining_tokens": max(global_weekly_budget_tokens - global_weekly_tokens_used, 0),
                "budget_usd": global_weekly_budget_usd,
                "used_usd": round(global_weekly_usd_used, 4),
                "remaining_usd": round(max(global_weekly_budget_usd - global_weekly_usd_used, 0.0), 4),
                "status": classify_budget_status(global_weekly_tokens_used, global_weekly_budget_tokens, warning_ratio, critical_ratio),
            },
            "action": resolve_domain_action(
                classify_budget_status(global_daily_tokens_used, global_daily_budget_tokens, warning_ratio, critical_ratio),
                classify_budget_status(global_weekly_tokens_used, global_weekly_budget_tokens, warning_ratio, critical_ratio),
            ),
        },
        "domains": domains_payload,
        "source_snapshot": {
            "status": str(token_snapshot.get("status", "desconocido")),
            "message": str(token_snapshot.get("message", "")),
        },
    }
    return BudgetSnapshot(
        snapshot_id=f"BGT-{uuid4().hex[:12]}",
        scope="global_with_domains",
        domain="*",
        payload=payload,
        created_at=now.isoformat(),
    )


def simulate_budget_request(
    *,
    store: Any,
    repo_root: Path,
    budget_policy: dict[str, Any],
    domain: str,
    provider: str,
    estimated_cost_usd: float,
    estimated_tokens: int,
) -> dict[str, Any]:
    snapshot = build_budget_snapshot(store=store, repo_root=repo_root, budget_policy=budget_policy).payload
    global_daily = snapshot["global"]["daily"]
    domain_daily = snapshot["domains"].get(domain, {}).get("daily", {})
    global_would_exhaust = global_daily["used_tokens"] + estimated_tokens > global_daily["budget_tokens"] or global_daily["used_usd"] + estimated_cost_usd > global_daily["budget_usd"]
    domain_would_exhaust = domain_daily and (
        domain_daily["used_tokens"] + estimated_tokens > domain_daily["budget_tokens"]
        or domain_daily["used_usd"] + estimated_cost_usd > domain_daily["budget_usd"]
    )
    allowed = not global_would_exhaust and not domain_would_exhaust
    return {
        "domain": domain,
        "provider": provider,
        "allowed": allowed,
        "global_status": snapshot["global"]["daily"]["status"],
        "domain_status": snapshot["domains"].get(domain, {}).get("daily", {}).get("status", "sin_configuracion"),
        "resulting_action": "permitido" if allowed else "degradar_local_offline_manual",
        "estimated_cost_usd": estimated_cost_usd,
        "estimated_tokens": estimated_tokens,
    }


def build_billing_record(
    *,
    task_id: str,
    session_id: str,
    domain: str,
    provider: str,
    billing_mode: str,
    estimated_tokens: int,
    estimated_cost_usd: float,
    actual_tokens: int | None = None,
    actual_cost_usd: float | None = None,
) -> BillingRecord:
    return BillingRecord(
        billing_id=f"BIL-{uuid4().hex[:12]}",
        task_id=task_id,
        session_id=session_id,
        domain=domain,
        provider=provider,
        billing_mode=billing_mode,
        estimated_tokens=estimated_tokens,
        estimated_cost_usd=estimated_cost_usd,
        actual_tokens=actual_tokens,
        actual_cost_usd=actual_cost_usd,
        created_at=datetime.now(UTC).isoformat(),
    )


def classify_budget_status(used: int, budget: int, warning_ratio: float, critical_ratio: float) -> str:
    if budget <= 0:
        return "exhausted"
    ratio = used / max(budget, 1)
    if ratio >= 1.0:
        return "exhausted"
    if ratio >= critical_ratio:
        return "critical"
    if ratio >= warning_ratio:
        return "warning"
    return "ok"


def resolve_domain_action(daily_status: str, weekly_status: str) -> str:
    statuses = {daily_status, weekly_status}
    if "exhausted" in statuses:
        return "bloquear_nube"
    if "critical" in statuses or "warning" in statuses:
        return "degradar_local_offline_manual"
    return "permitir"
