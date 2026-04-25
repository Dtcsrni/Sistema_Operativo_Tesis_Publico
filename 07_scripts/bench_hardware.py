from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_OLLAMA_MODEL = os.getenv("OPENCLAW_OLLAMA_BENCH_MODEL", "qwen2.5:0.5b")
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark de hardware local.")
    parser.add_argument("--json", action="store_true", help="Imprime JSON en stdout.")
    parser.add_argument("--ollama-model", default="", help="Modelo unico a usar para el benchmark de Ollama.")
    parser.add_argument(
        "--ollama-models",
        default="",
        help="Lista separada por comas de modelos Ollama a ejecutar en orden.",
    )
    parser.add_argument("--ollama-runs", type=int, default=1, help="Corridas por modelo Ollama.")
    parser.add_argument(
        "--ollama-prompt",
        default="Responde únicamente: listo",
        help="Prompt fijo a usar para cada corrida Ollama.",
    )
    parser.add_argument("--skip-disk", action="store_true", help="Omite el benchmark de disco.")
    parser.add_argument("--skip-ollama", action="store_true", help="Omite el benchmark de Ollama.")
    parser.add_argument("--skip-gpu", action="store_true", help="Omite el benchmark de GPU.")
    args = parser.parse_args()

    payload = collect_benchmarks(
        ollama_models=_parse_models(args.ollama_models, args.ollama_model),
        ollama_runs=max(1, args.ollama_runs),
        ollama_prompt=args.ollama_prompt,
        skip_disk=args.skip_disk,
        skip_ollama=args.skip_ollama,
        skip_gpu=args.skip_gpu,
    )
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text(payload))
    return 0


def collect_benchmarks(
    *,
    ollama_models: list[str],
    ollama_runs: int,
    ollama_prompt: str,
    skip_disk: bool,
    skip_ollama: bool,
    skip_gpu: bool,
) -> dict[str, Any]:
    host = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count() or 1,
        "memory_total_bytes": _memory_total_bytes(),
        "root_disk": _root_disk_usage(Path.cwd()),
    }
    cpu = _cpu_hash_benchmark()
    memory = _memory_copy_benchmark()
    disk = None if skip_disk else _disk_benchmark()
    gpu = None if skip_gpu else _gpu_benchmark()
    ollama = None if skip_ollama else [_ollama_benchmark(model, runs=ollama_runs, prompt=ollama_prompt) for model in ollama_models]
    return {
        "host": host,
        "benchmarks": {
            "cpu_sha256": cpu,
            "memory_copy": memory,
            "disk_io": disk,
            "gpu": gpu,
            "ollama": ollama,
        },
    }


def render_text(payload: dict[str, Any]) -> str:
    lines = [
        f"Host: {payload['host']['platform']} ({payload['host']['machine']})",
        f"CPU: {payload['host']['cpu_count']}",
        f"Mem total: {payload['host']['memory_total_bytes']}",
        "",
    ]
    for name, data in payload["benchmarks"].items():
        lines.append(f"[{name}]")
        lines.append(json.dumps(data, ensure_ascii=False, indent=2))
        lines.append("")
    return "\n".join(lines)


def _parse_models(models_arg: str, fallback: str) -> list[str]:
    raw = models_arg.strip() or fallback.strip() or DEFAULT_OLLAMA_MODEL
    models = [item.strip() for item in raw.split(",") if item.strip()]
    return models or [DEFAULT_OLLAMA_MODEL]


def _clean_output(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text).strip()


def _cpu_hash_benchmark() -> dict[str, Any]:
    block = b"x" * (16 * 1024 * 1024)
    rounds = 8
    start = time.perf_counter()
    digest = ""
    for _ in range(rounds):
        digest = hashlib.sha256(block).hexdigest()
    elapsed = time.perf_counter() - start
    total_mb = (len(block) * rounds) / (1024 * 1024)
    return {
        "rounds": rounds,
        "payload_mb": total_mb,
        "elapsed_s": round(elapsed, 4),
        "throughput_mb_s": round(total_mb / elapsed, 2) if elapsed > 0 else None,
        "digest": digest[:16],
    }


def _memory_copy_benchmark() -> dict[str, Any]:
    size = 64 * 1024 * 1024
    src = bytearray(b"a" * size)
    dst = bytearray(size)
    rounds = 12
    start = time.perf_counter()
    for _ in range(rounds):
        dst[:] = src
    elapsed = time.perf_counter() - start
    total_mb = (size * rounds) / (1024 * 1024)
    return {
        "rounds": rounds,
        "payload_mb": total_mb,
        "elapsed_s": round(elapsed, 4),
        "throughput_mb_s": round(total_mb / elapsed, 2) if elapsed > 0 else None,
    }


def _disk_benchmark() -> dict[str, Any]:
    size = 64 * 1024 * 1024
    data = os.urandom(size)
    temp_dir = Path(tempfile.gettempdir())
    path = temp_dir / f"codex-hardware-bench-{os.getpid()}.bin"
    write_start = time.perf_counter()
    with path.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    write_elapsed = time.perf_counter() - write_start
    read_start = time.perf_counter()
    with path.open("rb") as fh:
        while fh.read(1024 * 1024):
            pass
    read_elapsed = time.perf_counter() - read_start
    try:
        path.unlink()
    except OSError:
        pass
    total_mb = size / (1024 * 1024)
    return {
        "write": {
            "payload_mb": total_mb,
            "elapsed_s": round(write_elapsed, 4),
            "throughput_mb_s": round(total_mb / write_elapsed, 2) if write_elapsed > 0 else None,
        },
        "read": {
            "payload_mb": total_mb,
            "elapsed_s": round(read_elapsed, 4),
            "throughput_mb_s": round(total_mb / read_elapsed, 2) if read_elapsed > 0 else None,
        },
    }


