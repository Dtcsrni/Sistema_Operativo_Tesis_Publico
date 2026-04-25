from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .contracts import AcademicWorkPacket, ClaimRecord, EvidenceRecord, LiteratureRecord, ProviderDecision, TaskEnvelope, WritingDraft
from .budgeting import simulate_budget_request
from .policies import load_budget_policy, load_domain_secret_policies, load_provider_registry
from .runtime_status import summarize_host
from .secret_resolver import resolve_provider_secret


CLAIM_CLASSIFICATIONS = {
    "hecho_verificado",
    "inferencia_razonada",
    "hipotesis",
    "estimacion",
    "recomendacion_tentativa",
    "pendiente_de_validacion",
}
CRITICAL_CLASSIFICATIONS = {"hecho_verificado", "inferencia_razonada"}
ACADEMIC_MODES = {"estado_del_arte", "metodologia", "redaccion_tesis"}
CLOUD_PROVIDER_MODES = {"cloud_api", "cloud_web_assisted"}
HEAVY_ACADEMIC_MODES = {"estado_del_arte", "metodologia", "redaccion_tesis"}
HEAVY_TASK_MARKERS = {
    "comparacion_literatura",
    "estado_del_arte",
    "generacion_extensa",
    "rag",
    "sintesis_larga",
}
REASONING_TEXT_INDICATORS = {
    "por qué",
    "por que",
    "cómo funciona",
    "como funciona",
    "diseña",
    "arquitectura",
    "evalúa",
    "evalua",
    "critica",
    "analiza a fondo",
    "razona",
    "compara en detalle",
}
REASONING_TASK_MARKERS = {
    "analisis_critico",
    "comparacion_profunda",
    "diagnostico_complejo",
    "diseño_arquitectura",
    "evaluacion_riesgos",
    "reasoning",
    "sintesis_multimodal",
}


