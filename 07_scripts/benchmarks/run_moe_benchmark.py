from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_science import (  # noqa: E402
    MOE_BENCHMARK_PROFILE_ID,
    MOE_MODEL_ROLES,
    MOE_PRECISION_POLICY,
    append_hashed_record,
    build_run_header,
    build_sample_record,
    moe_matrix,
    moe_models,
    moe_promptset,
    moe_tasks,
    promptset_hash,
    run_log_path,
    update_index,
    utc_now,
    write_summary,
)

ROOT = Path(__file__).resolve().parents[2]
PC_BENCHMARK_DIR = ROOT / "runtime" / "pc_control" / "benchmarks"
OVERALL_OUTPUT_PATH = PC_BENCHMARK_DIR / "moe_battery_latest.json"
PROGRESS_OUTPUT_PATH = PC_BENCHMARK_DIR / "moe_battery_progress.jsonl"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bateria MoE de benchmarks por modelo y por tarea.")
    parser.add_argument("--models", default="", help="Lista separada por comas. Por defecto usa el orden MoE completo.")
    parser.add_argument("--tasks", default="", help="Lista separada por comas. Por defecto usa todas las tareas MoE.")
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=4)
    parser.add_argument("--interval-ms", type=int, default=500)
    parser.add_argument("--num-predict", type=int, default=96)
    parser.add_argument("--num-ctx", type=int, default=2048)
    parser.add_argument("--step-id", default="VAL-STEP-PENDING")
    parser.add_argument("--node", default="pc_control", choices=["pc_control", "edge_iot"])
    args = parser.parse_args()

    requested_models = _parse_csv(args.models)
    requested_tasks = _parse_csv(args.tasks)
    selected_models = moe_models(requested=requested_models)
    selected_tasks = moe_tasks(requested=requested_tasks)

    runs: list[dict[str, object]] = []
    overall_status = "ok"
    progress_state = {
        "schema_version": "siot-benchmark-run-v1",
        "record_type": "moe_battery_progress",
        "run_id": f"MOE-{utc_now().replace(':', '').replace('-', '').replace('T', 'T').replace('+00:00', 'Z')}",
        "profile_id": MOE_BENCHMARK_PROFILE_ID,
        "node": args.node,
        "step_id": args.step_id,
        "selected_models": selected_models,
        "selected_tasks": [task["id"] for task in selected_tasks],
        "completed_models": [],
        "completed_tasks": [],
        "active_model": None,
        "active_task": None,
        "status": "running",
        "model_roles": MOE_MODEL_ROLES,
        "precision_policy": MOE_PRECISION_POLICY,
        "updated_at": utc_now(),
    }
    _write_progress_snapshot(progress_state)
    print(json.dumps({"event": "moe_battery_start", "run_id": progress_state["run_id"], "models": selected_models, "tasks": [task["id"] for task in selected_tasks]}, ensure_ascii=False), flush=True)

    for model_index, model in enumerate(selected_models, start=1):
        progress_state["active_model"] = model
        progress_state["active_task"] = None
        progress_state["active_model_index"] = model_index
        progress_state["active_task_index"] = 0
        progress_state["updated_at"] = utc_now()
        _write_progress_snapshot(progress_state)
        print(json.dumps({"event": "model_start", "model": model, "index": model_index, "total": len(selected_models)}, ensure_ascii=False), flush=True)
        model_result = _run_model_battery(
            model=model,
            tasks=selected_tasks,
            warmups=args.warmups,
            iterations=args.iterations,
            interval_ms=args.interval_ms,
            num_predict=args.num_predict,
            num_ctx=args.num_ctx,
            step_id=args.step_id,
            node=args.node,
            progress_state=progress_state,
        )
        runs.append(model_result)
        progress_state["completed_models"].append(model)
        progress_state["active_model"] = None
        progress_state["active_task"] = None
        progress_state["completed_tasks"] = list(dict.fromkeys(progress_state["completed_tasks"]))
        progress_state["updated_at"] = utc_now()
        _write_progress_snapshot(progress_state)
        print(json.dumps({"event": "model_end", "model": model, "status": model_result["status"], "run_id": model_result["run_id"]}, ensure_ascii=False), flush=True)
        if model_result["status"] != "ok":
            overall_status = "partial_failure"

    overall_payload = {
        "schema_version": "siot-benchmark-run-v1",
        "record_type": "moe_battery_overview",
        "run_id": f"MOE-{utc_now().replace(':', '').replace('-', '').replace('T', 'T').replace('+00:00', 'Z')}",
        "profile_id": MOE_BENCHMARK_PROFILE_ID,
        "node": args.node,
        "step_id": args.step_id,
        "precision_policy": MOE_PRECISION_POLICY,
        "selected_models": selected_models,
        "selected_tasks": [task["id"] for task in selected_tasks],
        "runs": runs,
        "status": overall_status,
        "generated_at": utc_now(),
        "model_roles": MOE_MODEL_ROLES,
        "matrix_size": len(moe_matrix(models=selected_models, tasks=[task["id"] for task in selected_tasks])),
    }
    progress_state["status"] = overall_status
    progress_state["updated_at"] = utc_now()
    _write_progress_snapshot(progress_state)
    OVERALL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERALL_OUTPUT_PATH.write_text(json.dumps(overall_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"event": "moe_battery_complete", "status": overall_status, "overview": str(OVERALL_OUTPUT_PATH), "runs": runs}, ensure_ascii=False, indent=2), flush=True)
    return 0 if overall_status == "ok" else 1


