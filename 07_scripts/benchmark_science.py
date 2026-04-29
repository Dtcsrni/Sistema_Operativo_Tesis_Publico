from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "siot-benchmark-run-v1"
DEFAULT_PROTOCOL = "PEV-02"
PRIMARY_PC_MODEL = "mistral-nemo:12b"
PC_BENCHMARK_DIR = ROOT / "runtime" / "pc_control" / "benchmarks"
EDGE_BENCHMARK_DIR = ROOT / "runtime" / "edge_iot" / "benchmarks"

METHODOLOGY_REFERENCES = [
    {
        "id": "mlperf_inference",
        "name": "MLCommons MLPerf Inference",
        "url": "https://mlcommons.org/working-groups/benchmarks/inference/",
        "use": "Disciplina de escenarios, reproducibilidad y reporte de rendimiento; no implica certificacion oficial.",
    },
    {
        "id": "lm_evaluation_harness",
        "name": "EleutherAI lm-evaluation-harness",
        "url": "https://github.com/EleutherAI/lm-evaluation-harness",
        "use": "Compatibilidad con evaluacion estandarizada de LLMs cuando dependencias y datasets esten disponibles.",
    },
    {
        "id": "helm",
        "name": "Stanford CRFM HELM",
        "url": "https://crfm-helm.readthedocs.io/",
        "use": "Reporte holistico, transparente y reproducible de prompts, salidas y metricas.",
    },
]

