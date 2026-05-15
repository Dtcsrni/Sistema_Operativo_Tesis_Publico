from __future__ import annotations
from datetime import UTC, datetime
from typing import Any
import os
from pathlib import Path

from ..adaptive_router import build_adaptive_routing_snapshot
from ..contracts import SessionEnvelope
from ..session_layer import build_nodes_summary, build_provider_summary, process_channel_text
from ..orchestrator import Orchestrator
from ..channels import WebChannel
from ..sources import source_policy_snapshot
from ..runtime_status import summarize_host, probe_runtime_status

EDGE_AGENT_IDS = {"ollama_local", "rknn_llm_experimental"}


def _edge_agents_exposed() -> bool:
    return os.getenv("OPENCLAW_EXPOSE_EDGE_AGENTS", "0").strip().lower() in {"1", "true", "yes", "on", "si", "sí"}

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

    def list_approvals(self, status: str | None = "pending") -> list[dict[str, Any]]:
        if hasattr(self.store, "list_approvals"):
            return self.store.list_approvals(status=status)
        return self.store.list_pending_approvals()

    def clear_pending_approvals(self, status: str = "rejected") -> int:
        if hasattr(self.store, "clear_pending_approvals"):
            return int(self.store.clear_pending_approvals(status=status))
        count = 0
        for item in self.store.list_pending_approvals():
            self.store.mark_approval(item["approval_id"], status)
            count += 1
        return count

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

    def create_session(self, channel: str, peer: str | None = None) -> dict[str, Any]:
        peer_id = (peer or channel or "web").strip() or "web"
        existing = self.store.get_session(peer_id)
        if existing is not None:
            return existing

        now = datetime.now(UTC).isoformat()
        session = SessionEnvelope(
            session_id=peer_id,
            channel=channel,
            peer_id=peer_id,
            operator_identity=peer_id,
            target_node=os.getenv("OPENCLAW_DEFAULT_TARGET_NODE", "auto").strip() or "auto",
            provider_policy=os.getenv("OPENCLAW_PROVIDER_POLICY", "hybrid_controlled").strip() or "hybrid_controlled",
            premium_auto=os.getenv("OPENCLAW_PREMIUM_AUTO", "0").strip().lower() in {"1", "true", "yes", "on", "si", "sí"},
            status="active",
            title=f"{channel}:{peer_id}"[:120],
            task_profile="interactive",
            payload={"created_from": "gateway_websocket"},
            created_at=now,
            updated_at=now,
        )
        self.store.save_session(session)
        return session.to_dict()

    def list_session_messages(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        session = self.store.get_session(session_id)
        resolved_session_id = session_id
        if session is None:
            cached = self.store.get_cached_context(f"session:active:web:{session_id}") or {}
            cached_session_id = str(cached.get("session_id", "") or "")
            if cached_session_id:
                resolved_session_id = cached_session_id
        return self.store.list_session_messages(resolved_session_id, limit=limit)

    def send_session_message(
        self,
        session_key: str,
        text: str,
        operator_identity: str = "web",
        *,
        channel: str = "web",
        execution_profile: str = "",
        progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        profile = execution_profile.strip()
        route_channel = channel.strip() or "web"
        
        orchestrator = Orchestrator(self.repo_root, self.store)
        web_channel = WebChannel(session_key, callback=progress_callback)

        return process_channel_text(
            store=self.store,
            repo_root=self.repo_root,
            channel=route_channel,
            peer_id=session_key,
            text=text,
            dispatcher=lambda command, argument, **kwargs: orchestrator.dispatch_command(
                command=command,
                argument=argument,
                channel=web_channel,
                chat_id=session_key,
                operator_identity=profile or operator_identity,
                **kwargs
            ),
            operator_identity=operator_identity,
            progress_callback=progress_callback,
        )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        session = self.store.get_session(session_id)
        if session is None:
            return None
        session["messages"] = self.store.list_session_messages(session_id, limit=100)
        return session

    def list_agents(self) -> list[dict[str, Any]]:
        executable_session_modes = {
            "local_runtime",
            "desktop_local_runtime",
            "desktop_native_runtime",
        }
        expose_edge = _edge_agents_exposed()
        return [
            {
                "id": item.get("id", ""),
                "name": item.get("id", ""),
                "label": item.get("id", ""),
                "model": item.get("model_class", ""),
                "channel": item.get("mode", ""),
                "status": "active",
            }
            for item in build_provider_summary(self.repo_root)
            if item.get("session_mode") in executable_session_modes
            and (expose_edge or item.get("id") not in EDGE_AGENT_IDS)
        ]

    def list_models(self) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        seen: set[str] = set()
        primary = os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", "").strip() or os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "").strip() or os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "").strip() or "deepseek-r1:7b"
        candidates = [
            (primary, "openclaw", True),
            (os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", "").strip(), "desktop", True),
        ]
        if _edge_agents_exposed():
            candidates.append((os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "").strip(), "edge", False))
        for model_id, provider, reasoning in candidates:
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            models.append(
                {
                    "id": model_id,
                    "name": model_id,
                    "provider": provider,
                    "contextWindow": 8192,
                    "reasoning": reasoning,
                }
            )
        return models

    def get_config_snapshot(self) -> dict[str, Any]:
        return {
            "agents": {
                "defaults": {
                    "model": {
                        "primary": os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", "").strip() or os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "").strip() or "qwen3:4b",
                    },
                },
            },
        }

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        return self.store.get_request_trace(trace_id)

    def list_sources(self, limit: int = 50) -> dict[str, Any]:
        return source_policy_snapshot(self.repo_root, store=self.store, limit=limit)

    def process_session_message(self, session_id: str, text: str, operator_identity: str = "web", progress_callback: Any | None = None) -> dict[str, Any]:
        peer_id = session_id or "web"
        orchestrator = Orchestrator(self.repo_root, self.store)
        web_channel = WebChannel(peer_id, callback=progress_callback)
        
        return process_channel_text(
            store=self.store,
            repo_root=self.repo_root,
            channel="web",
            peer_id=peer_id,
            text=text,
            dispatcher=lambda command, argument, **kwargs: orchestrator.dispatch_command(
                command=command,
                argument=argument,
                channel=web_channel,
                chat_id=peer_id,
                operator_identity=operator_identity,
                **kwargs
            ),
            operator_identity=operator_identity,
            progress_callback=progress_callback,
        )

    def approve_task(self, task_id: str, status: str) -> bool:
        approval = self.store.get_latest_approval_for_task(task_id)
        if not approval:
            return False
        return bool(self.store.mark_approval(approval["approval_id"], status))

    def mark_approval(self, approval_id: str, status: str) -> bool:
        if hasattr(self.store, "get_approval") and not self.store.get_approval(approval_id):
            return False
        return bool(self.store.mark_approval(approval_id, status))
