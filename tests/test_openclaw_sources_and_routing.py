from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "runtime" / "openclaw"

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from openclaw_local.adaptive_router import build_adaptive_routing_snapshot, order_provider_candidates  # noqa: E402
from openclaw_local.contracts import TaskEnvelope  # noqa: E402
from openclaw_local.sources import append_reference_jsonl, ingest_reference, render_apa_reference  # noqa: E402
from openclaw_local.storage import OpenClawStore  # noqa: E402


def test_reference_ingest_jsonl_and_sqlite_without_online_verification(tmp_path: Path) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")
    record = ingest_reference(
        repo_root=ROOT,
        source_type="article",
        title="Edge intelligence for IoT systems",
        authors=["Jane Doe", "John Smith"],
        year="2026",
        doi="https://doi.org/10.1234/example.2026",
        tags=["iot", "edge"],
        verify_online=False,
    )
    jsonl = tmp_path / "references.jsonl"
    append_reference_jsonl(record, jsonl)
    store.save_reference_record(record)

    saved = store.list_reference_records(limit=5)
    line = json.loads(jsonl.read_text(encoding="utf-8").strip())
    assert record.doi == "10.1234/example.2026"
    assert record.verification_status == "no_verificada"
    assert "https://doi.org/10.1234/example.2026" in record.apa_reference
    assert saved[0]["reference_id"] == record.reference_id
    assert line["source_hash"] == record.source_hash


def test_render_apa_reference_has_core_apa7_shape() -> None:
    rendered = render_apa_reference(
        authors=["Jane Doe", "John Smith"],
        year="2026",
        title="Traceable IoT experimentation",
        source_type="article",
        container_title="Journal of Edge Systems",
        publisher="",
        doi="10.5555/trace.2026",
        url="",
    )
    assert rendered.startswith("Doe, J., & Smith, J. (2026).")
    assert "Journal of Edge Systems." in rendered
    assert rendered.endswith("https://doi.org/10.5555/trace.2026")


def test_adaptive_snapshot_blocks_npu_until_valid_edge_benchmark() -> None:
    snapshot = build_adaptive_routing_snapshot(ROOT)
    assert snapshot.pc_primary_model == "mistral-nemo:12b"
    assert snapshot.pc_scientific_validity == "valid_scientific_evidence"
    assert snapshot.edge_scientific_validity == "invalid_for_scientific_claim"
    assert snapshot.npu_promoted is False
    assert "edge_npu_blocked_until_valid_benchmark" in snapshot.warnings


def test_adaptive_order_preserves_existing_feedback_priority(tmp_path: Path) -> None:
    class StoreWithFeedback:
        def get_provider_outcome_stats(self, **_: object) -> dict[str, dict[str, float]]:
            return {"ollama_local": {"total": 5, "success_rate": 1.0}}

    task = TaskEnvelope(
        task_id="TASK-ROUTER-001",
        title="Sintesis",
        domain="academico",
        objective="Sintetizar fuentes",
        complexity="high",
        requires_citations=True,
    )
    ordered = order_provider_candidates(
        ["ollama_local", "pc_native_llamacpp", "rknn_llm_experimental"],
        task,
        repo_root=ROOT,
        store=StoreWithFeedback(),
    )
    assert ordered[0] == "ollama_local"
    assert "rknn_llm_experimental" in ordered


def test_adaptive_order_filters_npu_without_explicit_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_ADAPTIVE_ROUTING_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_DESKTOP_RUNTIME", "llamacpp")
    task = TaskEnvelope(
        task_id="TASK-ROUTER-002",
        title="Sintesis",
        domain="academico",
        objective="Sintetizar fuentes",
        complexity="high",
        requires_citations=True,
    )
    ordered = order_provider_candidates(
        ["ollama_local", "pc_native_llamacpp", "rknn_llm_experimental"],
        task,
        repo_root=ROOT,
        store=None,
    )
    assert ordered[0] == "pc_native_llamacpp"
    assert "rknn_llm_experimental" not in ordered