BENCHMARK_PROFILES = {
    "pc_mistral_nemo_12b_extensive": {
        "node": "pc_control",
        "runtime": "ollama_local",
        "model": PRIMARY_PC_MODEL,
        "warmup_iterations": 5,
        "measurement_iterations": 50,
        "interval_ms": 500,
        "valid_for_scientific_claim": True,
    },
    "pc_model_comparison": {
        "node": "pc_control",
        "runtime": "ollama_local",
        "model": PRIMARY_PC_MODEL,
        "comparison_models": ["qwen2.5-coder:14b", "qwen3:14b", "phi4:14b"],
        "warmup_iterations": 2,
        "measurement_iterations": 10,
        "interval_ms": 500,
        "valid_for_scientific_claim": True,
    },
    "edge_npu": {
        "node": "edge_iot",
        "runtime": "rknn_llm_experimental",
        "model": "rkllm_preconverted",
        "warmup_iterations": 5,
        "measurement_iterations": 50,
        "interval_ms": 500,
        "valid_for_scientific_claim": True,
    },
    "lm_eval": {
        "node": "pc_control",
        "runtime": "lm-evaluation-harness",
        "model": PRIMARY_PC_MODEL,
        "tasks": ["mmlu", "hellaswag"],
        "status_if_missing": "blocked_missing_dependency",
        "valid_for_scientific_claim": False,
    },
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_payload(payload: Any) -> str:
    return sha256_text(canonical_json(payload))


def git_commit(repo_root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def host_fingerprint(repo_root: Path = ROOT) -> dict[str, Any]:
    disk = shutil.disk_usage(repo_root)
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count() or 1,
        "memory_total_bytes": _memory_total_bytes(),
        "disk": {
            "path": str(repo_root),
            "total_bytes": disk.total,
            "free_bytes": disk.free,
        },
        "gpu": gpu_snapshot(),
    }


def gpu_snapshot() -> dict[str, Any] | None:
    cmd = shutil.which("nvidia-smi")
    if not cmd:
        return None
    completed = subprocess.run(
        [
            cmd,
            "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,driver_version",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {"status": "failed", "stderr": completed.stderr.strip()}
    first = completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""
    parts = [part.strip() for part in first.split(",")]
    if len(parts) < 7:
        return {"status": "unparsed", "raw": first}
    return {
        "status": "ok",
        "name": parts[0],
        "memory_total_mib": _to_int(parts[1]),
        "memory_used_mib": _to_int(parts[2]),
        "memory_free_mib": _to_int(parts[3]),
        "utilization_gpu_pct": _to_int(parts[4]),
        "temperature_celsius": _to_int(parts[5]),
        "driver_version": parts[6],
    }


def memory_snapshot() -> dict[str, int] | None:
    path = Path("/proc/meminfo")
    if not path.exists():
        return None
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    data: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, rest = line.partition(":")
        if key in wanted:
            value = rest.strip().split()[0]
            data[f"{key.lower()}_kib"] = int(value)
    return data


def model_fingerprint(model: str) -> dict[str, Any]:
    cmd = shutil.which("ollama")
    wsl_cmd = False
    if not cmd:
        # Intentar via WSL
        completed = subprocess.run(["wsl", "ollama", "list"], capture_output=True, text=True, check=False)
        if completed.returncode == 0:
            cmd = "wsl ollama"
            wsl_cmd = True
        else:
            return {"model": model, "status": "ollama_unavailable"}
            
    if not wsl_cmd:
        completed = subprocess.run([cmd, "list"], capture_output=True, text=True, check=False)
        
    if completed.returncode != 0:
        return {"model": model, "status": "list_failed", "stderr": completed.stderr.strip()[:300]}
    for line in completed.stdout.splitlines()[1:]:
        parts = line.split()
        if parts and parts[0] == model:
            return {
                "model": model,
                "status": "ok",
                "ollama_id": parts[1] if len(parts) > 1 else "",
                "size": parts[2] if len(parts) > 2 else "",
                "raw": line.strip(),
            }
    return {"model": model, "status": "missing"}


def promptset_hash(promptset: list[dict[str, str]]) -> str:
    return sha256_payload(promptset)


def benchmark_output_dir(node: str) -> Path:
    return EDGE_BENCHMARK_DIR if node.startswith("edge_iot") else PC_BENCHMARK_DIR


def run_log_path(*, node: str, run_id: str) -> Path:
    return benchmark_output_dir(node) / "runs" / f"{run_id}.jsonl"


def index_path(*, node: str) -> Path:
    return benchmark_output_dir(node) / "index.json"


def last_record_hash(path: Path) -> str:
    if not path.exists():
        return ""
    last = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            last = line
    if not last:
        return ""
    try:
        return str(json.loads(last).get("record_hash", ""))
    except json.JSONDecodeError:
        return ""


def append_hashed_record(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(record)
    payload.setdefault("previous_record_hash", last_record_hash(path))
    payload["record_hash"] = ""
    payload["record_hash"] = sha256_payload(payload)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return payload


def summarize_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(item["latency_ms"]) for item in samples if item.get("latency_ms") is not None]
    tokens_s = [float(item["tokens_per_second"]) for item in samples if item.get("tokens_per_second") is not None]
    if not latencies:
        return {"sample_size": 0, "status": "no_valid_samples"}
    mean = sum(latencies) / len(latencies)
    std_dev = math.sqrt(sum((item - mean) ** 2 for item in latencies) / len(latencies))
    return {
        "sample_size": len(latencies),
        "mean_latency_ms": round(mean, 4),
        "std_dev_latency_ms": round(std_dev, 4),
        "margin_error_95_ms": round(1.96 * (std_dev / math.sqrt(len(latencies))), 4),
        "p50_latency_ms": round(percentile(latencies, 0.50), 4),
        "p95_latency_ms": round(percentile(latencies, 0.95), 4),
        "p99_latency_ms": round(percentile(latencies, 0.99), 4),
        "mean_tokens_per_second": round(sum(tokens_s) / len(tokens_s), 4) if tokens_s else None,
    }


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * ratio) - 1))
    return ordered[index]


