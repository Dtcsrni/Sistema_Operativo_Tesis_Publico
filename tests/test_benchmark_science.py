from __future__ import annotations

import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "07_scripts"))
sys.path.insert(0, str(ROOT / "runtime" / "openclaw"))

from benchmark_science import (  # noqa: E402
    append_hashed_record,
    build_run_header,
    build_sample_record,
    promptset_hash,
    summarize_samples,
    validate_jsonl_artifact,
    write_summary,
)
from openclaw_local.contracts import BenchmarkRecord  # noqa: E402
from openclaw_local.storage import OpenClawStore  # noqa: E402


def test_benchmark_jsonl_hash_chain_and_summary(tmp_path: Path) -> None:
    promptset = [{"category": "decision", "prompt": "test"}]
    header = build_run_header(
        profile_id="pc_mistral_nemo_12b_extensive",
        node="pc_control",
        runtime="ollama_local",
        model="mistral-nemo:12b",
        step_id="VAL-STEP-TEST",
        command="pytest",
        promptset=promptset,
        mode="real",
        repo_root=ROOT,
    )
    path = tmp_path / "run.jsonl"
    first = append_hashed_record(path, header)
    sample = append_hashed_record(
        path,
        build_sample_record(
            run_id=header["run_id"],
            step_id="VAL-STEP-TEST",
            sample_index=1,
            phase="measurement",
            category="decision",
            prompt_hash=promptset_hash(promptset),
            latency_ms=100.0,
            ttft_ms=20.0,
            tokens_per_second=15.0,
            status="ok",
        ),
    )
    summary = write_summary(
        path=path,
        header=header,
        samples=[{"latency_ms": 100.0, "tokens_per_second": 15.0}],
        status="ok",
    )

    assert first["previous_record_hash"] == ""
    assert sample["previous_record_hash"] == first["record_hash"]
    assert summary["previous_record_hash"] == sample["record_hash"]
    assert summary["scientific_validity"] == "valid_scientific_evidence"
    assert validate_jsonl_artifact(path)["status"] == "ok"


def test_non_real_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="Only 'real' is allowed"):
        build_run_header(
            profile_id="pc_mistral_nemo_12b_extensive",
            node="pc_control",
            runtime="ollama_local",
            model="mistral-nemo:12b",
            step_id="VAL-STEP-TEST",
            command="pytest",
            promptset=[{"prompt": "test"}],
            mode="simulation_only",
            repo_root=ROOT,
        )


def test_statistics_include_percentiles_and_margin_error() -> None:
    stats = summarize_samples(
        [
            {"latency_ms": 100.0, "tokens_per_second": 10.0},
            {"latency_ms": 110.0, "tokens_per_second": 12.0},
            {"latency_ms": 90.0, "tokens_per_second": 8.0},
            {"latency_ms": 105.0, "tokens_per_second": 11.0},
            {"latency_ms": 95.0, "tokens_per_second": 9.0},
        ]
    )

    assert stats["sample_size"] == 5
    assert stats["mean_latency_ms"] == 100.0
    assert stats["p95_latency_ms"] == 110.0
    assert stats["mean_tokens_per_second"] == 10.0
    assert stats["margin_error_95_ms"] > 0


def test_openclaw_benchmark_record_persists_scientific_fields(tmp_path: Path) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")
    record = BenchmarkRecord(
        benchmark_id="BEN-TEST",
        run_id="RUN-TEST",
        provider="desktop_compute",
        model="mistral-nemo:12b",
        status="ok",
        latency_ms=123.4,
        payload_hash="abc",
        primary_jsonl="runtime/pc_control/benchmarks/runs/RUN-TEST.jsonl",
        scientific_validity="valid_scientific_evidence",
        details={"primary_jsonl": "runtime/pc_control/benchmarks/runs/RUN-TEST.jsonl"},
        created_at="2026-04-28T00:00:00+00:00",
    )
    store.save_benchmark_record(record)

    saved = store.list_benchmark_runs(limit=1)[0]

    assert saved["run_id"] == "RUN-TEST"
    assert saved["model"] == "mistral-nemo:12b"
    assert saved["payload_hash"] == "abc"
    assert saved["scientific_validity"] == "valid_scientific_evidence"
