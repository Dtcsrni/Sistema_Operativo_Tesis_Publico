#!/usr/bin/env python3
"""Consolida los `run_summary` de runtime/pc_control/benchmarks/runs en un CSV.

Escribe: runtime/pc_control/benchmarks/moe_run_summaries.csv
"""
from pathlib import Path
import json
import csv

RUNS_DIR = Path("runtime/pc_control/benchmarks/runs")
OUT_CSV = Path("runtime/pc_control/benchmarks/moe_run_summaries.csv")

def extract_summary(run_path: Path):
    header = None
    summary = None
    started_at = None
    ended_at = None
    with run_path.open("r", encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            rt = obj.get("record_type")
            if rt == "run_header":
                header = obj
                started_at = obj.get("started_at")
            if rt == "run_summary":
                summary = obj
                ended_at = obj.get("ended_at") or ended_at
    if not summary:
        return None
    stats = summary.get("statistics", {}) or {}
    return {
        "run_id": summary.get("run_id"),
        "model": summary.get("model"),
        "runtime": summary.get("runtime"),
        "started_at": started_at or "",
        "ended_at": ended_at or summary.get("ended_at", ""),
        "status": summary.get("status", ""),
        "scientific_validity": summary.get("scientific_validity", ""),
        "mean_latency_ms": stats.get("mean_latency_ms", ""),
        "mean_tokens_per_second": stats.get("mean_tokens_per_second", ""),
        "sample_size": stats.get("sample_size", ""),
        "p50_latency_ms": stats.get("p50_latency_ms", ""),
        "p95_latency_ms": stats.get("p95_latency_ms", ""),
        "p99_latency_ms": stats.get("p99_latency_ms", ""),
        "record_hash": summary.get("record_hash", ""),
    }

def main():
    out_rows = []
    if not RUNS_DIR.exists():
        print("No existe el directorio de runs:", RUNS_DIR)
        return
    for p in sorted(RUNS_DIR.glob("BENCH-*.jsonl")):
        s = extract_summary(p)
        if s:
            out_rows.append(s)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_id", "model", "runtime", "started_at", "ended_at",
        "status", "scientific_validity", "mean_latency_ms",
        "mean_tokens_per_second", "sample_size",
        "p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "record_hash"
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for r in out_rows:
            writer.writerow(r)

    print(f"Wrote CSV: {OUT_CSV}")

if __name__ == "__main__":
    main()
