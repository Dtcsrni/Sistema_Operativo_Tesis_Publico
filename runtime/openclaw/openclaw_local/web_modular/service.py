from __future__ import annotations
from typing import Any
from pathlib import Path

from ..runtime_status import summarize_host, probe_runtime_status
from ..adaptive_router import build_adaptive_routing_snapshot
from ..session_layer import build_nodes_summary, build_provider_summary, process_channel_text
from ..sources import source_policy_snapshot

class WebService:
    def __init__(self, store: Any, repo_root: Path):
        self.store = store
        self.repo_root = repo_root

    def get_dashboard_data(self) -> dict[str, Any]:
        return {
            "tasks": self.store.audit_summary().get("tasks", 0),
            "pending_approvals": self.store.audit_summary().get("pending_approvals", 0),
            "evidence_records": self.store.audit_summary().get("evidence_records", 0),
            "academic_packets": self.store.audit_summary().get("academic_packets", 0),
            "source_records": self.store.audit_summary().get("source_records", 0),
        }

    def get_runtime_status(self) -> dict[str, Any]:
        return probe_runtime_status(self.repo_root)

    def get_host_info(self) -> dict[str, Any]:
        return summarize_host(self.repo_root)

    def list_approvals(self) -> list[dict[str, Any]]:
        return self.store.list_pending_approvals()

    def list_nodes(self) -> list[dict[str, Any]]:
        return build_nodes_summary(self.repo_root)

    def list_providers(self) -> list[dict[str, Any]]:
        providers = build_provider_summary(self.repo_root)
        snapshot = build_adaptive_routing_snapshot(self.repo_root, store=self.store).to_dict()
        return [{**item, "adaptive_snapshot_id": snapshot["snapshot_id"]} for item in providers]

    def adaptive_routing(self) -> dict[str, Any]:
        return build_adaptive_routing_snapshot(self.repo_root, store=self.store).to_dict()

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.list_sessions(limit=limit)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.store.get_session(session_id)
        if session is None:
            return None
        session["messages"] = self.store.list_session_messages(session_id, limit=100)
        return session

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        return self.store.get_request_trace(trace_id)

    def list_sources(self, limit: int = 50) -> dict[str, Any]:
        return source_policy_snapshot(self.repo_root, store=self.store, limit=limit)

    def process_session_message(self, session_id: str, text: str, operator_identity: str = "web") -> dict[str, Any]:
        from ..telegram_bot import dispatch_command

        peer_id = session_id or "web"
        return process_channel_text(
            store=self.store,
            repo_root=self.repo_root,
            channel="web",
            peer_id=peer_id,
            text=text,
            dispatcher=lambda command, argument: dispatch_command(command, argument, repo_root=self.repo_root, store=self.store, chat_id=peer_id),
            operator_identity=operator_identity,
        )

    def approve_task(self, task_id: str, status: str) -> bool:
        approval = self.store.get_latest_approval_for_task(task_id)
        if not approval:
            return False
        self.store.mark_approval(approval["approval_id"], status)
        return True
