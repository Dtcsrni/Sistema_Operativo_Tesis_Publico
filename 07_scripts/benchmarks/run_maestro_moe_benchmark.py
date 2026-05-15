from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "runtime" / "openclaw"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_science import (  # noqa: E402
    append_hashed_record,
    build_run_header,
    build_sample_record,
    promptset_hash,
    run_log_path,
    sha256_payload,
    utc_now,
    write_summary,
)
from openclaw_local.contracts import BenchmarkRecord  # noqa: E402
from openclaw_local.maestro_router import REALTIME_BLOCKED_MODELS, build_maestro_route_decision  # noqa: E402
from openclaw_local.storage import OpenClawStore  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROFILE_ID = "maestro_moe_benchmark"
REPORT_PATH = ROOT / "runtime" / "pc_control" / "benchmarks" / "reports" / "maestro_moe_latest.json"

CASES = [
    {
        "id": "spanish_fast_chat",
        "command": "chat",
        "text": "hola, dame una respuesta breve",
        "expected_intent": "chat_fast",
    },
    {
        "id": "spanish_coding_debug",
        "command": "chat",
        "text": "Tengo un traceback de Python y necesito depurar un error en JSONL con hashes encadenados",
        "expected_intent": "coding",
    },
    {
        "id": "edge_ops_status",
        "command": "chat",
        "text": "revisa el estado del edge, servicios, modelos y telemetría de la Orange Pi",
        "expected_intent": "ops",
    },
    {
        "id": "research_synthesis",
        "command": "chat",
        "text": "Analiza la evidencia de benchmarks y sintetiza implicaciones para la tesis con trazabilidad",
        "expected_intent": "research_synthesis",
    },
    {
        "id": "mutating_guard",
        "command": "chat",
        "text": "reinicia el servicio openclaw-telegram-bot y modifica la configuración",
        "expected_intent": "ops",
        "expected_risk": "high",
    },
    {
        "id": "npu_blocked",
        "command": "chat",
        "text": "usa la NPU del edge para una síntesis pesada si está disponible",
        "expected_intent": "ops",
        "expect_no_npu": True,
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Bateria Maestro MoE sobre ruteo OpenClaw integrado.")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--step-id", default="VAL-STEP-PENDING")
    parser.add_argument("--session-id", default="BENCH-MAESTRO-SESSION")
    args = parser.parse_args()

    promptset = [{"id": case["id"], "prompt": case["text"]} for case in CASES]
    header = build_run_header(
        profile_id=PROFILE_ID,
        node="pc_control",
        runtime="maestro_router",
        model="maestro-router-integrated",
        step_id=args.step_id,
        command="python3 07_scripts/benchmarks/run_maestro_moe_benchmark.py",
        promptset=promptset,
        mode="real",
        repo_root=ROOT,
    )
    log_path = run_log_path(node="pc_control", run_id=header["run_id"])
    append_hashed_record(log_path, header)
    store = OpenClawStore(ROOT / "runtime" / "openclaw" / "state" / "openclaw.db")
    samples: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    print(json.dumps({"event": "maestro_moe_start", "run_id": header["run_id"], "cases": len(CASES)}, ensure_ascii=False), flush=True)
    sample_index = 0
    for iteration in range(args.iterations):
        for case in CASES:
            sample_index += 1
            started = time.perf_counter()
            decision = build_maestro_route_decision(
                repo_root=ROOT,
                session_id=args.session_id,
                channel="telegram",
                peer_id="benchmark",
                command=str(case["command"]),
                text=str(case["text"]),
                store=store,
            )
            store.save_maestro_route_decision(decision)
            latency_ms = (time.perf_counter() - started) * 1000.0
            status, error = _evaluate_case(case, decision.to_dict())
            if status != "ok":
                failures.append({"case": case["id"], "error": error, "decision": decision.to_dict()})
            sample = build_sample_record(
                run_id=header["run_id"],
                step_id=args.step_id,
                sample_index=sample_index,
                phase="measurement",
                category=str(case["id"]),
                prompt_hash=promptset_hash([{"case": case["id"], "text": case["text"]}]),
                latency_ms=latency_ms,
                ttft_ms=latency_ms,
                tokens_per_second=None,
                status=status,
                stdout=json.dumps(decision.to_dict(), ensure_ascii=False),
                stderr=error,
                exit_status=0 if status == "ok" else 1,
                metadata={"iteration": iteration + 1, "expected_intent": case["expected_intent"]},
            )
            append_hashed_record(log_path, sample)
            samples.append(sample)
            print(json.dumps({"event": "maestro_case", "case": case["id"], "status": status, "intent": decision.intent, "model": decision.selected_model}, ensure_ascii=False), flush=True)

    status = "ok" if not failures else "partial_failure"
    summary = write_summary(
        path=log_path,
        header=header,
        samples=samples,
        status=status,
        extra={
            "cases": [case["id"] for case in CASES],
            "failures": failures,
            "realtime_blocked_models": sorted(REALTIME_BLOCKED_MODELS),
            "primary_jsonl": str(log_path.relative_to(ROOT)),
        },
    )
    report = {
        "schema_version": "siot-maestro-moe-report-v1",
        "generated_at": utc_now(),
        "header": header,
        "summary": summary,
        "primary_jsonl": str(log_path.relative_to(ROOT)),
        "cases": CASES,
        "failures": failures,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    store.save_benchmark_record(
        BenchmarkRecord(
            benchmark_id=header["run_id"],
            run_id=header["run_id"],
            provider="maestro_router",
            model="maestro-router-integrated",
            status=status,
            latency_ms=summary.get("statistics", {}).get("mean_latency_ms"),
            payload_hash=sha256_payload(report),
            primary_jsonl=str(log_path.relative_to(ROOT)),
            scientific_validity=str(summary.get("scientific_validity", "")),
            details={"report": str(REPORT_PATH.relative_to(ROOT)), "primary_jsonl": str(log_path.relative_to(ROOT)), "failures": failures},
            created_at=utc_now(),
        )
    )
    print(json.dumps({"event": "maestro_moe_complete", "status": status, "report": str(REPORT_PATH), "jsonl": str(log_path)}, ensure_ascii=False, indent=2), flush=True)
    return 0 if status == "ok" else 1


def _evaluate_case(case: dict[str, Any], decision: dict[str, Any]) -> tuple[str, str]:
    if decision.get("intent") != case.get("expected_intent"):
        return "failed", f"intent {decision.get('intent')} != {case.get('expected_intent')}"
    if case.get("expected_risk") and decision.get("risk_level") != case.get("expected_risk"):
        return "failed", f"risk {decision.get('risk_level')} != {case.get('expected_risk')}"
    if decision.get("selected_model") in REALTIME_BLOCKED_MODELS:
        return "failed", f"blocked realtime model selected: {decision.get('selected_model')}"
    if case.get("expect_no_npu") and any(str(item).startswith("rknn_llm_experimental:") for item in decision.get("fallback_chain", [])):
        return "failed", "npu was present in fallback chain without valid edge benchmark"
    if not decision.get("evidence_refs"):
        return "failed", "missing evidence_refs"
    return "ok", ""


if __name__ == "__main__":
    raise SystemExit(main())