def _run_model_battery(
    *,
    model: str,
    tasks: list[dict[str, object]],
    warmups: int,
    iterations: int,
    interval_ms: int,
    num_predict: int,
    num_ctx: int,
    step_id: str,
    node: str,
    progress_state: dict[str, object] | None = None,
) -> dict[str, object]:
    profile_id = f"{MOE_BENCHMARK_PROFILE_ID}:{model}"
    promptset = moe_promptset(models=[model], tasks=[task["id"] for task in tasks])
    header = build_run_header(
        profile_id=profile_id,
        node=node,
        runtime="ollama_local",
        model=model,
        step_id=step_id,
        command="python3 07_scripts/benchmarks/run_moe_benchmark.py",
        promptset=promptset,
        mode="real",
        repo_root=ROOT,
    )
    log_path = run_log_path(node=node, run_id=header["run_id"])
    append_hashed_record(log_path, header)
    print(json.dumps({"event": "run_header_written", "model": model, "run_id": header["run_id"], "jsonl": str(log_path)}, ensure_ascii=False), flush=True)

    extra: dict[str, object] = {
        "profile": {
            "model": model,
            "role": MOE_MODEL_ROLES.get(model, {}).get("role", "unknown"),
            "task_count": len(tasks),
            "task_ids": [task["id"] for task in tasks],
            "precision_policy": MOE_PRECISION_POLICY,
        },
        "model_role": MOE_MODEL_ROLES.get(model, {}).get("role", "unknown"),
        "model_notes": MOE_MODEL_ROLES.get(model, {}).get("notes", ""),
        "tasks": [task["id"] for task in tasks],
    }

    if not _ollama_model_available(model):
        status = "blocked_missing_model"
        summary = write_summary(path=log_path, header=header, samples=[], status=status, extra=extra)
        update_index(node=node, summary=summary, log_path=log_path)
        _write_model_report(model=model, header=header, summary=summary, log_path=log_path, extra=extra)
        _emit_progress(progress_state, {"event": "model_blocked", "model": model, "status": status, "run_id": header["run_id"]})
        return {
            "model": model,
            "role": extra["model_role"],
            "status": status,
            "run_id": header["run_id"],
            "jsonl": str(log_path),
            "report": str(_model_report_path(model)),
        }

    samples: list[dict[str, float | None]] = []
    status = "ok"
    sample_index = 0

    for warmup in range(warmups):
        sample_index += 1
        if progress_state is not None:
            progress_state["active_task"] = "warmup"
            progress_state["active_task_index"] = warmup + 1
            progress_state["updated_at"] = utc_now()
            _write_progress_snapshot(progress_state)
        print(json.dumps({"event": "warmup_start", "model": model, "warmup_index": warmup + 1, "warmups_total": warmups}, ensure_ascii=False), flush=True)
        result = _ollama_generate(model, "Responde unicamente: listo", num_predict, num_ctx)
        append_hashed_record(
            log_path,
            build_sample_record(
                run_id=header["run_id"],
                step_id=step_id,
                sample_index=sample_index,
                phase="warmup",
                category="warmup",
                prompt_hash=promptset_hash([{ "prompt": "warmup" }]),
                latency_ms=result.get("latency_ms"),
                ttft_ms=result.get("ttft_ms"),
                tokens_per_second=result.get("tokens_per_second"),
                status=str(result["status"]),
                stdout=str(result.get("response", "")),
                stderr=str(result.get("error", "")),
                exit_status=0 if result["status"] == "ok" else 1,
                metadata={"model": model, "phase": "warmup", "warmup_index": warmup + 1},
            ),
        )
        _emit_progress(progress_state, {"event": "warmup_end", "model": model, "warmup_index": warmup + 1, "status": result["status"], "latency_ms": result.get("latency_ms")})
        time.sleep(interval_ms / 1000.0)

    for task_index, task in enumerate(tasks, start=1):
        task_id = str(task["id"])
        task_prompt = str(task["prompt"])
        if progress_state is not None:
            progress_state["active_task"] = task_id
            progress_state["active_task_index"] = task_index
            progress_state["updated_at"] = utc_now()
            _write_progress_snapshot(progress_state)
        print(json.dumps({"event": "task_start", "model": model, "task": task_id, "index": task_index, "total": len(tasks)}, ensure_ascii=False), flush=True)
        for iteration in range(iterations):
            sample_index += 1
            result = _ollama_generate(model, task_prompt, num_predict, num_ctx)
            sample = build_sample_record(
                run_id=header["run_id"],
                step_id=step_id,
                sample_index=sample_index,
                phase="measurement",
                category=task_id,
                prompt_hash=promptset_hash([task | {"model": model}]),
                latency_ms=result.get("latency_ms"),
                ttft_ms=result.get("ttft_ms"),
                tokens_per_second=result.get("tokens_per_second"),
                status=str(result["status"]),
                stdout=str(result.get("response", "")),
                stderr=str(result.get("error", "")),
                exit_status=0 if result["status"] == "ok" else 1,
                metadata={
                    "model": model,
                    "role": extra["model_role"],
                    "task_name": task["name"],
                    "precision_priority": task["precision_priority"],
                    "expected_behavior": task["expected_behavior"],
                },
            )
            append_hashed_record(log_path, sample)
            if result["status"] == "ok":
                samples.append({"latency_ms": result.get("latency_ms"), "tokens_per_second": result.get("tokens_per_second")})
            else:
                status = "partial_failure"
            _emit_progress(
                progress_state,
                {
                    "event": "task_sample",
                    "model": model,
                    "task": task_id,
                    "iteration": iteration + 1,
                    "iterations_total": iterations,
                    "status": result["status"],
                    "latency_ms": result.get("latency_ms"),
                },
            )
            time.sleep(interval_ms / 1000.0)
        if progress_state is not None:
            completed = progress_state.setdefault("completed_tasks", [])
            if isinstance(completed, list) and task_id not in completed:
                completed.append(task_id)
            progress_state["updated_at"] = utc_now()
            _write_progress_snapshot(progress_state)
        print(json.dumps({"event": "task_end", "model": model, "task": task_id, "status": status}, ensure_ascii=False), flush=True)

    summary = write_summary(path=log_path, header=header, samples=samples, status=status, extra=extra)
    update_index(node=node, summary=summary, log_path=log_path)
    _write_model_report(model=model, header=header, summary=summary, log_path=log_path, extra=extra)
    _emit_progress(progress_state, {"event": "model_summary", "model": model, "status": status, "scientific_validity": summary["scientific_validity"], "run_id": header["run_id"]})
    return {
        "model": model,
        "role": extra["model_role"],
        "status": status,
        "run_id": header["run_id"],
        "jsonl": str(log_path),
        "report": str(_model_report_path(model)),
        "scientific_validity": summary["scientific_validity"],
    }


