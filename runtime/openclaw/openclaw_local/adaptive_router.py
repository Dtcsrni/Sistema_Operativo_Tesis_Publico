from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import AdaptiveRoutingSnapshot, TaskEnvelope


PC_INDEX = Path("runtime/pc_control/benchmarks/index.json")
EDGE_INDEX = Path("runtime/edge_iot/benchmarks/index.json")
PC_REPORT = Path("runtime/pc_control/benchmarks/scientific_report_mistral_nemo_12b.json")
HERMES_INDEX_KEY = "hermes_benchmark"  # Clave en index.json tras run_pc_benchmark_hermes.py
EDGE_PROVIDER_IDS = {"rknn_llm_experimental"}


def build_adaptive_routing_snapshot(repo_root: Path, store: Any | None = None) -> AdaptiveRoutingSnapshot:
    pc_index = _read_json(repo_root / PC_INDEX)
    edge_index = _read_json(repo_root / EDGE_INDEX)
    pc_report = _read_json(repo_root / PC_REPORT)
    pc_stats = dict(((pc_report.get("summary") or {}).get("statistics") or {}) if isinstance(pc_report, dict) else {})
    pc_validity = str(pc_index.get("latest_scientific_validity", "") or "missing")
    edge_validity = str(edge_index.get("latest_scientific_validity", "") or "missing")
    pc_model = str(pc_index.get("primary_pc_model") or pc_stats.get("model") or "mistral-nemo:12b")

    # -- Hermes benchmark (D2=A): leer resultado de run_pc_benchmark_hermes.py
    hermes_data = pc_index.get(HERMES_INDEX_KEY, {})
    hermes_enabled = (
        bool(hermes_data.get("activate_recommended"))
        and _env_bool("OPENCLAW_HERMES_ENABLED", default=False)
    )
    hermes_model = hermes_data.get("model", "hermes3:8b")
    npu_promoted = edge_validity == "valid_scientific_evidence" and _env_bool("OPENCLAW_NPU_AUTO_PROMOTE", default=False)
    warnings: list[str] = []
    if pc_validity != "valid_scientific_evidence":
        warnings.append("pc_benchmark_not_scientifically_valid")
    if edge_validity != "valid_scientific_evidence":
        warnings.append("edge_npu_blocked_until_valid_benchmark")
    if not npu_promoted:
        warnings.append("npu_auto_promotion_disabled")
    recommendations = [
        {
            "profile": "fast_command",
            "provider": "deterministic_local",
            "model": os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b"),
            "node": "edge",
            "reason": "low latency continuity through rules, Serena and local context",
        },
        {
            "profile": "research_synthesis",
            "provider": _desktop_provider_id(),
            # Hermes toma prioridad sobre el modelo base si benchmark lo confirma (D2=A)
            "model": hermes_model if hermes_enabled else pc_model,
            "node": "pc",
            "reason": (
                f"hermes3:8b activado por benchmark (D2=A): avg {hermes_data.get('avg_tps', '?')} TPS"
                if hermes_enabled
                else f"latest PC benchmark {pc_validity}"
            ),
            "mean_latency_ms": hermes_data.get("avg_latency_ms") if hermes_enabled else pc_stats.get("mean_latency_ms"),
            "mean_tokens_per_second": hermes_data.get("avg_tps") if hermes_enabled else pc_stats.get("mean_tokens_per_second"),
            "hermes_active": hermes_enabled,
        },
        {
            "profile": "coding",
            "provider": "llamacpp_local",
            "model": os.getenv("OPENCLAW_CODER_MODEL", "hermes3:8b"),
            "node": "pc",
            "reason": "Ruta activa llama.cpp: preferir hermes3:8b y mantener 14B coder fuera del ruteo interactivo por defecto",
        },
        {
            "profile": "documented_external_router",
            "provider": "openrouter_remote",
            "model": os.getenv("OPENROUTER_MODEL", os.getenv("OPENCLAW_OPENROUTER_MODEL", "openrouter/free")),
            "node": "router",
            "enabled": bool(os.getenv("OPENROUTER_API_KEY", "").strip() or os.getenv("OPENCLAW_OPENROUTER_API_KEY", "").strip()),
            "reason": "OpenRouter is remote and manual per task; use llama.cpp local for private fallback",
        },
        {
            "profile": "npu",
            "provider": "rknn_llm_experimental",
            "model": "rkllm_preconverted",
            "node": "edge",
            "enabled": npu_promoted,
            "reason": "blocked unless edge benchmark is valid and OPENCLAW_NPU_AUTO_PROMOTE=1",
        },
    ]
    payload: dict[str, Any] = {
        "pc_index": _compact_index(pc_index),
        "edge_index": _compact_index(edge_index),
        "pc_statistics": pc_stats,
    }
    if store is not None:
        try:
            payload["recent_provider_outcomes"] = store.get_provider_outcome_stats(limit=100)
        except Exception as exc:  # pragma: no cover - defensive diagnostics only
            payload["provider_outcomes_error"] = str(exc)
    status = "ok" if pc_validity == "valid_scientific_evidence" else "degraded"
    return AdaptiveRoutingSnapshot(
        snapshot_id=f"ARS-{uuid4().hex[:12]}",
        status=status,
        pc_primary_model=pc_model,
        pc_scientific_validity=pc_validity,
        pc_latest_run_id=str(pc_index.get("latest_run_id", "")),
        edge_scientific_validity=edge_validity,
        edge_latest_run_id=str(edge_index.get("latest_run_id", "")),
        npu_promoted=npu_promoted,
        recommendations=recommendations,
        warnings=warnings,
        payload=payload,
        created_at=datetime.now(UTC).isoformat(),
    )


