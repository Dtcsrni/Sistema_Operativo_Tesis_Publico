from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class TaskEnvelope:
    task_id: str
    title: str
    domain: str
    objective: str
    complexity: str = "medium"
    risk_level: str = "medium"
    mutates_state: bool = False
    target_paths: list[str] = field(default_factory=list)
    requires_citations: bool = False
    offline_allowed: bool = True
    preferred_mode: str = "auto"
    session_id: str = ""
    extra_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProviderDecision:
    domain: str
    risk_level: str
    requires_human_gate: bool
    provider: str
    mode: str
    model_class: str
    estimated_cost: float
    estimated_tokens: int
    budget_bucket: str
    credential_scope: str
    billing_mode: str
    session_mode: str
    fallback_chain: list[str]
    reason: str
    reasoning_quality: str = "basic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    task_id: str
    provider: str
    session_id: str
    prompt: str
    response: str
    context: dict[str, Any]
    payload_hash: str
    estimated_cost: float
    source_links: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ApprovalRequest:
    approval_id: str
    task_id: str
    diff_summary: str
    affected_targets: list[str]
    step_id_expected: str
    evidence_source_required: bool
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DomainPolicy:
    domain_id: str
    description: str
    allowed_backends: list[str]
    routing_preferences: list[str]
    workspace_roots: list[str]
    publicable: str | bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DomainSecretPolicy:
    domain_id: str
    network_mode: str
    allow_web_assisted: bool
    allow_api_formal: bool
    allow_publication: str | bool
    requires_strict_redaction: bool
    providers: dict[str, list[str]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LiteratureRecord:
    record_id: str
    tema: str
    pregunta: str
    fuente: str
    anio: str
    doi: str
    nivel_evidencia: str
    hallazgos_clave: list[str]
    contradicciones: list[str]
    relacion_con_hipotesis: str
    estado_verificacion: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClaimRecord:
    claim_id: str
    claim_text: str
    classification: str
    source_refs: list[str]
    confidence: str
    verification_status: str
    impact_on_thesis: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WritingDraft:
    section_id: str
    purpose: str
    source_refs: list[str]
    open_questions: list[str]
    markdown_body: str
    latex_body: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AcademicWorkPacket:
    packet_id: str
    task_id: str
    mode: str
    question: str
    scope: str
    sources: list[str]
    claims: list[ClaimRecord] = field(default_factory=list)
    literature_records: list[LiteratureRecord] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    traceability_links: list[str] = field(default_factory=list)
    writing_draft: WritingDraft | None = None
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.writing_draft is None:
            payload["writing_draft"] = None
        return payload


@dataclass(slots=True)
class RuntimeProbe:
    probe_id: str
    source_command: str
    system_state: str
    active_runtime: str
    payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkRecord:
    benchmark_id: str
    provider: str
    status: str
    latency_ms: float | None
    details: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RequestTrace:
    trace_id: str
    task_id: str
    channel: str
    command: str
    request_kind: str
    complexity: str
    selected_provider: str
    selected_model: str
    fallback_reason: str
    parse_ms: float | None
    profile_ms: float | None
    semantic_ms: float | None
    routing_ms: float | None
    web_search_ms: float | None
    provider_ms: float | None
    delivery_ms: float | None
    total_ms: float | None
    prompt_chars: int
    prompt_tokens_est: int
    payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SessionEnvelope:
    session_id: str
    channel: str
    peer_id: str
    operator_identity: str
    target_node: str
    provider_policy: str
    premium_auto: bool
    status: str
    title: str
    task_profile: str
    payload: dict[str, Any]
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SessionMessage:
    message_id: str
    session_id: str
    direction: str
    channel: str
    command: str
    text: str
    provider: str
    model: str
    status: str
    payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProviderProbe:
    probe_id: str
    provider: str
    status: str
    latency_ms: float | None
    error_code: str
    payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class QualityEvalResult:
    eval_id: str
    task_id: str
    domain: str
    question: str
    answer: str
    expected_sources: list[str]
    used_sources: list[str]
    supported_claims: int
    partially_supported_claims: int
    unsupported_claims: int
    groundedness_score: float | None
    faithfulness_score: float | None
    status: str
    payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NodeBenchmarkReport:
    report_id: str
    node: str
    status: str
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SecretResolution:
    resolution_id: str
    domain: str
    provider: str
    credential_scope: str
    status: str
    expected_variables: list[str]
    missing_variables: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BillingRecord:
    billing_id: str
    task_id: str
    session_id: str
    domain: str
    provider: str
    billing_mode: str
    estimated_tokens: int
    estimated_cost_usd: float
    actual_tokens: int | None
    actual_cost_usd: float | None
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BudgetSnapshot:
    snapshot_id: str
    scope: str
    domain: str
    payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VoiceMessageArtifact:
    artifact_id: str
    chat_id: str
    source: str
    source_file_id: str
    source_path: str
    source_mime_type: str
    duration_seconds: int | None
    language_code: str
    transcript_text: str
    transcript_provider: str
    transcript_model: str
    transcript_confidence: float | None
    tts_provider: str
    tts_model: str
    tts_voice: str
    reply_audio_path: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VoiceSessionState:
    chat_id: str
    enabled: bool
    style: str
    turn_count: int
    last_transcript: str
    last_response: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
