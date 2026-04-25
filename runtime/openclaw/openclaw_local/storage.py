from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .contracts import (
    AcademicWorkPacket,
    BenchmarkRecord,
    BillingRecord,
    BudgetSnapshot,
    EvidenceRecord,
    NodeBenchmarkReport,
    ProviderProbe,
    ProviderDecision,
    QualityEvalResult,
    RequestTrace,
    RuntimeProbe,
    SecretResolution,
    SessionEnvelope,
    SessionMessage,
    TaskEnvelope,
    VoiceMessageArtifact,
)


class OpenClawStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    approval_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    diff_summary TEXT NOT NULL,
                    affected_targets_json TEXT NOT NULL,
                    step_id_expected TEXT NOT NULL,
                    evidence_source_required INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    evidence_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS academic_packets (
                    packet_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS context_cache (
                    cache_key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runtime_probes (
                    probe_id TEXT PRIMARY KEY,
                    source_command TEXT NOT NULL,
                    system_state TEXT NOT NULL,
                    active_runtime TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    benchmark_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latency_ms REAL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS request_traces (
                    trace_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    command TEXT NOT NULL,
                    request_kind TEXT NOT NULL,
                    complexity TEXT NOT NULL,
                    selected_provider TEXT NOT NULL,
                    selected_model TEXT NOT NULL,
                    fallback_reason TEXT NOT NULL,
                    parse_ms REAL,
                    profile_ms REAL,
                    semantic_ms REAL,
                    routing_ms REAL,
                    web_search_ms REAL,
                    provider_ms REAL,
                    delivery_ms REAL,
                    total_ms REAL,
                    prompt_chars INTEGER NOT NULL,
                    prompt_tokens_est INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    channel TEXT NOT NULL,
                    peer_id TEXT NOT NULL,
                    operator_identity TEXT NOT NULL,
                    target_node TEXT NOT NULL,
                    provider_policy TEXT NOT NULL,
                    premium_auto INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    title TEXT NOT NULL,
                    task_profile TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    command TEXT NOT NULL,
                    text TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS provider_probes (
                    probe_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    latency_ms REAL,
                    error_code TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS quality_eval_results (
                    eval_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    expected_sources_json TEXT NOT NULL,
                    used_sources_json TEXT NOT NULL,
                    supported_claims INTEGER NOT NULL,
                    partially_supported_claims INTEGER NOT NULL,
                    unsupported_claims INTEGER NOT NULL,
                    groundedness_score REAL,
                    faithfulness_score REAL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS node_benchmark_reports (
                    report_id TEXT PRIMARY KEY,
                    node TEXT NOT NULL,
                    status TEXT NOT NULL,
                    p50_latency_ms REAL,
                    p95_latency_ms REAL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS secret_resolutions (
                    resolution_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS billing_records (
                    billing_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    billing_mode TEXT NOT NULL,
                    estimated_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    actual_tokens INTEGER,
                    actual_cost_usd REAL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS budget_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    scope TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS telegram_events (
                    event_id TEXT PRIMARY KEY,
                    update_id INTEGER NOT NULL,
                    chat_id TEXT NOT NULL,
                    command TEXT NOT NULL,
                    authorized INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS telegram_voice_events (
                    artifact_id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_file_id TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    source_mime_type TEXT NOT NULL,
                    duration_seconds INTEGER,
                    language_code TEXT NOT NULL,
                    transcript_text TEXT NOT NULL,
                    transcript_provider TEXT NOT NULL,
                    transcript_model TEXT NOT NULL,
                    transcript_confidence REAL,
                    tts_provider TEXT NOT NULL,
                    tts_model TEXT NOT NULL,
                    tts_voice TEXT NOT NULL,
                    reply_audio_path TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    request_kind TEXT NOT NULL,
                    complexity TEXT NOT NULL,
                    latency_ms REAL,
                    error_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def save_task(self, task: TaskEnvelope, decision: ProviderDecision) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tasks(task_id, payload_json, decision_json, created_at)
                VALUES(?, ?, ?, ?)
                """,
                (
                    task.task_id,
                    json.dumps(task.to_dict(), ensure_ascii=False),
                    json.dumps(decision.to_dict(), ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def save_session(self, session: SessionEnvelope) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions(
                    session_id, channel, peer_id, operator_identity, target_node,
                    provider_policy, premium_auto, status, title, task_profile,
                    payload_json, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.channel,
                    session.peer_id,
                    session.operator_identity,
                    session.target_node,
                    session.provider_policy,
                    1 if session.premium_auto else 0,
                    session.status,
                    session.title,
                    session.task_profile,
                    json.dumps(session.to_dict(), ensure_ascii=False),
                    session.created_at,
                    session.updated_at,
                ),
            )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        return json.loads(row["payload_json"])

    def list_sessions(self, *, channel: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM sessions"
        params: list[Any] = []
        if channel:
            query += " WHERE channel = ?"
            params.append(channel)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_session_message(self, message: SessionMessage) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO session_messages(
                    message_id, session_id, direction, channel, command, text,
                    provider, model, status, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.session_id,
                    message.direction,
                    message.channel,
                    message.command,
                    message.text,
                    message.provider,
                    message.model,
                    message.status,
                    json.dumps(message.to_dict(), ensure_ascii=False),
                    message.created_at,
                ),
            )

    def list_session_messages(self, session_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM session_messages WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in reversed(rows)]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return {
            "task_id": row["task_id"],
            "payload": json.loads(row["payload_json"]),
            "decision": json.loads(row["decision_json"]),
            "created_at": row["created_at"],
        }

    def create_approval_request(
        self,
        *,
        task: TaskEnvelope,
        decision: ProviderDecision,
        diff_summary: str,
        affected_targets: list[str],
        step_id_expected: str,
        evidence_source_required: bool,
    ) -> str:
        approval_id = f"APR-{task.task_id}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO approvals(
                    approval_id, task_id, status, diff_summary, affected_targets_json,
                    step_id_expected, evidence_source_required, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    task.task_id,
                    "pending" if decision.requires_human_gate else "not_required",
                    diff_summary,
                    json.dumps(affected_targets, ensure_ascii=False),
                    step_id_expected,
                    1 if evidence_source_required else 0,
                    datetime.now(UTC).isoformat(),
                ),
            )
        return approval_id

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM approvals WHERE status = 'pending' ORDER BY created_at").fetchall()
        return [
            {
                "approval_id": row["approval_id"],
                "task_id": row["task_id"],
                "diff_summary": row["diff_summary"],
                "affected_targets": json.loads(row["affected_targets_json"]),
                "step_id_expected": row["step_id_expected"],
                "evidence_source_required": bool(row["evidence_source_required"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def get_latest_approval_for_task(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "approval_id": row["approval_id"],
            "task_id": row["task_id"],
            "status": row["status"],
            "diff_summary": row["diff_summary"],
            "affected_targets": json.loads(row["affected_targets_json"]),
            "step_id_expected": row["step_id_expected"],
            "evidence_source_required": bool(row["evidence_source_required"]),
            "created_at": row["created_at"],
        }

    def mark_approval(self, approval_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE approvals SET status = ? WHERE approval_id = ?", (status, approval_id))

    def save_evidence(self, record: EvidenceRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO evidence(evidence_id, task_id, provider, payload_hash, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    record.evidence_id,
                    record.task_id,
                    record.provider,
                    record.payload_hash,
                    json.dumps(record.to_dict(), ensure_ascii=False),
                    record.created_at,
                ),
            )

    def list_evidence_for_task(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM evidence WHERE task_id = ? ORDER BY created_at",
                (task_id,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def get_latest_evidence_for_task(self, task_id: str) -> dict[str, Any] | None:
        items = self.list_evidence_for_task(task_id)
        return items[-1] if items else None

    def save_academic_packet(self, packet: AcademicWorkPacket, payload_hash: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO academic_packets(packet_id, task_id, mode, payload_hash, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    packet.packet_id,
                    packet.task_id,
                    packet.mode,
                    payload_hash,
                    json.dumps(packet.to_dict(), ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get_latest_academic_packet_for_task(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM academic_packets WHERE task_id = ? ORDER BY created_at DESC LIMIT 1",
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        payload["_payload_hash"] = row["payload_hash"]
        payload["_created_at"] = row["created_at"]
        return payload

    def list_academic_packets(self, mode: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM academic_packets"
        params: tuple[Any, ...] = ()
        if mode:
            query += " WHERE mode = ?"
            params = (mode,)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["payload_json"])
            payload["_payload_hash"] = row["payload_hash"]
            payload["_created_at"] = row["created_at"]
            items.append(payload)
        return items

    def cache_context(self, cache_key: str, value: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO context_cache(cache_key, value_json, created_at)
                VALUES(?, ?, ?)
                """,
                (
                    cache_key,
                    json.dumps(value, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )

    def get_cached_context(self, cache_key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value_json FROM context_cache WHERE cache_key = ?", (cache_key,)).fetchone()
        if row is None:
            return None
        return json.loads(row["value_json"])

    def save_runtime_probe(self, probe: RuntimeProbe) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runtime_probes(
                    probe_id, source_command, system_state, active_runtime, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    probe.probe_id,
                    probe.source_command,
                    probe.system_state,
                    probe.active_runtime,
                    json.dumps(probe.to_dict(), ensure_ascii=False),
                    probe.created_at,
                ),
            )

    def get_latest_runtime_probe(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM runtime_probes ORDER BY created_at DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return json.loads(row["payload_json"])

    def save_benchmark_record(self, record: BenchmarkRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO benchmark_runs(
                    benchmark_id, provider, status, latency_ms, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    record.benchmark_id,
                    record.provider,
                    record.status,
                    record.latency_ms,
                    json.dumps(record.to_dict(), ensure_ascii=False),
                    record.created_at,
                ),
            )

    def list_benchmark_runs(self, provider: str | None = None, *, limit: int = 10) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM benchmark_runs"
        params: list[Any] = []
        if provider:
            query += " WHERE provider = ?"
            params.append(provider)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_request_trace(self, trace: RequestTrace) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO request_traces(
                    trace_id, task_id, channel, command, request_kind, complexity,
                    selected_provider, selected_model, fallback_reason,
                    parse_ms, profile_ms, semantic_ms, routing_ms, web_search_ms,
                    provider_ms, delivery_ms, total_ms, prompt_chars, prompt_tokens_est,
                    payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace.trace_id,
                    trace.task_id,
                    trace.channel,
                    trace.command,
                    trace.request_kind,
                    trace.complexity,
                    trace.selected_provider,
                    trace.selected_model,
                    trace.fallback_reason,
                    trace.parse_ms,
                    trace.profile_ms,
                    trace.semantic_ms,
                    trace.routing_ms,
                    trace.web_search_ms,
                    trace.provider_ms,
                    trace.delivery_ms,
                    trace.total_ms,
                    trace.prompt_chars,
                    trace.prompt_tokens_est,
                    json.dumps(trace.to_dict(), ensure_ascii=False),
                    trace.created_at,
                ),
            )

    def list_request_traces(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM request_traces ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_provider_probe(self, probe: ProviderProbe) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO provider_probes(
                    probe_id, provider, status, latency_ms, error_code, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    probe.probe_id,
                    probe.provider,
                    probe.status,
                    probe.latency_ms,
                    probe.error_code,
                    json.dumps(probe.to_dict(), ensure_ascii=False),
                    probe.created_at,
                ),
            )

    def list_provider_probes(self, provider: str | None = None, *, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM provider_probes"
        params: list[Any] = []
        if provider:
            query += " WHERE provider = ?"
            params.append(provider)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_quality_eval_result(self, result: QualityEvalResult) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO quality_eval_results(
                    eval_id, task_id, domain, question, answer,
                    expected_sources_json, used_sources_json,
                    supported_claims, partially_supported_claims, unsupported_claims,
                    groundedness_score, faithfulness_score, status, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.eval_id,
                    result.task_id,
                    result.domain,
                    result.question,
                    result.answer,
                    json.dumps(result.expected_sources, ensure_ascii=False),
                    json.dumps(result.used_sources, ensure_ascii=False),
                    result.supported_claims,
                    result.partially_supported_claims,
                    result.unsupported_claims,
                    result.groundedness_score,
                    result.faithfulness_score,
                    result.status,
                    json.dumps(result.to_dict(), ensure_ascii=False),
                    result.created_at,
                ),
            )

    def list_quality_eval_results(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM quality_eval_results ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_node_benchmark_report(self, report: NodeBenchmarkReport) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO node_benchmark_reports(
                    report_id, node, status, p50_latency_ms, p95_latency_ms, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.report_id,
                    report.node,
                    report.status,
                    report.p50_latency_ms,
                    report.p95_latency_ms,
                    json.dumps(report.to_dict(), ensure_ascii=False),
                    report.created_at,
                ),
            )

    def list_node_benchmark_reports(self, node: str | None = None, *, limit: int = 50) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM node_benchmark_reports"
        params: list[Any] = []
        if node:
            query += " WHERE node = ?"
            params.append(node)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_secret_resolution(self, resolution: SecretResolution) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO secret_resolutions(
                    resolution_id, domain, provider, status, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    resolution.resolution_id,
                    resolution.domain,
                    resolution.provider,
                    resolution.status,
                    json.dumps(resolution.to_dict(), ensure_ascii=False),
                    resolution.created_at,
                ),
            )

    def list_secret_resolutions(self, domain: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM secret_resolutions"
        params: list[Any] = []
        if domain:
            query += " WHERE domain = ?"
            params.append(domain)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_billing_record(self, record: BillingRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO billing_records(
                    billing_id, task_id, session_id, domain, provider, billing_mode,
                    estimated_tokens, estimated_cost_usd, actual_tokens, actual_cost_usd, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.billing_id,
                    record.task_id,
                    record.session_id,
                    record.domain,
                    record.provider,
                    record.billing_mode,
                    record.estimated_tokens,
                    record.estimated_cost_usd,
                    record.actual_tokens,
                    record.actual_cost_usd,
                    json.dumps(record.to_dict(), ensure_ascii=False),
                    record.created_at,
                ),
            )

    def list_billing_records(self, *, domain: str | None = None, provider: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        query = "SELECT payload_json FROM billing_records"
        clauses: list[str] = []
        params: list[Any] = []
        if domain:
            clauses.append("domain = ?")
            params.append(domain)
        if provider:
            clauses.append("provider = ?")
            params.append(provider)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def aggregate_billing_windows(self, *, now: datetime) -> dict[str, Any]:
        rows = self.list_billing_records(limit=1000)
        daily_key = now.date().isoformat()
        current_iso = now.isocalendar()
        weekly_key = (current_iso.year, current_iso.week)
        payload: dict[str, Any] = {
            "global": {
                "daily": {"estimated_tokens": 0, "estimated_cost_usd": 0.0},
                "weekly": {"estimated_tokens": 0, "estimated_cost_usd": 0.0},
            },
            "domains": {},
        }
        for row in rows:
            created_at = str(row.get("created_at", ""))
            row_domain = str(row.get("domain", ""))
            if row_domain not in payload["domains"]:
                payload["domains"][row_domain] = {
                    "daily": {"estimated_tokens": 0, "estimated_cost_usd": 0.0},
                    "weekly": {"estimated_tokens": 0, "estimated_cost_usd": 0.0},
                }
            estimated_tokens = int(row.get("estimated_tokens") or 0)
            estimated_cost_usd = float(row.get("estimated_cost_usd") or 0.0)
            if created_at.startswith(daily_key):
                payload["global"]["daily"]["estimated_tokens"] += estimated_tokens
                payload["global"]["daily"]["estimated_cost_usd"] += estimated_cost_usd
                payload["domains"][row_domain]["daily"]["estimated_tokens"] += estimated_tokens
                payload["domains"][row_domain]["daily"]["estimated_cost_usd"] += estimated_cost_usd
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                created_iso = created_dt.isocalendar()
                same_week = (created_iso.year, created_iso.week) == weekly_key
            except ValueError:
                same_week = False
            if same_week:
                payload["global"]["weekly"]["estimated_tokens"] += estimated_tokens
                payload["global"]["weekly"]["estimated_cost_usd"] += estimated_cost_usd
                payload["domains"][row_domain]["weekly"]["estimated_tokens"] += estimated_tokens
                payload["domains"][row_domain]["weekly"]["estimated_cost_usd"] += estimated_cost_usd
        return payload

    def save_budget_snapshot(self, snapshot: BudgetSnapshot) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO budget_snapshots(snapshot_id, scope, domain, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    snapshot.snapshot_id,
                    snapshot.scope,
                    snapshot.domain,
                    json.dumps(snapshot.to_dict(), ensure_ascii=False),
                    snapshot.created_at,
                ),
            )

    def get_latest_budget_snapshot(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM budget_snapshots ORDER BY created_at DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return json.loads(row["payload_json"])

    def save_telegram_event(
        self,
        *,
        event_id: str,
        update_id: int,
        chat_id: str,
        command: str,
        authorized: bool,
        status: str,
        payload: dict[str, Any],
    ) -> None:
        created_at = datetime.now(UTC).isoformat()
        payload = {**payload, "created_at": created_at}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO telegram_events(
                    event_id, update_id, chat_id, command, authorized, status, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    update_id,
                    chat_id,
                    command,
                    1 if authorized else 0,
                    status,
                    json.dumps(payload, ensure_ascii=False),
                    created_at,
                ),
            )

    def list_telegram_events(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM telegram_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def save_telegram_voice_event(self, artifact: VoiceMessageArtifact, payload: dict[str, Any]) -> None:
        created_at = datetime.now(UTC).isoformat()
        record_payload = {**payload, "created_at": created_at, "artifact": artifact.to_dict()}
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO telegram_voice_events(
                    artifact_id, chat_id, source, source_file_id, source_path, source_mime_type,
                    duration_seconds, language_code, transcript_text, transcript_provider,
                    transcript_model, transcript_confidence, tts_provider, tts_model, tts_voice,
                    reply_audio_path, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.artifact_id,
                    artifact.chat_id,
                    artifact.source,
                    artifact.source_file_id,
                    artifact.source_path,
                    artifact.source_mime_type,
                    artifact.duration_seconds,
                    artifact.language_code,
                    artifact.transcript_text,
                    artifact.transcript_provider,
                    artifact.transcript_model,
                    artifact.transcript_confidence,
                    artifact.tts_provider,
                    artifact.tts_model,
                    artifact.tts_voice,
                    artifact.reply_audio_path,
                    json.dumps(record_payload, ensure_ascii=False),
                    created_at,
                ),
            )

    def list_telegram_voice_events(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM telegram_voice_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def log_task_outcome(
        self,
        *,
        task_id: str,
        domain: str,
        provider: str,
        outcome: str,
        request_kind: str,
        complexity: str,
        latency_ms: float | None,
        error_text: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "task_id": task_id,
            "domain": domain,
            "provider": provider,
            "outcome": outcome,
            "request_kind": request_kind,
            "complexity": complexity,
            "latency_ms": latency_ms,
            "error_text": error_text,
            "payload": payload or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO task_outcomes(
                    outcome_id, task_id, domain, provider, outcome, request_kind,
                    complexity, latency_ms, error_text, payload_json, created_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"OUT-{task_id}",
                    task_id,
                    domain,
                    provider,
                    outcome,
                    request_kind,
                    complexity,
                    latency_ms,
                    error_text,
                    json.dumps(record, ensure_ascii=False),
                    record["created_at"],
                ),
            )

    def list_task_outcomes(self, *, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM task_outcomes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def get_provider_outcome_stats(
        self,
        *,
        domain: str | None = None,
        request_kind: str | None = None,
        limit: int = 50,
    ) -> dict[str, dict[str, Any]]:
        query = "SELECT payload_json FROM task_outcomes"
        clauses: list[str] = []
        params: list[Any] = []
        if domain:
            clauses.append("domain = ?")
            params.append(domain)
        if request_kind:
            clauses.append("request_kind = ?")
            params.append(request_kind)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        stats: dict[str, dict[str, Any]] = {}
        for row in rows:
            payload = json.loads(row["payload_json"])
            provider = str(payload.get("provider", "")).strip()
            if not provider:
                continue
            provider_stats = stats.setdefault(
                provider,
                {
                    "total": 0,
                    "success": 0,
                    "failure": 0,
                    "timeout": 0,
                    "latency_sum": 0.0,
                    "latency_count": 0,
                    "models": {},
                },
            )
            provider_stats["total"] += 1
            error_text = str(payload.get("error_text", "") or "").lower()
            if str(payload.get("outcome", "")).strip() in {"ok", "ok_voice", "degraded"}:
                provider_stats["success"] += 1
            else:
                provider_stats["failure"] += 1
            if "timeout" in error_text or "timed out" in error_text or "fuera de sla" in error_text:
                provider_stats["timeout"] += 1
            latency = payload.get("latency_ms")
            if latency is not None:
                provider_stats["latency_sum"] += float(latency)
                provider_stats["latency_count"] += 1
            nested_payload = payload.get("payload") or {}
            model = str(nested_payload.get("model", "") or "").strip()
            if model:
                model_stats = provider_stats["models"].setdefault(model, {"total": 0, "success": 0, "failure": 0, "timeout": 0})
                model_stats["total"] += 1
                if str(payload.get("outcome", "")).strip() in {"ok", "ok_voice", "degraded"}:
                    model_stats["success"] += 1
                else:
                    model_stats["failure"] += 1
                if "timeout" in error_text or "timed out" in error_text or "fuera de sla" in error_text:
                    model_stats["timeout"] += 1
        for provider_stats in stats.values():
            count = int(provider_stats.get("latency_count", 0))
            provider_stats["average_latency_ms"] = (provider_stats["latency_sum"] / count) if count else None
            provider_stats["success_rate"] = (provider_stats["success"] / provider_stats["total"]) if provider_stats["total"] else 0.0
            provider_stats["failure_rate"] = (provider_stats["failure"] / provider_stats["total"]) if provider_stats["total"] else 0.0
            provider_stats["timeout_rate"] = (provider_stats["timeout"] / provider_stats["total"]) if provider_stats["total"] else 0.0
        return stats

    def audit_summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            approvals = conn.execute("SELECT COUNT(*) FROM approvals WHERE status = 'pending'").fetchone()[0]
            evidence = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
            academic_packets = conn.execute("SELECT COUNT(*) FROM academic_packets").fetchone()[0]
            cached_contexts = conn.execute("SELECT COUNT(*) FROM context_cache").fetchone()[0]
            runtime_probes = conn.execute("SELECT COUNT(*) FROM runtime_probes").fetchone()[0]
            benchmark_runs = conn.execute("SELECT COUNT(*) FROM benchmark_runs").fetchone()[0]
            request_traces = conn.execute("SELECT COUNT(*) FROM request_traces").fetchone()[0]
            sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            session_messages = conn.execute("SELECT COUNT(*) FROM session_messages").fetchone()[0]
            provider_probes = conn.execute("SELECT COUNT(*) FROM provider_probes").fetchone()[0]
            quality_eval_results = conn.execute("SELECT COUNT(*) FROM quality_eval_results").fetchone()[0]
            node_benchmark_reports = conn.execute("SELECT COUNT(*) FROM node_benchmark_reports").fetchone()[0]
            secret_resolutions = conn.execute("SELECT COUNT(*) FROM secret_resolutions").fetchone()[0]
            billing_records = conn.execute("SELECT COUNT(*) FROM billing_records").fetchone()[0]
            budget_snapshots = conn.execute("SELECT COUNT(*) FROM budget_snapshots").fetchone()[0]
            telegram_events = conn.execute("SELECT COUNT(*) FROM telegram_events").fetchone()[0]
            telegram_voice_events = conn.execute("SELECT COUNT(*) FROM telegram_voice_events").fetchone()[0]
        return {
            "tasks": tasks,
            "pending_approvals": approvals,
            "evidence_records": evidence,
            "academic_packets": academic_packets,
            "cached_contexts": cached_contexts,
            "runtime_probes": runtime_probes,
            "benchmark_runs": benchmark_runs,
            "request_traces": request_traces,
            "sessions": sessions,
            "session_messages": session_messages,
            "provider_probes": provider_probes,
            "quality_eval_results": quality_eval_results,
            "node_benchmark_reports": node_benchmark_reports,
            "secret_resolutions": secret_resolutions,
            "billing_records": billing_records,
            "budget_snapshots": budget_snapshots,
            "telegram_events": telegram_events,
            "telegram_voice_events": telegram_voice_events,
            "db_path": str(self.db_path),
        }