def route_task(
    task: TaskEnvelope,
    policies: dict[str, Any],
    *,
    repo_root: Path | None = None,
    store: Any | None = None,
) -> ProviderDecision:
    repo = repo_root or Path(__file__).resolve().parents[3]
    domain_policy = policies["domains"][task.domain]
    secret_domain_policy = load_domain_secret_policies(repo)["domains"][task.domain]
    provider_registry = load_provider_registry(repo)
    provider_index = {str(item["id"]): item for item in provider_registry.get("providers", [])}
    secret_policies = load_domain_secret_policies(repo)
    budget_policy = load_budget_policy(repo)
    academic_mode = str(task.extra_context.get("academic_mode", "")).strip()
    requires_human_gate = task.mutates_state or task.risk_level in {"high", "critical"}
    if academic_mode == "redaccion_tesis" and task.target_paths:
        requires_human_gate = True
    if academic_mode == "metodologia" and task.extra_context.get("changes_methodology"):
        requires_human_gate = True

    evaluations: list[str] = []
    candidates = _candidate_provider_order(task)
    protected_candidates: list[str] = []
    preferred_web = _preferred_web_assisted_provider(task)
    if preferred_web:
        protected_candidates = [preferred_web]
        if preferred_web != "chatgpt_plus_web_assisted":
            protected_candidates.append("chatgpt_plus_web_assisted")
    candidates = _rank_candidates_with_feedback(candidates, task, store=store, protected_candidates=protected_candidates)
    chosen_meta: dict[str, Any] | None = None
    chosen_secret = None
    for provider_id in candidates:
        provider_meta = provider_index.get(provider_id)
        if provider_meta is None:
            evaluations.append(f"{provider_id}: no_registrado")
            continue
        if provider_id not in domain_policy.allowed_backends:
            evaluations.append(f"{provider_id}: bloqueado_por_dominio")
            continue
        resolution = resolve_provider_secret(task.domain, provider_id, secret_policies=secret_policies)
        mode = str(provider_meta.get("mode", "local_rules"))
        is_cloud = mode in CLOUD_PROVIDER_MODES
        if is_cloud and mode == "cloud_web_assisted":
            if not (secret_domain_policy.allow_web_assisted and _web_assisted_enabled()):
                evaluations.append(f"{provider_id}: web_asistido_deshabilitado")
                continue
        elif is_cloud and not _cloud_providers_enabled(task):
            evaluations.append(f"{provider_id}: nube_deshabilitada_por_defecto")
            continue
        if task.preferred_mode == "offline" and is_cloud:
            evaluations.append(f"{provider_id}: omitido_por_modo_offline")
            continue
        if resolution.status == "missing":
            evaluations.append(f"{provider_id}: faltan_secretos")
            continue
        budget_result = {
            "allowed": True,
            "resulting_action": "permitir",
        }
        estimated_cost = float(provider_meta.get("estimated_cost_usd", 0.0))
        estimated_tokens = int(provider_meta.get("estimated_tokens", 0))
        if is_cloud and store is not None:
            budget_result = simulate_budget_request(
                store=store,
                repo_root=repo,
                budget_policy=budget_policy,
                domain=task.domain,
                provider=provider_id,
                estimated_cost_usd=estimated_cost,
                estimated_tokens=estimated_tokens,
            )
        if is_cloud and not budget_result["allowed"]:
            evaluations.append(f"{provider_id}: presupuesto_agotado")
            continue
        chosen_meta = {
            "id": provider_id,
            "mode": mode,
            "model_class": str(provider_meta.get("model_class", "local_rag_and_summary")),
            "estimated_cost": estimated_cost,
            "estimated_tokens": estimated_tokens,
            "billing_mode": str(provider_meta.get("billing_mode", _billing_mode_for(mode))),
            "session_mode": str(provider_meta.get("session_mode", _session_mode_for(mode))),
        }
        chosen_secret = resolution
        evaluations.append(f"{provider_id}: seleccionado")
        break

    if chosen_meta is None:
        chosen_meta = {
            "id": "local",
            "mode": "local_rules",
            "model_class": "rules_or_local_model",
            "estimated_cost": 0.0,
            "estimated_tokens": 0,
            "billing_mode": "estimated",
            "session_mode": "local_runtime",
        }
        chosen_secret = resolve_provider_secret(task.domain, "local", secret_policies=secret_policies)
        evaluations.append("local: degradacion_final")

    if chosen_meta["mode"] == "cloud_web_assisted" or task.risk_level == "critical":
        requires_human_gate = True

    fallback_chain = _build_fallback_chain(task, policies, chosen_meta["id"], provider_index)
    reason = _route_reason(task, chosen_meta["id"], evaluations)
    reasoning_quality = _reasoning_quality_for(chosen_meta["id"], provider_index)
    return ProviderDecision(
        domain=task.domain,
        risk_level=task.risk_level,
        requires_human_gate=requires_human_gate,
        provider=str(chosen_meta["id"]),
        mode=str(chosen_meta["mode"]),
        model_class=str(chosen_meta["model_class"]),
        estimated_cost=float(chosen_meta["estimated_cost"]),
        estimated_tokens=int(chosen_meta["estimated_tokens"]),
        budget_bucket=task.domain,
        credential_scope=chosen_secret.credential_scope if chosen_secret is not None else "sin_credencial",
        billing_mode=str(chosen_meta["billing_mode"]),
        session_mode=str(chosen_meta["session_mode"]),
        fallback_chain=fallback_chain,
        reason=reason,
        reasoning_quality=reasoning_quality,
    )


def _rank_candidates_with_feedback(
    candidates: list[str],
    task: TaskEnvelope,
    *,
    store: Any | None,
    protected_candidates: list[str] | None = None,
) -> list[str]:
    if store is None or not candidates:
        return candidates
    protected = [item for item in (protected_candidates or []) if item in candidates]
    if protected:
        candidates = [item for item in candidates if item not in protected]
    try:
        feedback = store.get_provider_outcome_stats(domain=task.domain, request_kind=str(task.extra_context.get("request_profile", "")).strip() or None, limit=100)
    except AttributeError:
        return protected + candidates

    ranked: list[tuple[float, int, str]] = []
    for index, provider_id in enumerate(candidates):
        stats = feedback.get(provider_id) or {}
        success_rate = float(stats.get("success_rate", 0.0) or 0.0)
        failure_rate = float(stats.get("failure_rate", 0.0) or 0.0)
        timeout_rate = float(stats.get("timeout_rate", 0.0) or 0.0)
        average_latency = stats.get("average_latency_ms")
        latency_penalty = 0.0
        if average_latency is not None:
            latency_penalty = min(float(average_latency) / 10_000.0, 0.5)
        score = success_rate - latency_penalty - (failure_rate * 0.35) - (timeout_rate * 0.5)
        ranked.append((score, index, provider_id))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    ranked_candidates = [item[2] for item in ranked]
    return protected + ranked_candidates


