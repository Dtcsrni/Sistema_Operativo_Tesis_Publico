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
from openclaw_local.maestro_router import build_maestro_route_decision, maestro_message_hash, maestro_profile_from_decision  # noqa: E402
from openclaw_local.toltecayotl_ingestor import ingest_document, split_text  # noqa: E402
from openclaw_local.knowledge_sync import export_sync_package, import_sync_package  # noqa: E402
from openclaw_local.contracts import TaskEnvelope  # noqa: E402
from openclaw_local.sources import append_reference_jsonl, ingest_reference, render_apa_reference  # noqa: E402
from openclaw_local.storage import OpenClawStore  # noqa: E402
from openclaw_local.session_layer import process_channel_text  # noqa: E402


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
            return {"edge_inference": {"total": 5, "success_rate": 1.0}}

    task = TaskEnvelope(
        task_id="TASK-ROUTER-001",
        title="Sintesis",
        domain="academico",
        objective="Sintetizar fuentes",
        complexity="high",
        requires_citations=True,
    )
    ordered = order_provider_candidates(
        ["edge_inference", "llamacpp_local", "rknn_llm_experimental"],
        task,
        repo_root=ROOT,
        store=StoreWithFeedback(),
    )
    assert ordered[0] == "edge_inference"
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
        ["edge_inference", "llamacpp_local", "rknn_llm_experimental"],
        task,
        repo_root=ROOT,
        store=None,
    )
    assert ordered[0] == "llamacpp_local"
    assert "rknn_llm_experimental" not in ordered


def test_maestro_route_uses_benchmarks_and_blocks_edge_npu() -> None:
    decision = build_maestro_route_decision(
        repo_root=ROOT,
        session_id="SES-TEST",
        channel="telegram",
        peer_id="chat",
        command="chat",
        text="Analiza benchmarks y sintetiza evidencia para la tesis con trazabilidad",
    )
    payload = decision.to_dict()
    assert payload["intent"] == "research_synthesis"
    assert payload["selected_model"] in {"mistral-nemo:12b", "hermes3:8b", "qwen3:4b"}
    assert payload["selected_model"] not in {"qwen3:14b", "phi4:14b", "qwen2.5-coder:14b"}
    assert payload["telemetry_required"] is True
    assert not any(item.startswith("rknn_llm_experimental:") for item in payload["fallback_chain"])
    assert any(str(item).replace("\\", "/") == "runtime/edge_iot/benchmarks/index.json" for item in payload["evidence_refs"])


def test_maestro_route_prefers_hermes_for_coding_realtime() -> None:
    decision = build_maestro_route_decision(
        repo_root=ROOT,
        session_id="SES-TEST",
        channel="telegram",
        peer_id="chat",
        command="chat",
        text="Necesito depurar un traceback de Python y validar un JSONL con hashes encadenados",
    )
    assert decision.intent == "coding"
    assert decision.selected_model == "hermes3:8b"
    assert "qwen2.5-coder:14b" not in ",".join(decision.fallback_chain)


def test_maestro_route_persists_and_feeds_telegram_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_MAESTRO_ENABLED", "1")
    store = OpenClawStore(tmp_path / "openclaw.db")
    text = "Necesito depurar un error de Python en el benchmark"
    result = process_channel_text(
        store=store,
        repo_root=ROOT,
        channel="telegram",
        peer_id="123",
        text=text,
        dispatcher=lambda command, argument: {"status": "ok", "text": f"{command}:{argument}", "model": "test"},
        operator_identity="telegram:123",
    )
    decisions = store.list_maestro_route_decisions(limit=1)
    assert decisions[0]["intent"] == "coding"
    assert result["response"]["maestro_route"]["route_id"] == decisions[0]["route_id"]
    cached = store.get_cached_context(f"telegram:maestro_route:123:{maestro_message_hash(text)}")
    profile = maestro_profile_from_decision(cached["decision"])
    assert profile["semantic_status"] == "maestro_router"
    assert profile["request_kind"] == "coding"


def test_toltecayotl_ingestor_chunks_markdown_with_hashes(tmp_path: Path) -> None:
    source = tmp_path / "paper.md"
    source.write_text("# Paper\n\nToltecayotl integra evidencia academica y telemetria IoT trazable.", encoding="utf-8")

    chunks = ingest_document(repo_root=ROOT, source_path=str(source), source_type="markdown", chunk_chars=240)

    assert len(chunks) == 1
    assert chunks[0].source_hash
    assert chunks[0].chunk_hash
    assert chunks[0].verification_status == "hash_verificado"
    assert "Toltecayotl integra evidencia" in chunks[0].text


def test_toltecayotl_split_text_preserves_minimum_chunks() -> None:
    chunks = split_text("uno. " * 200, chunk_chars=80)
    assert len(chunks) >= 2
    assert all(chunk.strip() for chunk in chunks)


def test_toltecayotl_sync_export_import_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sync_dir = tmp_path / "sync"
    monkeypatch.setenv("TOLTECAYOTL_SYNC_DIR", str(sync_dir))
    source = tmp_path / "note.md"
    source.write_text("Conocimiento Toltecayotl sincronizable con hash.", encoding="utf-8")
    chunks = [chunk.to_dict() for chunk in ingest_document(repo_root=ROOT, source_path=str(source), source_type="markdown")]

    (sync_dir).mkdir(parents=True)
    jsonl = sync_dir / "chunks.jsonl"
    jsonl.write_text("\n".join(json.dumps(chunk, ensure_ascii=False, sort_keys=True) for chunk in chunks) + "\n", encoding="utf-8")
    package = export_sync_package(ROOT)
    jsonl.unlink()
    result = import_sync_package(ROOT, sync_dir / f"{package.package_id}.json")

    assert result["status"] == "ok"
    assert result["imported"] == 1
    assert jsonl.exists()
