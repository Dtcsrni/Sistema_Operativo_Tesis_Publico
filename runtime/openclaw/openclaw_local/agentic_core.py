from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .contracts import AgentProfile, ContextPacket, LearningEvent, MemoryRecord, ProviderPolicy, TaskEnvelope


SENSITIVE_MARKERS = {
    ".env",
    "api_key",
    "apikey",
    "bearer ",
    "credencial",
    "credential",
    "hf_",
    "ledger privado",
    "password",
    "secret",
    "ssh",
    "token",
    "val-step",
}

OPENROUTER_FREE_DAILY_WITHOUT_CREDITS = 50
OPENROUTER_FREE_DAILY_WITH_CREDITS = 1000
OPENROUTER_FREE_RPM = 20


def default_agent_profiles() -> list[AgentProfile]:
    shared_memory = ["trabajo", "episodica", "procedimental"]
    return [
        AgentProfile(
            profile_id="maestro_orquestador",
            name="Maestro Orquestador",
            role="orchestrator",
            description="Descompone tareas, asigna especialistas y decide gates humanos.",
            is_orchestrator=True,
            allowed_tools=["planning", "routing", "approvals", "mission_control"],
            allowed_memory_types=shared_memory,
            preferred_provider="llamacpp_local",
            fallback_providers=["deterministic_local", "manual"],
            max_context_tokens=8192,
        ),
        AgentProfile(
            profile_id="gobernador_tecnico",
            name="Gobernador Técnico",
            role="governor",
            description="Evalúa privacidad, riesgo, permisos, Step ID y bloqueo de acciones sensibles.",
            allowed_tools=["governance.preflight", "secret_scan", "policy_check"],
            allowed_memory_types=["episodica", "procedimental", "canonica"],
            preferred_provider="deterministic_local",
            fallback_providers=["llamacpp_local", "manual"],
            max_context_tokens=4096,
        ),
        AgentProfile(
            profile_id="administrador_contexto",
            name="Administrador de Contexto",
            role="context_manager",
            description="Construye paquetes de contexto, comprime memoria de trabajo y controla presupuesto de tokens.",
            allowed_tools=["context.fetch_compact", "memory.lookup", "summarize"],
            allowed_memory_types=["trabajo", "episodica", "semantica", "procedimental"],
            preferred_provider="llamacpp_local",
            fallback_providers=["deterministic_local"],
            max_context_tokens=8192,
        ),
        AgentProfile(
            profile_id="bibliotecario_semantico",
            name="Bibliotecario Semántico",
            role="semantic_librarian",
            description="Gestiona RAG, chunks con hash, embeddings y memoria semántica local.",
            allowed_tools=["rag.search", "rag.upsert", "weaviate", "jsonl_sync"],
            allowed_memory_types=["semantica", "episodica"],
            preferred_provider="llamacpp_local",
            fallback_providers=["deterministic_local"],
            max_context_tokens=8192,
        ),
        AgentProfile(
            profile_id="investigador_academico",
            name="Investigador Académico",
            role="researcher",
            description="Busca fuentes, extrae citas y construye matrices de evidencia.",
            allowed_tools=["web_research", "sources", "citation_check", "rag.search"],
            allowed_memory_types=["trabajo", "episodica", "semantica"],
            preferred_provider="openrouter_remote",
            fallback_providers=["llamacpp_local", "deterministic_local"],
            max_context_tokens=16384,
        ),
        AgentProfile(
            profile_id="ingeniero_implementacion",
            name="Ingeniero de Implementación",
            role="builder",
            description="Implementa código, scripts, pruebas y reproducibilidad bajo control humano.",
            allowed_tools=["filesystem_controlled", "tests", "build", "serena"],
            allowed_memory_types=shared_memory,
            preferred_provider="llamacpp_local",
            fallback_providers=["openrouter_remote", "deterministic_local"],
            max_context_tokens=12288,
        ),
        AgentProfile(
            profile_id="revisor_critico",
            name="Revisor Crítico",
            role="reviewer",
            description="Audita calidad, metodología, regresiones, riesgos y pruebas faltantes.",
            allowed_tools=["review", "tests", "quality_gate", "trace_lookup"],
            allowed_memory_types=["trabajo", "episodica", "semantica", "procedimental"],
            preferred_provider="openrouter_remote",
            fallback_providers=["llamacpp_local", "deterministic_local"],
            max_context_tokens=12288,
        ),
        AgentProfile(
            profile_id="curador_modelos_costos",
            name="Curador de Modelos y Costos",
            role="model_cost_curator",
            description="Selecciona modelos, administra cuotas, benchmarks, presupuestos y degradación.",
            allowed_tools=["provider_status", "budget", "benchmarks", "model_registry"],
            allowed_memory_types=["episodica", "procedimental"],
            preferred_provider="deterministic_local",
            fallback_providers=["llamacpp_local"],
            max_context_tokens=4096,
        ),
        AgentProfile(
            profile_id="operador_sistemas",
            name="Operador de Sistemas",
            role="systems_operator",
            description="Observa Docker, WSL, servicios, salud, logs y recuperación sin mutar sin gate.",
            allowed_tools=["doctor", "logs", "services_readonly", "runtime_probe"],
            allowed_memory_types=["trabajo", "episodica", "procedimental"],
            preferred_provider="deterministic_local",
            fallback_providers=["llamacpp_local", "manual"],
            max_context_tokens=4096,
        ),
    ]