def build_run_header(
    *,
    profile_id: str,
    node: str,
    runtime: str,
    model: str,
    step_id: str,
    command: str,
    promptset: list[dict[str, str]],
    mode: str,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    if mode != "real":
        raise ValueError(f"Unsupported benchmark mode '{mode}'. Only 'real' is allowed.")
    scientific_validity = "valid_candidate"
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "run_header",
        "run_id": f"BENCH-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}",
        "step_id": step_id,
        "protocol": DEFAULT_PROTOCOL,
        "profile_id": profile_id,
        "node": node,
        "runtime": runtime,
        "model": model,
        "mode": mode,
        "scientific_validity": scientific_validity,
        "git_commit": git_commit(repo_root),
        "host_fingerprint": host_fingerprint(repo_root),
        "model_fingerprint": model_fingerprint(model),
        "promptset_hash": promptset_hash(promptset),
        "methodology_references": METHODOLOGY_REFERENCES,
        "command": command,
        "started_at": utc_now(),
    }


def build_sample_record(
    *,
    run_id: str,
    step_id: str,
    sample_index: int,
    phase: str,
    category: str,
    prompt_hash: str,
    latency_ms: float | None,
    ttft_ms: float | None,
    tokens_per_second: float | None,
    status: str,
    stdout: str = "",
    stderr: str = "",
    exit_status: int | None = None,
    mode: str = "real",
) -> dict[str, Any]:
    output_payload = {"stdout": stdout[:500], "stderr": stderr[:500]}
    return {
        "schema_version": SCHEMA_VERSION,
        "record_type": "sample",
        "run_id": run_id,
        "step_id": step_id,
        "sample_index": sample_index,
        "phase": phase,
        "category": category,
        "prompt_hash": prompt_hash,
        "timestamp_utc": utc_now(),
        "latency_ms": latency_ms,
        "ttft_ms": ttft_ms,
        "tokens_per_second": tokens_per_second,
        "memory": memory_snapshot(),
        "gpu": gpu_snapshot(),
        "status": status,
        "exit_status": exit_status,
        "input_hash": prompt_hash,
        "output_hash": sha256_payload(output_payload),
        "output_preview": stdout[:200],
        "error_preview": stderr[:200],
    }


def write_summary(
    *,
    path: Path,
    header: dict[str, Any],
    samples: list[dict[str, Any]],
    status: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stats = summarize_samples(samples)
    is_real_ok = status == "ok" and stats.get("sample_size", 0) > 0
    summary = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "run_summary",
        "run_id": header["run_id"],
        "step_id": header["step_id"],
        "profile_id": header["profile_id"],
        "node": header["node"],
        "runtime": header["runtime"],
        "model": header["model"],
        "status": status,
        "scientific_validity": "valid_scientific_evidence" if is_real_ok else "invalid_for_scientific_claim",
        "ended_at": utc_now(),
        "statistics": stats,
        "extra": extra or {},
    }
    return append_hashed_record(path, summary)


def update_index(*, node: str, summary: dict[str, Any], log_path: Path) -> dict[str, Any]:
    index = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": utc_now(),
        "node": node,
        "primary_pc_model": PRIMARY_PC_MODEL,
        "latest_run_id": summary["run_id"],
        "latest_status": summary["status"],
        "latest_scientific_validity": summary["scientific_validity"],
        "latest_record_hash": summary["record_hash"],
        "latest_jsonl": str(log_path.relative_to(ROOT)),
        "profiles": BENCHMARK_PROFILES,
        "methodology_references": METHODOLOGY_REFERENCES,
    }
    path = index_path(node=node)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return index


def validate_jsonl_artifact(path: Path) -> dict[str, Any]:
    previous = ""
    count = 0
    errors: list[str] = []
    if not path.exists():
        return {"status": "missing", "errors": [f"missing:{path}"], "records": 0}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        count += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line_{line_number}:json:{exc}")
            continue
        if record.get("previous_record_hash", "") != previous:
            errors.append(f"line_{line_number}:previous_record_hash")
        expected_payload = dict(record)
        expected_hash = expected_payload.get("record_hash", "")
        expected_payload["record_hash"] = ""
        actual_hash = sha256_payload(expected_payload)
        if expected_hash != actual_hash:
            errors.append(f"line_{line_number}:record_hash")
        previous = expected_hash
    return {"status": "ok" if not errors else "failed", "errors": errors, "records": count}


def _memory_total_bytes() -> int | None:
    try:
        return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, ValueError, OSError):
        return None


def _to_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None