def _gpu_benchmark() -> dict[str, Any]:
    snapshot = _gpu_snapshot()
    if snapshot is not None:
        return snapshot
    cmd = shutil.which("nvidia-smi")
    if not cmd:
        return {"status": "skipped_unavailable"}
    return {"status": "failed", "stderr": "nvidia-smi snapshot unavailable"}


def _gpu_snapshot() -> dict[str, Any] | None:
    cmd = shutil.which("nvidia-smi")
    if not cmd:
        return None
    query = [
        cmd,
        "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,driver_version",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(query, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return {
            "status": "failed",
            "returncode": completed.returncode,
            "stderr": completed.stderr.strip(),
        }
    raw = completed.stdout.strip()
    first = raw.splitlines()[0] if raw else ""
    parts = [part.strip() for part in first.split(",")]
    parsed = None
    if len(parts) >= 6:
        parsed = {
            "name": parts[0],
            "memory_total_mib": _to_int(parts[1]),
            "memory_used_mib": _to_int(parts[2]),
            "memory_free_mib": _to_int(parts[3]),
            "utilization_gpu_pct": _to_int(parts[4]),
            "driver_version": parts[5],
        }
    return {"status": "ok", "raw": raw, "parsed": parsed}


def _ollama_benchmark(model: str, *, runs: int, prompt: str) -> dict[str, Any]:
    cmd = shutil.which("ollama")
    if not cmd:
        return {"status": "skipped_unavailable"}
    listed = subprocess.run([cmd, "list"], capture_output=True, text=True, check=False)
    if listed.returncode != 0:
        return {"status": "failed_list", "stderr": listed.stderr.strip(), "stdout": listed.stdout.strip()}
    if model not in listed.stdout:
        return {"status": "skipped_model_missing", "model": model}
    results = [_ollama_run_once(cmd, model, prompt, index) for index in range(1, runs + 1)]
    elapsed_values = [item["elapsed_s"] for item in results if item["status"] == "ok"]
    gpu_peak = max((item.get("gpu_peak_memory_used_mib") or 0 for item in results), default=0)
    return {
        "status": "ok" if results and all(item["status"] == "ok" for item in results) else "failed",
        "model": model,
        "runs": results,
        "cold_elapsed_s": elapsed_values[0] if elapsed_values else None,
        "warm_elapsed_s": elapsed_values[-1] if len(elapsed_values) > 1 else None,
        "best_elapsed_s": min(elapsed_values) if elapsed_values else None,
        "gpu_peak_memory_used_mib": gpu_peak or None,
    }


def _ollama_run_once(cmd: str, model: str, prompt: str, index: int) -> dict[str, Any]:
    before_gpu = _gpu_snapshot()
    before_memory = _memory_snapshot()
    gpu_samples: list[dict[str, Any]] = []
    start = time.perf_counter()
    process = subprocess.Popen([cmd, "run", model, prompt], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    timed_out = False
    while process.poll() is None:
        snapshot = _gpu_snapshot()
        if snapshot is not None:
            gpu_samples.append(snapshot)
        if time.perf_counter() - start > 300:
            process.kill()
            timed_out = True
            break
        time.sleep(0.5)
    stdout, stderr = process.communicate()
    elapsed = time.perf_counter() - start
    after_gpu = _gpu_snapshot()
    after_memory = _memory_snapshot()
    returncode = process.returncode if process.returncode is not None else -9
    peak_memory = _gpu_peak_memory(gpu_samples)
    return {
        "run": index,
        "status": "timeout" if timed_out else ("ok" if returncode == 0 else "failed"),
        "elapsed_s": round(elapsed, 4),
        "returncode": returncode,
        "stdout": _clean_output(stdout)[:300],
        "stderr": "" if returncode == 0 else _clean_output(stderr)[:300],
        "memory_before": before_memory,
        "memory_after": after_memory,
        "gpu_before": before_gpu,
        "gpu_after": after_gpu,
        "gpu_samples": len(gpu_samples),
        "gpu_peak_memory_used_mib": peak_memory,
    }


def _gpu_peak_memory(samples: list[dict[str, Any]]) -> int | None:
    values = []
    for sample in samples:
        parsed = sample.get("parsed") or {}
        value = parsed.get("memory_used_mib")
        if isinstance(value, int):
            values.append(value)
    return max(values) if values else None


def _memory_snapshot() -> dict[str, int] | None:
    path = Path("/proc/meminfo")
    if not path.exists():
        return None
    wanted = {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}
    data: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, _, rest = line.partition(":")
        if key in wanted:
            parts = rest.strip().split()
            if parts:
                data[f"{key.lower()}_kib"] = int(parts[0])
    return data


def _memory_total_bytes() -> int | None:
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        return int(page_size * phys_pages)
    except (AttributeError, ValueError, OSError):
        return None


def _to_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _root_disk_usage(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {
        "path": str(path),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


if __name__ == "__main__":
    raise SystemExit(main())
