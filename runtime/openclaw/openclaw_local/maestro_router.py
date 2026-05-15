from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .adaptive_router import build_adaptive_routing_snapshot, order_provider_candidates
from .contracts import MaestroRouteDecision, TaskEnvelope

PC_INDEX = Path("runtime/pc_control/benchmarks/index.json")
EDGE_INDEX = Path("runtime/edge_iot/benchmarks/index.json")
MOE_OVERVIEW = Path("runtime/pc_control/benchmarks/moe_battery_latest.json")

REALTIME_BLOCKED_MODELS = {"qwen3:14b", "phi4:14b", "qwen2.5-coder:14b"}
CHAT_BLOCKED_MODEL_TOKENS: set[str] = set()

INTENT_SLOS_MS = {
    "chat_fast": 60000,
    "coding": 120000,
    "ops": 60000,
    "research_synthesis": 300000,
    "fallback": 30000,
}


def maestro_enabled() -> bool:
    value = os.getenv("OPENCLAW_MAESTRO_ENABLED", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def maestro_message_hash(text: str) -> str:
    normalized = " ".join(text.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_maestro_route_decision(
    *,
    repo_root: Path,
    session_id: str,
    channel: str,
    peer_id: str,
    command: str,
    text: str,
    store: Any | None = None,
) -> MaestroRouteDecision:
    repo_root = Path(repo_root)
    snapshot = build_adaptive_routing_snapshot(repo_root, store=store)
    intent, confidence = _classify_intent(command=command, text=text)
    risk_level = _risk_level(intent=intent, command=command, text=text)
    request_kind = _request_kind_for_intent(intent)
    complexity = "high" if intent in {"coding", "research_synthesis"} else "low"
    task = TaskEnvelope(
        task_id=f"MAESTRO-{uuid4().hex[:10]}",
        title="Decision Maestro MoE",
        domain="academico",
        objective=text,
        complexity=complexity,
        risk_level=risk_level,
        mutates_state=risk_level == "high",
        requires_citations=intent == "research_synthesis",
        extra_context={"request_kind": request_kind, "maestro_intent": intent},
    )
    provider_order = order_provider_candidates(
        _candidate_provider_ids(),
        task,
        repo_root=repo_root,
        store=store,
    )
    model_stats = _moe_model_stats(repo_root)
    fallback_chain = _fallback_chain_for_intent(
        intent=intent,
        provider_order=provider_order,
        snapshot=snapshot,
        model_stats=model_stats,
    )
    selected_provider, selected_model = _split_chain_item(fallback_chain[0])
    node = _node_for_selection(intent=intent, provider=selected_provider)
    evidence_refs = _evidence_refs_for_decision(
        repo_root=repo_root,
        selected_model=selected_model,
        snapshot=snapshot,
        model_stats=model_stats,
    )
    slo_ms = INTENT_SLOS_MS[intent]
    telemetry_required = slo_ms > 30000 or intent == "research_synthesis"
    reason = _decision_reason(
        intent=intent,
        selected_provider=selected_provider,
        selected_model=selected_model,
        provider_order=provider_order,
        snapshot=snapshot,
        model_stats=model_stats,
    )
    agentic_capability = intent in {"coding", "research_synthesis"} or complexity == "high"
    return MaestroRouteDecision(
        route_id=f"ROUTE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}",
        session_id=session_id,
        intent=intent,
        risk_level=risk_level,
        selected_provider=selected_provider,
        selected_model=selected_model,
        node=node,
        confidence=confidence,
        evidence_refs=evidence_refs,
        fallback_chain=fallback_chain,
        telemetry_required=telemetry_required,
        decision_reason=reason,
        agentic_capability=agentic_capability,
        created_at=datetime.now(UTC).isoformat(),
    )


def maestro_profile_from_decision(decision: dict[str, Any]) -> dict[str, str]:
    intent = str(decision.get("intent", "fallback"))
    if intent == "chat_fast":
        profile = {"intent": "general_chat", "complexity": "low", "request_kind": "standard", "route_hint": "model_local"}
    elif intent == "ops":
        profile = {"intent": "system_status", "complexity": "low", "request_kind": "system", "route_hint": "deterministic_local"}
    elif intent == "coding":
        profile = {"intent": "coding", "complexity": "high", "request_kind": "coding", "route_hint": "model_desktop"}
    elif intent == "research_synthesis":
        profile = {"intent": "research", "complexity": "high", "request_kind": "deep", "route_hint": "model_desktop"}
    else:
        profile = {"intent": "general_chat", "complexity": "low", "request_kind": "standard", "route_hint": "model_local"}
    profile.update(
        {
            "confidence": f"{float(decision.get('confidence', 0.5)):.2f}",
            "semantic_status": "maestro_router",
            "maestro_route_id": str(decision.get("route_id", "")),
            "maestro_selected_provider": str(decision.get("selected_provider", "")),
            "maestro_selected_model": str(decision.get("selected_model", "")),
            "maestro_fallback_chain": json.dumps(decision.get("fallback_chain", []), ensure_ascii=False),
            "maestro_intent": intent,
        }
    )
    return profile


def _classify_intent(*, command: str, text: str) -> tuple[str, float]:
    lowered = text.lower()
    command = command.strip().lower()
    if command in {"estado", "modelos", "routing", "herramienta", "herramientas", "logs", "servicios"}:
        return "ops", 0.9
    if _contains_any(
        lowered,
        (
            "servicio",
            "systemctl",
            "reinicia",
            "estado",
            "modelo",
            "modelos",
            "routing",
            "latencia",
            "telemetría",
            "telemetria",
            "edge",
            "orange pi",
            "npu",
        ),
    ):
        return "ops", 0.84
    if _contains_any(
        lowered,
        (
            "bug",
            "codigo",
            "código",
            "debug",
            "error",
            "traceback",
            "stack trace",
            "pytest",
            "test",
            "refactor",
            "python",
            "script",
            "jsonl",
        ),
    ):
        return "coding", 0.86
    if _contains_any(
        lowered,
        (
            "paper",
            "tesis",
            "síntesis",
            "sintesis",
            "investiga",
            "investigación",
            "investigacion",
            "analiza",
            "benchmark",
            "evidencia",
            "fuentes",
            "trazabilidad",
        ),
    ):
        return "research_synthesis", 0.82
    if len(text.strip()) <= 120:
        return "chat_fast", 0.72
    return "fallback", 0.55


def _risk_level(*, intent: str, command: str, text: str) -> str:
    lowered = f"{command} {text}".lower()
    if _contains_any(
        lowered,
        (
            "borra",
            "elimina",
            "escribe",
            "modifica",
            "reinicia",
            "restart",
            "systemctl",
            "commit",
            "push",
            "instala",
            "deploy",
            "despliega",
        ),
    ):
        return "high"
    if intent in {"ops", "research_synthesis", "coding"}:
        return "medium"
    return "low"


def _request_kind_for_intent(intent: str) -> str:
    return {
        "chat_fast": "standard",
        "coding": "coding",
        "ops": "system",
        "research_synthesis": "reasoning",
        "fallback": "standard",
    }.get(intent, "standard")


def _candidate_provider_ids() -> list[str]:
    desktop = "pc_native_llamacpp" if os.getenv("OPENCLAW_DESKTOP_RUNTIME", "").strip().lower() == "llamacpp" else "desktop_compute"
    providers = [desktop, "local"]
    if os.getenv("OPENCLAW_GEMINI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}:
        providers.insert(0, "gemini_api")
    if os.getenv("OPENCLAW_EDGE_AUTO_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}:
        providers.extend(["ollama_local", "rknn_llm_experimental"])
    return providers


def _fallback_chain_for_intent(
    *,
    intent: str,
    provider_order: list[str],
    snapshot: Any,
    model_stats: dict[str, dict[str, Any]],
) -> list[str]:
    if intent == "chat_fast":
        chain = ["gemini_api:google/gemini-3-flash-preview", "desktop_compute:hermes3:8b", "local:sin_modelo"]
    elif intent == "ops":
        chain = ["desktop_compute:hermes3:8b", "local:sin_modelo"]
    elif intent == "coding":
        chain = ["desktop_compute:hermes3:8b", "gemini_api:google/gemini-3-flash-preview", "local:sin_modelo"]
    elif intent == "research_synthesis":
        chain = ["gemini_api:google/gemini-3-flash-preview", "desktop_compute:mistral-nemo:12b", "ollama_local:qwen3:4b"]
    else:
        chain = ["gemini_api:google/gemini-3-flash-preview", "desktop_compute:hermes3:8b", "local:sin_modelo"]
    if os.getenv("OPENCLAW_EDGE_AUTO_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}:
        chain.append("ollama_local:qwen3:4b")
    chain = [item for item in chain if _split_chain_item(item)[1] not in REALTIME_BLOCKED_MODELS]
    chain = [item for item in chain if not any(token in _split_chain_item(item)[1].lower() for token in CHAT_BLOCKED_MODEL_TOKENS)]
    if not snapshot.npu_promoted:
        chain = [item for item in chain if not item.startswith("rknn_llm_experimental:")]
    valid_models = {model for model, stats in model_stats.items() if stats.get("scientific_validity") == "valid_scientific_evidence"}
    if valid_models:
        chain = [
            item
            for item in chain
            if _split_chain_item(item)[0] == "local" or _split_chain_item(item)[1] in valid_models
        ]
    if intent in {"coding", "research_synthesis"}:
        return chain or ["local:sin_modelo"]
    ordered: list[str] = []
    for provider in provider_order:
        ordered.extend(item for item in chain if item.startswith(f"{provider}:") and item not in ordered)
    ordered.extend(item for item in chain if item not in ordered)
    return ordered or ["local:sin_modelo"]


def _node_for_selection(*, intent: str, provider: str) -> str:
    if intent == "ops":
        return "edge"
    if provider in {"pc_native_llamacpp", "desktop_compute"}:
        return "pc"
    if provider == "ollama_local":
        return "pc_or_edge_local"
    return "local"


def _evidence_refs_for_decision(
    *,
    repo_root: Path,
    selected_model: str,
    snapshot: Any,
    model_stats: dict[str, dict[str, Any]],
) -> list[str]:
    refs = [str(PC_INDEX), str(EDGE_INDEX)]
    if selected_model in model_stats and model_stats[selected_model].get("report"):
        refs.append(str(model_stats[selected_model]["report"]))
    if snapshot.pc_latest_run_id:
        refs.append(f"pc_latest_run_id:{snapshot.pc_latest_run_id}")
    if snapshot.edge_latest_run_id:
        refs.append(f"edge_latest_run_id:{snapshot.edge_latest_run_id}")
    return refs


def _decision_reason(
    *,
    intent: str,
    selected_provider: str,
    selected_model: str,
    provider_order: list[str],
    snapshot: Any,
    model_stats: dict[str, dict[str, Any]],
) -> str:
    stats = model_stats.get(selected_model, {})
    parts = [
        f"intent={intent}",
        f"selected={selected_provider}:{selected_model}",
        f"pc_validity={snapshot.pc_scientific_validity}",
        f"edge_validity={snapshot.edge_scientific_validity}",
        f"npu_promoted={snapshot.npu_promoted}",
        f"provider_order={','.join(provider_order)}",
    ]
    if stats:
        parts.append(f"model_p95_ms={stats.get('p95_latency_ms', '?')}")
        parts.append(f"model_tps={stats.get('mean_tokens_per_second', '?')}")
    if selected_model in REALTIME_BLOCKED_MODELS:
        parts.append("blocked_model_violation")
    return "; ".join(parts)


def _moe_model_stats(repo_root: Path) -> dict[str, dict[str, Any]]:
    overview = _read_json(repo_root / MOE_OVERVIEW)
    stats: dict[str, dict[str, Any]] = {}
    for run in overview.get("runs", []) if isinstance(overview, dict) else []:
        if not isinstance(run, dict):
            continue
        model = str(run.get("model", ""))
        report = _relative_report_path(str(run.get("report", "")))
        report_payload = _read_json(repo_root / report) if report is not None else {}
        summary = report_payload.get("summary", {}) if isinstance(report_payload, dict) else {}
        summary_stats = summary.get("statistics", {}) if isinstance(summary, dict) else {}
        stats[model] = {
            "status": run.get("status"),
            "scientific_validity": run.get("scientific_validity") or summary.get("scientific_validity"),
            "report": str(report) if report is not None else "",
            "run_id": run.get("run_id", ""),
            "p95_latency_ms": summary_stats.get("p95_latency_ms"),
            "mean_tokens_per_second": summary_stats.get("mean_tokens_per_second"),
        }
    return stats


def _relative_report_path(raw: str) -> Path | None:
    normalized = raw.replace("\\", "/")
    marker = "Sistema_Operativo_Tesis_Posgrado/"
    if marker in normalized:
        normalized = normalized.split(marker, 1)[1]
    return Path(normalized) if normalized else None


def _split_chain_item(item: str) -> tuple[str, str]:
    provider, _, model = item.partition(":")
    return provider, model


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)