def order_provider_candidates(
    candidates: list[str],
    task: TaskEnvelope,
    *,
    repo_root: Path,
    store: Any | None = None,
) -> list[str]:
    if not candidates:
        return candidates
    if not _env_bool("OPENCLAW_ADAPTIVE_ROUTING_ENABLED", default=False):
        return candidates
    if _has_recent_feedback(store, task, candidates):
        return candidates
    snapshot = build_adaptive_routing_snapshot(repo_root, store=None)
    preferred = _preferred_provider_order(task, snapshot)
    ranked = [item for item in preferred if item in candidates]
    ranked.extend(item for item in candidates if item not in ranked)
    if not snapshot.npu_promoted and not _task_explicitly_requests_npu(task):
        ranked = [item for item in ranked if item != "rknn_llm_experimental"]
    return ranked


def _preferred_provider_order(task: TaskEnvelope, snapshot: AdaptiveRoutingSnapshot) -> list[str]:
    desktop = _desktop_provider_id()
    request_kind = str(task.extra_context.get("request_kind") or task.extra_context.get("request_profile") or "").lower()
    if request_kind in {"coding", "code"}:
        return _filter_edge_fallbacks([desktop, "openrouter_remote", "deterministic_local", "local", "openai_api", "groq_api"], task)
    if task.domain == "academico" or task.requires_citations or task.complexity == "high":
        return _filter_edge_fallbacks([desktop, "openrouter_remote", "deterministic_local", "local", "gemini_api", "openai_api", "chatgpt_plus_web_assisted", "groq_api"], task)
    return _filter_edge_fallbacks([desktop, "deterministic_local", "local", "openrouter_remote", "groq_api", "openai_api"], task)


def _edge_execution_requested(task: TaskEnvelope) -> bool:
    if os.getenv("OPENCLAW_EDGE_AUTO_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}:
        return True
    target = str(task.extra_context.get("target_node") or task.extra_context.get("assigned_node") or "").strip().lower()
    capability = str(task.extra_context.get("assigned_capability") or task.extra_context.get("agent_role") or "").strip().lower()
    if task.domain == "edge" or target in {"edge", "orange_pi", "tesis-edge"}:
        return True
    return capability in {"edge", "edge_agent", "npu", "iot"}


def _filter_edge_fallbacks(order: list[str], task: TaskEnvelope) -> list[str]:
    if _edge_execution_requested(task):
        return order
    return [provider for provider in order if provider not in EDGE_PROVIDER_IDS]


def _has_recent_feedback(store: Any | None, task: TaskEnvelope, candidates: list[str]) -> bool:
    if store is None:
        return False
    try:
        stats = store.get_provider_outcome_stats(
            domain=task.domain,
            request_kind=str(task.extra_context.get("request_profile", "")).strip() or None,
            limit=100,
        )
    except Exception:
        return False
    return any(int((stats.get(item) or {}).get("total", 0) or 0) > 0 for item in candidates)


def _task_explicitly_requests_npu(task: TaskEnvelope) -> bool:
    return bool(task.extra_context.get("prefer_npu")) or str(task.extra_context.get("runtime_override", "")).strip().lower() == "rknn_llm_experimental"


def _compact_index(payload: dict[str, Any]) -> dict[str, Any]:
    keys = ("node", "latest_run_id", "latest_status", "latest_scientific_validity", "primary_pc_model", "latest_jsonl", "updated_at")
    return {key: payload.get(key) for key in keys if key in payload}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _desktop_provider_id() -> str:
    return "llamacpp_local" if os.getenv("OPENCLAW_DESKTOP_RUNTIME", "").strip().lower() in {"", "llamacpp", "llamacpp_local"} else "desktop_compute"


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "si", "sí"}