def _parse_csv(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _slugify_model(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def _model_report_path(model: str) -> Path:
    return PC_BENCHMARK_DIR / "reports" / f"moe_{_slugify_model(model)}.json"


def _write_model_report(*, model: str, header: dict[str, object], summary: dict[str, object], log_path: Path, extra: dict[str, object]) -> None:
    payload = {
        "generated_at": utc_now(),
        "model": model,
        "header": header,
        "summary": summary,
        "extra": extra,
        "jsonl": str(log_path.relative_to(ROOT)),
        "precision_policy": MOE_PRECISION_POLICY,
    }
    path = _model_report_path(model)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_progress_snapshot(progress_state: dict[str, object]) -> None:
    PROGRESS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = dict(progress_state)
    record["record_hash"] = ""
    record["record_hash"] = __import__("hashlib").sha256(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    with PROGRESS_OUTPUT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()


def _emit_progress(progress_state: dict[str, object] | None, event: dict[str, object]) -> None:
    if progress_state is None:
        print(json.dumps(event, ensure_ascii=False), flush=True)
        return
    event_payload = dict(event)
    event_payload["run_id"] = progress_state.get("run_id")
    event_payload["updated_at"] = utc_now()
    print(json.dumps(event_payload, ensure_ascii=False), flush=True)


def _ollama_model_available(model: str) -> bool:
    cmd = shutil.which("ollama")
    if cmd:
        completed = subprocess.run([cmd, "list"], capture_output=True, text=True, check=False)
    else:
        completed = subprocess.run(["wsl", "ollama", "list"], capture_output=True, text=True, check=False)
    return completed.returncode == 0 and any(line.split() and line.split()[0] == model for line in completed.stdout.splitlines()[1:])


def _ollama_generate(model: str, prompt: str, num_predict: int, num_ctx: int) -> dict[str, object]:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": num_predict, "num_ctx": num_ctx},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(f"{OLLAMA_BASE_URL}/api/generate", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=180) as response:
            parsed = json.loads(response.read().decode("utf-8", errors="replace"))
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        eval_count = float(parsed.get("eval_count") or 0)
        eval_duration_ns = float(parsed.get("eval_duration") or 0)
        prompt_eval_duration_ns = float(parsed.get("prompt_eval_duration") or 0)
        tokens_per_second = (eval_count / (eval_duration_ns / 1_000_000_000.0)) if eval_count and eval_duration_ns else None
        ttft_ms = (prompt_eval_duration_ns / 1_000_000.0) if prompt_eval_duration_ns else None
        return {
            "status": "ok",
            "latency_ms": round(elapsed_ms, 4),
            "ttft_ms": round(ttft_ms, 4) if ttft_ms is not None else None,
            "tokens_per_second": round(tokens_per_second, 4) if tokens_per_second is not None else None,
            "response": str(parsed.get("response", "")),
        }
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {"status": "failed", "latency_ms": round(elapsed_ms, 4), "ttft_ms": None, "tokens_per_second": None, "error": f"{type(exc).__name__}:{exc}"}


if __name__ == "__main__":
    raise SystemExit(main())