def build_evidence_record(
    *,
    task: TaskEnvelope,
    decision: ProviderDecision,
    prompt: str,
    response: str,
    context: dict[str, Any],
    estimated_cost: float,
    source_links: list[str],
    session_id: str,
) -> EvidenceRecord:
    payload = {
        "task": task.to_dict(),
        "decision": decision.to_dict(),
        "prompt": prompt,
        "response": response,
        "context": context,
        "estimated_cost": estimated_cost,
        "source_links": source_links,
        "session_id": session_id,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    payload_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    return EvidenceRecord(
        evidence_id=f"EVI-{uuid4().hex[:12]}",
        task_id=task.task_id,
        provider=decision.provider,
        session_id=session_id,
        prompt=prompt,
        response=response,
        context=context,
        payload_hash=payload_hash,
        estimated_cost=estimated_cost,
        source_links=source_links,
        created_at=datetime.now(UTC).isoformat(),
    )


def build_academic_packet(
    *,
    task: TaskEnvelope,
    question: str,
    scope: str,
    sources: list[str],
    claims: list[ClaimRecord],
    literature_records: list[LiteratureRecord],
    traceability_links: list[str],
    writing_draft: WritingDraft | None = None,
    summary: str = "",
) -> AcademicWorkPacket:
    mode = str(task.extra_context.get("academic_mode", "")).strip()
    if mode not in ACADEMIC_MODES:
        raise ValueError("TaskEnvelope.extra_context.academic_mode es obligatorio para paquetes académicos.")
    validate_academic_payload(
        mode=mode,
        claims=claims,
        literature_records=literature_records,
        writing_draft=writing_draft,
    )
    outputs = list(task.target_paths)
    return AcademicWorkPacket(
        packet_id=f"AWP-{uuid4().hex[:12]}",
        task_id=task.task_id,
        mode=mode,
        question=question,
        scope=scope,
        sources=sources,
        claims=claims,
        literature_records=literature_records,
        outputs=outputs,
        traceability_links=traceability_links,
        writing_draft=writing_draft,
        summary=summary or build_academic_summary(mode=mode, claims=claims, literature_records=literature_records),
    )


def validate_academic_payload(
    *,
    mode: str,
    claims: list[ClaimRecord],
    literature_records: list[LiteratureRecord],
    writing_draft: WritingDraft | None,
) -> None:
    if mode == "estado_del_arte":
        if not literature_records:
            raise ValueError("estado_del_arte requiere al menos un LiteratureRecord.")
        for record in literature_records:
            if not record.contradicciones:
                raise ValueError("estado_del_arte requiere contradicciones explícitas por registro.")
            if not record.estado_verificacion.strip():
                raise ValueError("estado_del_arte requiere estado_verificacion por registro.")
    for claim in claims:
        if claim.classification not in CLAIM_CLASSIFICATIONS:
            raise ValueError(f"Clasificación de afirmación inválida: {claim.classification}")
        if claim.classification in CRITICAL_CLASSIFICATIONS:
            if not claim.source_refs:
                raise ValueError("Las afirmaciones críticas requieren source_refs.")
            if claim.verification_status not in {"verificado", "fuente_primaria", "pendiente_de_validacion"}:
                raise ValueError("verification_status inválido para afirmación crítica.")
            if claim.verification_status == "pendiente_de_validacion" and claim.classification == "hecho_verificado":
                raise ValueError("hecho_verificado no puede quedar pendiente_de_validacion.")
    if mode == "redaccion_tesis":
        if writing_draft is None:
            raise ValueError("redaccion_tesis requiere WritingDraft.")
        if not writing_draft.markdown_body.strip() or not writing_draft.latex_body.strip():
            raise ValueError("WritingDraft requiere markdown_body y latex_body.")


def build_academic_summary(
    *,
    mode: str,
    claims: list[ClaimRecord],
    literature_records: list[LiteratureRecord],
) -> str:
    if mode == "estado_del_arte":
        return (
            f"Estado del arte con {len(literature_records)} registros, "
            f"{len(claims)} afirmaciones y contradicciones explícitas."
        )
    if mode == "metodologia":
        return f"Paquete metodológico con {len(claims)} afirmaciones clasificadas."
    if mode == "redaccion_tesis":
        return f"Borrador de redacción con {len(claims)} afirmaciones trazables."
    return "Paquete académico."


def render_literature_matrix(records: list[LiteratureRecord]) -> str:
    lines = [
        "# Matriz de Literatura",
        "",
        "Usar `data_contracts/literature_matrix_schema.md` como contrato minimo.",
        "",
        "| record_id | tema | pregunta | fuente | anio | doi | nivel_evidencia | hallazgos_clave | contradicciones | relacion_con_hipotesis | estado_verificacion |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            "| {record_id} | {tema} | {pregunta} | {fuente} | {anio} | {doi} | {nivel} | {hallazgos} | {contradicciones} | {hipotesis} | {estado} |".format(
                record_id=record.record_id,
                tema=_pipe_safe(record.tema),
                pregunta=_pipe_safe(record.pregunta),
                fuente=_pipe_safe(record.fuente),
                anio=_pipe_safe(record.anio),
                doi=_pipe_safe(record.doi),
                nivel=_pipe_safe(record.nivel_evidencia),
                hallazgos=_pipe_safe("; ".join(record.hallazgos_clave)),
                contradicciones=_pipe_safe("; ".join(record.contradicciones)),
                hipotesis=_pipe_safe(record.relacion_con_hipotesis),
                estado=_pipe_safe(record.estado_verificacion),
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_claim_matrix(claims: list[ClaimRecord]) -> str:
    lines = [
        "# Matriz de Afirmaciones y Evidencia",
        "",
        "Cada afirmacion importante debe enlazar a fuente, clase de afirmacion y nivel de confianza.",
        "",
        "| claim_id | afirmacion | clasificacion | fuentes | nivel_confianza | estado_verificacion | impacto_en_tesis |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for claim in claims:
        lines.append(
            "| {claim_id} | {text} | {classification} | {sources} | {confidence} | {verification} | {impact} |".format(
                claim_id=claim.claim_id,
                text=_pipe_safe(claim.claim_text),
                classification=_pipe_safe(claim.classification),
                sources=_pipe_safe("; ".join(claim.source_refs)),
                confidence=_pipe_safe(claim.confidence),
                verification=_pipe_safe(claim.verification_status),
                impact=_pipe_safe(claim.impact_on_thesis),
            )
        )
    lines.append("")
    return "\n".join(lines)


def build_methodology_note(packet: AcademicWorkPacket) -> str:
    lines = [
        "# Paquete Metodologico",
        "",
        f"## Pregunta\n{packet.question}",
        "",
        f"## Alcance\n{packet.scope}",
        "",
        "## Fuentes",
    ]
    lines.extend(f"- {item}" for item in packet.sources)
    lines.extend(
        [
            "",
            "## Afirmaciones clasificadas",
        ]
    )
    for claim in packet.claims:
        lines.append(
            f"- `{claim.classification}` | {claim.claim_text} | fuentes: {', '.join(claim.source_refs) or 'sin fuente'} | estado: {claim.verification_status}"
        )
    lines.extend(
        [
            "",
            "## Decisión o pendiente",
            packet.summary,
            "",
        ]
    )
    return "\n".join(lines)


def build_contrast_note(packet: AcademicWorkPacket) -> str:
    lines = [
        "# Nota Critica de Contraste",
        "",
        f"Pregunta: {packet.question}",
        "",
        "## Contradicciones y vacios",
    ]
    for record in packet.literature_records:
        lines.append(f"- `{record.record_id}`: {'; '.join(record.contradicciones)}")
    lines.extend(
        [
            "",
            "## Impacto sobre la tesis",
        ]
    )
    for claim in packet.claims:
        lines.append(f"- {claim.claim_text} -> {claim.impact_on_thesis}")
    lines.append("")
    return "\n".join(lines)


def build_writing_outputs(packet: AcademicWorkPacket) -> dict[str, str]:
    if packet.writing_draft is None:
        raise ValueError("El paquete no contiene WritingDraft.")
    return {
        "markdown": packet.writing_draft.markdown_body.strip() + "\n",
        "latex": packet.writing_draft.latex_body.strip() + "\n",
    }


def render_academic_artifacts(packet: AcademicWorkPacket) -> dict[str, str]:
    if packet.mode == "estado_del_arte":
        return {
            "docs/05_reproducibilidad/matriz-de-literatura.md": render_literature_matrix(packet.literature_records),
            "docs/05_reproducibilidad/matriz-de-afirmaciones-y-evidencia.md": render_claim_matrix(packet.claims),
            "runtime/openclaw/state/academico/notas/nota-critica-contraste.md": build_contrast_note(packet),
        }
    if packet.mode == "metodologia":
        return {
            "runtime/openclaw/state/academico/metodologia/ficha-de-estudio.md": build_methodology_note(packet),
            "runtime/openclaw/state/academico/metodologia/matriz-de-exploracion.md": render_claim_matrix(packet.claims),
        }
    if packet.mode == "redaccion_tesis":
        outputs = build_writing_outputs(packet)
        section_id = packet.writing_draft.section_id if packet.writing_draft else "borrador"
        return {
            f"runtime/openclaw/state/academico/drafts/{section_id}.md": outputs["markdown"],
            f"05_tesis_latex/sections/{section_id}.tex": outputs["latex"],
        }
    return {}
def default_data_dir(root: Path | None = None) -> Path:
    repo_root = root or Path(__file__).resolve().parents[3]
    data_dir = Path(os.getenv("OPENCLAW_DATA_DIR", repo_root / "runtime" / "openclaw" / "state"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _npu_explicitly_enabled(task: TaskEnvelope) -> bool:
    if task.extra_context.get("prefer_npu"):
        return True
    if task.extra_context.get("npu_bench_approved"):
        return True
    return str(task.extra_context.get("runtime_override", "")).strip().lower() == "rknn_llm_experimental"


def _task_requires_advanced_reasoning(task: TaskEnvelope) -> bool:
    """Detect when a task needs advanced reasoning capabilities."""
    task_type = str(task.extra_context.get("task_type", "")).strip().lower()
    if task_type in REASONING_TASK_MARKERS:
        return True
    request_kind = str(task.extra_context.get("request_profile", "")).strip().lower()
    if request_kind in {"reasoning", "deep", "research"}:
        return True
    academic_mode = str(task.extra_context.get("academic_mode", "")).strip()
    if academic_mode in HEAVY_ACADEMIC_MODES and task.complexity == "high":
        return True
    if task.requires_citations and task.complexity == "high":
        return True
    return False


def _env_flag_enabled(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _web_assisted_enabled() -> bool:
    return _env_flag_enabled("OPENCLAW_WEB_ENABLED", default=True)


def _preferred_web_assisted_provider(task: TaskEnvelope) -> str:
    explicit = str(task.extra_context.get("preferred_web_assisted", "") or "").strip().lower()
    if explicit in {"chatgpt_plus_web_assisted", "gemini_web_assisted"}:
        return explicit
    if task.extra_context.get("prefer_chatgpt_plus") is True:
        return "chatgpt_plus_web_assisted"
    return ""


def _cloud_providers_enabled(task: TaskEnvelope) -> bool:
    if task.extra_context.get("allow_cloud") is True:
        return True
    if str(task.extra_context.get("network_mode", "")).strip().lower() == "cloud_allowed":
        return True
    return _env_flag_enabled("OPENCLAW_CLOUD_ENABLED", default=False)


def _desktop_compute_enabled(task: TaskEnvelope) -> bool:
    if task.extra_context.get("disable_desktop_compute") is True:
        return False
    if task.extra_context.get("desktop_compute") is False:
        return False
    return _env_flag_enabled("OPENCLAW_DESKTOP_COMPUTE_ENABLED", default=True)


def _desktop_provider_id() -> str:
    runtime = os.getenv("OPENCLAW_DESKTOP_RUNTIME", "").strip().lower()
    if runtime == "llamacpp":
        return "pc_native_llamacpp"
    return "desktop_compute"


def _desktop_compute_requested(task: TaskEnvelope) -> bool:
    override = str(task.extra_context.get("runtime_override", "")).strip().lower()
    if override in {"desktop_compute", "pc_native_llamacpp", "desktop"}:
        return True
    if task.extra_context.get("desktop_compute") is True:
        return True
    task_type = str(task.extra_context.get("task_type", "")).strip().lower()
    if task_type in HEAVY_TASK_MARKERS:
        return True
    academic_mode = str(task.extra_context.get("academic_mode", "")).strip()
    if task.domain == "academico" and academic_mode in HEAVY_ACADEMIC_MODES:
        return task.complexity in {"medium", "high"} or task.requires_citations
    return task.domain in {"academico", "profesional"} and task.complexity == "high"


def _append_npu_if_requested(order: list[str], task: TaskEnvelope) -> list[str]:
    if _npu_explicitly_enabled(task) and "rknn_llm_experimental" not in order:
        order.append("rknn_llm_experimental")
    return order


def _task_requires_advanced_reasoning(task: TaskEnvelope) -> bool:
    task_type = str(task.extra_context.get("task_type", "")).strip().lower()
    if task_type in REASONING_TASK_MARKERS:
        return True
    request_kind = str(task.extra_context.get("request_kind", "")).strip()
    if task.complexity == "high" and request_kind == "reasoning":
        return True
    academic_mode = str(task.extra_context.get("academic_mode", "")).strip()
    if academic_mode in HEAVY_ACADEMIC_MODES and task.complexity == "high":
        return True
    objective = str(task.objective).lower()
    if any(indicator in objective for indicator in REASONING_TEXT_INDICATORS):
        return True
    return False


def _reasoning_quality_for(provider_id: str, provider_index: dict[str, Any]) -> str:
    provider_meta = provider_index.get(provider_id, {})
    tier = str(provider_meta.get("reasoning_tier", "")).strip().lower()
    if tier == "premium":
        return "advanced"
    if tier == "intermediate":
        return "intermediate"
    model_class = str(provider_meta.get("model_class", "")).strip()
    if model_class in {"cloud_assisted_premium"}:
        return "intermediate"
    if model_class in {"open_source_gpu_heavy"}:
        return "intermediate"
    return "basic"


def _candidate_provider_order(task: TaskEnvelope) -> list[str]:
    desktop_provider = _desktop_provider_id()
    if task.domain in {"edge", "administrativo", "personal"}:
        return ["local"]
    if task.preferred_mode == "offline" or task.extra_context.get("network_mode") == "offline":
        order = ["local", "ollama_local"]
        return _append_npu_if_requested(order, task)
    advanced_reasoning = _task_requires_advanced_reasoning(task)
    if task.domain == "profesional":
        preferred_web = _preferred_web_assisted_provider(task)
        if preferred_web:
            order = [preferred_web, "openai_api", "groq_api", "ollama_local", "local"]
            if preferred_web != "chatgpt_plus_web_assisted":
                order.insert(1, "chatgpt_plus_web_assisted")
            return _append_npu_if_requested(order, task)
        if advanced_reasoning:
            order = ["chatgpt_plus_web_assisted", desktop_provider, "openai_api", "groq_api", "ollama_local", "local"]
            if not _desktop_compute_enabled(task):
                order.remove(desktop_provider)
            return _append_npu_if_requested(order, task)
        if task.complexity == "high" or task.risk_level in {"high", "critical"}:
            if _cloud_providers_enabled(task) and not _desktop_compute_enabled(task):
                order = ["chatgpt_plus_web_assisted", "openai_api", "groq_api", "ollama_local", "local"]
                return _append_npu_if_requested(order, task)
            order = [desktop_provider, "chatgpt_plus_web_assisted", "ollama_local", "local", "groq_api", "openai_api"]
            if not _desktop_compute_enabled(task):
                order.remove(desktop_provider)
            return _append_npu_if_requested(order, task)
        if task.complexity == "medium":
            if _cloud_providers_enabled(task) and not _desktop_compute_requested(task):
                order = ["groq_api", "ollama_local", "openai_api", "local"]
                return _append_npu_if_requested(order, task)
            order = ["ollama_local", "local", desktop_provider, "groq_api", "openai_api"]
            if not _desktop_compute_enabled(task) or not _desktop_compute_requested(task):
                order.remove(desktop_provider)
            return _append_npu_if_requested(order, task)
        order = ["local", "ollama_local", "groq_api"]
        return _append_npu_if_requested(order, task)
    if task.domain == "academico":
        preferred_web = _preferred_web_assisted_provider(task)
        if preferred_web:
            order = [preferred_web, "gemini_web_assisted", "openai_api", "gemini_api", "groq_api", desktop_provider, "ollama_local", "local"]
            if preferred_web != "chatgpt_plus_web_assisted":
                order.insert(1, "chatgpt_plus_web_assisted")
            if not _desktop_compute_enabled(task):
                order = [item for item in order if item != desktop_provider]
            return _append_npu_if_requested(order, task)
        if _task_requires_advanced_reasoning(task):
            order = [
                "chatgpt_plus_web_assisted",
                "gemini_web_assisted",
                desktop_provider,
                "openai_api",
                "gemini_api",
                "groq_api",
                "ollama_local",
                "local",
            ]
            if not _desktop_compute_enabled(task):
                order = [item for item in order if item != desktop_provider]
            return _append_npu_if_requested(order, task)
        if task.complexity == "high" or task.requires_citations:
            if _cloud_providers_enabled(task) and not _desktop_compute_enabled(task):
                order = [
                    "gemini_api",
                    "gemini_web_assisted",
                    "openai_api",
                    "chatgpt_plus_web_assisted",
                    "groq_api",
                    "ollama_local",
                    "local",
                ]
                return _append_npu_if_requested(order, task)
            order = [
                desktop_provider,
                "ollama_local",
                "local",
                "gemini_api",
                "gemini_web_assisted",
                "openai_api",
                "chatgpt_plus_web_assisted",
                "groq_api",
            ]
            if not _desktop_compute_enabled(task):
                order.remove(desktop_provider)
            return _append_npu_if_requested(order, task)
        if task.complexity == "medium":
            if _desktop_compute_enabled(task):
                order = [desktop_provider]
                if _cloud_providers_enabled(task):
                    order.extend(["groq_api", "gemini_api", "gemini_web_assisted", "openai_api", "chatgpt_plus_web_assisted"])
                order.extend(["ollama_local", "local"])
                return _append_npu_if_requested(order, task)
            if _cloud_providers_enabled(task):
                order = ["groq_api", "gemini_api", "gemini_web_assisted", "openai_api", "chatgpt_plus_web_assisted", "ollama_local", "local"]
                return _append_npu_if_requested(order, task)
            order = ["ollama_local", "local"]
            return _append_npu_if_requested(order, task)
        order = [desktop_provider, "groq_api", "gemini_api", "gemini_web_assisted", "openai_api", "chatgpt_plus_web_assisted", "ollama_local", "local"]
        if not _desktop_compute_enabled(task):
            order = [item for item in order if item != desktop_provider]
        return _append_npu_if_requested(order, task)
    return ["local"]


def _build_fallback_chain(task: TaskEnvelope, policies: dict[str, Any], selected: str, provider_index: dict[str, Any]) -> list[str]:
    fallback_chain: list[str] = []
    allow_web_assisted = bool(load_domain_secret_policies(Path(__file__).resolve().parents[3])["domains"][task.domain].allow_web_assisted) and _web_assisted_enabled()
    for provider_id in _candidate_provider_order(task):
        if provider_id == selected:
            continue
        provider_meta = provider_index.get(provider_id)
        if provider_meta is None or provider_id not in policies["domains"][task.domain].allowed_backends:
            continue
        provider_mode = str(provider_meta.get("mode", "local_rules"))
        if provider_mode in CLOUD_PROVIDER_MODES:
            if provider_mode == "cloud_web_assisted" and allow_web_assisted:
                pass
            elif not _cloud_providers_enabled(task):
                continue
        fallback_chain.append(provider_id)
    fallback_chain.extend(["offline", "manual"])
    deduped: list[str] = []
    for item in fallback_chain:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _billing_mode_for(mode: str) -> str:
    if mode == "cloud_api":
        return "api_measured"
    if mode == "cloud_web_assisted":
        return "manual_web_assisted"
    return "estimated"


def _session_mode_for(mode: str) -> str:
    if mode == "cloud_api":
        return "direct_api_call"
    if mode == "cloud_web_assisted":
        return "human_supervised_web_session"
    return "local_runtime"


def _route_reason(task: TaskEnvelope, selected_provider: str, evaluations: list[str]) -> str:
    prefix = f"Proveedor seleccionado: {selected_provider} para dominio {task.domain}."
    if not evaluations:
        return prefix
    return prefix + " Evaluación: " + "; ".join(evaluations[:5])


def _pipe_safe(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ").strip()


def _reasoning_quality_for(provider_id: str, provider_index: dict[str, Any]) -> str:
    """Map provider to reasoning quality tier based on registry metadata."""
    provider_meta = provider_index.get(provider_id)
    if provider_meta is None:
        return "basic"
    tier = str(provider_meta.get("reasoning_tier", "")).strip().lower()
    if tier in {"premium", "advanced"}:
        return "advanced"
    if tier in {"intermediate", "mid"}:
        return "intermediate"
    model_class = str(provider_meta.get("model_class", "")).strip().lower()
    if "premium" in model_class:
        return "advanced"
    if "mid" in model_class or "heavy" in model_class:
        return "intermediate"
    return "basic"