def provider_policies() -> dict[str, ProviderPolicy]:
    return {
        "openrouter_remote": ProviderPolicy(
            provider_id="openrouter_remote",
            mode="remote_openai_compatible",
            privacy_classes=["public", "redacted", "private_non_sensitive"],
            quota_policy={
                "free_variant_rpm": OPENROUTER_FREE_RPM,
                "free_variant_daily_without_credits": OPENROUTER_FREE_DAILY_WITHOUT_CREDITS,
                "free_variant_daily_with_credits": OPENROUTER_FREE_DAILY_WITH_CREDITS,
                "strategy": "free_first_with_reserved_quota",
            },
            fallback_chain=["llamacpp_local", "deterministic_local", "manual"],
            requires_manual_approval=True,
            supports_tool_calling=True,
            supports_json_schema=True,
            cost_policy="free_first_then_budgeted_remote",
        ),
        "llamacpp_local": ProviderPolicy(
            provider_id="llamacpp_local",
            mode="local_openai_compatible",
            privacy_classes=["public", "redacted", "private_non_sensitive", "sensitive", "canonical_private"],
            quota_policy={"strategy": "local_resource_bound"},
            fallback_chain=["deterministic_local", "manual"],
            requires_manual_approval=False,
            supports_tool_calling=False,
            supports_json_schema=False,
            cost_policy="local_zero_marginal_cost",
        ),
        "deterministic_local": ProviderPolicy(
            provider_id="deterministic_local",
            mode="rules_rag_serena",
            privacy_classes=["public", "redacted", "private_non_sensitive", "sensitive", "canonical_private"],
            quota_policy={"strategy": "no_llm"},
            fallback_chain=["manual"],
            requires_manual_approval=False,
            cost_policy="no_provider_cost",
        ),
    }


def classify_context_sensitivity(task: TaskEnvelope) -> str:
    explicit = str(task.extra_context.get("privacy_class", task.extra_context.get("sensitivity", ""))).strip().lower()
    if explicit in {"public", "redacted", "private_non_sensitive", "sensitive", "canonical_private"}:
        return explicit
    haystack = " ".join([task.objective, " ".join(task.target_paths), str(task.extra_context)]).lower()
    if task.domain in {"personal", "administrativo"}:
        return "sensitive"
    if "canon" in haystack or "ledger" in haystack or "bitacora" in haystack:
        return "canonical_private"
    if any(marker in haystack for marker in SENSITIVE_MARKERS):
        return "sensitive"
    if task.domain in {"academico", "profesional"}:
        return "private_non_sensitive"
    return "redacted"


def openrouter_allowed_for_task(task: TaskEnvelope) -> tuple[bool, str]:
    if not _manual_openrouter_approval(task):
        return False, "openrouter_requiere_aprobacion_manual_por_tarea"
    if not _openrouter_key_available():
        return False, "openrouter_sin_api_key"
    sensitivity = classify_context_sensitivity(task)
    allowed_classes = set(provider_policies()["openrouter_remote"].privacy_classes)
    if sensitivity not in allowed_classes:
        return False, f"openrouter_bloqueado_por_privacidad:{sensitivity}"
    if _contains_sensitive_marker(task):
        return False, "openrouter_bloqueado_por_marcador_sensible"
    return True, "openrouter_aprobado_para_contexto_no_sensible"


def build_context_packet(task: TaskEnvelope, *, source_refs: list[str] | None = None, summary: str = "") -> ContextPacket:
    sensitivity = classify_context_sensitivity(task)
    allowed = ["deterministic_local", "llamacpp_local"]
    blocked_reason = ""
    ok, reason = openrouter_allowed_for_task(task)
    if ok:
        allowed.insert(0, "openrouter_remote")
    else:
        blocked_reason = reason
    return ContextPacket(
        packet_id=f"CTX-{uuid4().hex[:12]}",
        objective=task.objective,
        sensitivity=sensitivity,
        source_refs=source_refs or list(task.target_paths),
        summary=summary or task.objective[:500],
        token_budget=int(task.extra_context.get("token_budget", 8192) or 8192),
        allowed_providers=allowed,
        blocked_reason=blocked_reason,
    )


def build_memory_record(
    *,
    memory_type: str,
    sensitivity: str,
    source: str,
    content: str,
    ttl_seconds: int,
    allowed_roles: list[str] | None = None,
    allowed_providers: list[str] | None = None,
) -> MemoryRecord:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return MemoryRecord(
        memory_id=f"MEM-{uuid4().hex[:12]}",
        memory_type=memory_type,
        sensitivity=sensitivity,
        source=source,
        content=content,
        content_hash=digest,
        ttl_seconds=ttl_seconds,
        allowed_roles=allowed_roles or [],
        allowed_providers=allowed_providers or ["deterministic_local", "llamacpp_local"],
        created_at=datetime.now(UTC).isoformat(),
    )


def build_learning_event(
    *,
    scope: str,
    target: str,
    proposed_change: dict[str, Any],
    evidence: dict[str, Any],
    status: str = "proposed",
) -> LearningEvent:
    requires_gate = scope in {"canon", "security_policy", "secret_policy", "publication_policy"}
    return LearningEvent(
        event_id=f"LEARN-{uuid4().hex[:12]}",
        scope=scope,
        target=target,
        proposed_change=proposed_change,
        evidence=evidence,
        status=status,
        reversible=True,
        requires_human_gate=requires_gate,
        created_at=datetime.now(UTC).isoformat(),
    )


def _manual_openrouter_approval(task: TaskEnvelope) -> bool:
    return bool(task.extra_context.get("allow_openrouter")) or str(task.extra_context.get("runtime_override", "")).strip().lower() == "openrouter_remote"


def _openrouter_key_available() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY", "").strip() or os.getenv("OPENCLAW_OPENROUTER_API_KEY", "").strip())


def _contains_sensitive_marker(task: TaskEnvelope) -> bool:
    haystack = " ".join([task.objective, " ".join(task.target_paths), str(task.extra_context)]).lower()
    return any(marker in haystack for marker in SENSITIVE_MARKERS)
