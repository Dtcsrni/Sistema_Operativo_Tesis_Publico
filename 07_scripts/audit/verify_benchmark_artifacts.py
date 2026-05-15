from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks")) # benchmarks scripts



import argparse
import json

from benchmark_science import ROOT, SCHEMA_VERSION, validate_jsonl_artifact

def _validate_real_execution(path: Path) -> list[str]:
    issues: list[str] = []
    if not path.exists():
        return ["missing_file"]

    saw_summary = False
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            issues.append(f"line_{line_number}:invalid_json")
            continue

        status = str(record.get("status", ""))
        if status == "simulation_only":
            issues.append(f"line_{line_number}:simulation_only_not_allowed")

        if record.get("record_type") == "run_summary":
            saw_summary = True
            if status != "ok":
                issues.append(f"line_{line_number}:summary_status_{status}")
            scientific = str(record.get("scientific_validity", ""))
            if scientific != "valid_scientific_evidence":
                issues.append(f"line_{line_number}:summary_scientific_validity_{scientific}")
            sample_size = ((record.get("statistics") or {}).get("sample_size"))
            if not isinstance(sample_size, int) or sample_size <= 0:
                issues.append(f"line_{line_number}:invalid_sample_size_{sample_size}")

    if not saw_summary:
        issues.append("missing_run_summary")
    return issues

def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica artefactos de benchmark cientifico SIOT.")
    parser.add_argument("paths", nargs="*", help="JSONL especificos; si se omiten se buscan runs locales.")
    args = parser.parse_args()

    explicit_paths = bool(args.paths)
    paths = [Path(item) for item in args.paths]
    if not paths:
        paths = sorted((ROOT / "runtime").glob("*/benchmarks/runs/*.jsonl"))
    latest_ok_paths = _latest_ok_paths()
    results = []
    for path in paths:
        absolute = path if path.is_absolute() else ROOT / path
        result = validate_jsonl_artifact(absolute)
        enforce_real_execution = explicit_paths or absolute.resolve() in latest_ok_paths
        result["real_execution_issues"] = _validate_real_execution(absolute) if enforce_real_execution else []
        result["real_execution_enforced"] = enforce_real_execution
        if result["real_execution_issues"]:
            result["status"] = "failed"
        result["path"] = str(absolute.relative_to(ROOT) if absolute.is_relative_to(ROOT) else absolute)
        results.append(result)

    status = "ok" if all(item["status"] == "ok" for item in results) else "failed"
    if not results:
        status = "skipped_no_artifacts"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "artifacts": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] in {"ok", "skipped_no_artifacts"} else 1

def _latest_ok_paths() -> set[Path]:
    paths: set[Path] = set()
    for index in (ROOT / "runtime").glob("*/benchmarks/index.json"):
        try:
            payload = json.loads(index.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("latest_status") != "ok":
            continue
        raw = str(payload.get("latest_jsonl", "")).replace("\\", "/")
        if raw:
            paths.add((ROOT / raw).resolve())
    return paths

if __name__ == "__main__":
    raise SystemExit(main())
