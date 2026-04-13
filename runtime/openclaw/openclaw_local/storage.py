from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import AcademicWorkPacket, BenchmarkRecord, BillingRecord, BudgetSnapshot, EvidenceRecord, ProviderDecision, RuntimeProbe, SecretResolution, TaskEnvelope


class OpenClawStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

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

    def audit_summary(self) -> dict[str, Any]:
        with self._connect() as conn:
            tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            approvals = conn.execute("SELECT COUNT(*) FROM approvals WHERE status = 'pending'").fetchone()[0]
            evidence = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
            academic_packets = conn.execute("SELECT COUNT(*) FROM academic_packets").fetchone()[0]
            cached_contexts = conn.execute("SELECT COUNT(*) FROM context_cache").fetchone()[0]
            runtime_probes = conn.execute("SELECT COUNT(*) FROM runtime_probes").fetchone()[0]
            benchmark_runs = conn.execute("SELECT COUNT(*) FROM benchmark_runs").fetchone()[0]
            secret_resolutions = conn.execute("SELECT COUNT(*) FROM secret_resolutions").fetchone()[0]
            billing_records = conn.execute("SELECT COUNT(*) FROM billing_records").fetchone()[0]
            budget_snapshots = conn.execute("SELECT COUNT(*) FROM budget_snapshots").fetchone()[0]
        return {
            "tasks": tasks,
            "pending_approvals": approvals,
            "evidence_records": evidence,
            "academic_packets": academic_packets,
            "cached_contexts": cached_contexts,
            "runtime_probes": runtime_probes,
            "benchmark_runs": benchmark_runs,
            "secret_resolutions": secret_resolutions,
            "billing_records": billing_records,
            "budget_snapshots": budget_snapshots,
            "db_path": str(self.db_path),
        }
