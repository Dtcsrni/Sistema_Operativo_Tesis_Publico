from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "runtime" / "openclaw"
SCRIPTS_ROOT = ROOT / "07_scripts"

if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from canon import append_openclaw_proposal, load_events  # noqa: E402
from openclaw_local.contracts import (  # noqa: E402
    BenchmarkRecord,
    ClaimRecord,
    LiteratureRecord,
    NodeBenchmarkReport,
    ProviderProbe,
    QualityEvalResult,
    TaskEnvelope,
    WritingDraft,
)
from openclaw_local.budgeting import build_billing_record, build_budget_snapshot, simulate_budget_request  # noqa: E402
from openclaw_local.engine import (  # noqa: E402
    build_academic_packet,
    build_evidence_record,
    default_data_dir,
    render_academic_artifacts,
    route_task,
)
from openclaw_local.image_backend import generate_image_from_prompt  # noqa: E402
from openclaw_local.policies import load_budget_policy, load_domain_policies, load_domain_secret_policies, load_provider_registry  # noqa: E402
from openclaw_local.runtime_status import (  # noqa: E402
    build_preflight_report,
    build_runtime_probe,
    probe_runtime_status,
    run_runtime_benchmarks,
    summarize_host,
)
from openclaw_local.serena_adapter import SerenaClient  # noqa: E402
from openclaw_local.secret_resolver import build_secret_status, resolve_provider_secret  # noqa: E402
from openclaw_local.storage import OpenClawStore  # noqa: E402
from openclaw_local.notifier import dispatch_ready_notification, dispatch_test_notification  # noqa: E402
from openclaw_local.matrix_bot import matrix_configured, poll_matrix_once, process_matrix_event, run_matrix_loop  # noqa: E402
from openclaw_local.session_layer import build_nodes_summary, build_provider_summary, process_channel_text  # noqa: E402
from openclaw_local.telegram_bot import dispatch_command, handle_update, poll_once, run_polling_loop, telegram_configured  # noqa: E402
from openclaw_local.telemetry import export_request_traces_to_otel_jsonl  # noqa: E402
from openclaw_local.web import serve_workspace, web_stack_name  # noqa: E402
from openclaw_local.web_session import build_web_session_status, open_login_session  # noqa: E402


ACADEMIC_CANONICAL_TARGETS = {
    "estado_del_arte": [
        "docs/05_reproducibilidad/matriz-de-literatura.md",
        "docs/05_reproducibilidad/matriz-de-afirmaciones-y-evidencia.md",
    ],
    "metodologia": [
        "docs/05_reproducibilidad/matriz-de-exploracion-y-analisis.md",
        "docs/05_reproducibilidad/metodologia-de-estudio-de-sistemas-y-conceptos.md",
    ],
}


def _store() -> OpenClawStore:
    data_dir = default_data_dir(ROOT)
    db_path = Path(os.getenv("OPENCLAW_DB_PATH", data_dir / "openclaw.db"))
    return OpenClawStore(db_path)


def _safe_store_write(operation: str, fn: Any) -> dict[str, Any] | None:
    try:
        fn()
        return None
    except sqlite3.OperationalError as exc:
        return {"operation": operation, "error": f"sqlite_operational_error:{exc}"}


def _resolve_serena_mode(args: argparse.Namespace) -> str:
    cli_mode = str(getattr(args, "serena_mode", "") or "").strip().lower()
    if cli_mode in {"off", "required"}:
        return cli_mode
    env_mode = os.getenv("OPENCLAW_SERENA_MODE", "auto").strip().lower()
    if env_mode in {"off", "required"}:
        return env_mode
    return "auto"


def _should_use_serena(task: TaskEnvelope, *, mode: str) -> bool:
    if mode == "off":
        return False
    if not _env_enabled("OPENCLAW_SERENA_ENABLED", True):
        return False
    academic_mode = str(task.extra_context.get("academic_mode", "")).strip()
    if academic_mode:
        return True
    if task.target_paths:
        return True
    if task.requires_citations:
        return True
    if task.mutates_state:
        return True
    return task.risk_level in {"high", "critical"}


def _env_enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def _serena_can_degrade(task: TaskEnvelope, *, dry_run: bool, write_artifacts: bool) -> bool:
    if dry_run:
        return True
    if write_artifacts:
        return False
    return not task.mutates_state


def _serena_fetch_query(task: TaskEnvelope) -> str:
    explicit = str(task.extra_context.get("serena_query", "")).strip()
    if explicit:
        return explicit
    if task.target_paths:
        return ""
    return task.title.strip()


def _serena_limit(task: TaskEnvelope) -> int:
    if not task.target_paths:
        return 3
    return max(1, min(len(task.target_paths), 3))


def _serena_requires_preflight(task: TaskEnvelope) -> bool:
    academic_mode = str(task.extra_context.get("academic_mode", "")).strip()
    if not task.target_paths:
        return False
    if task.mutates_state:
        return True
    if task.risk_level in {"high", "critical"}:
        return True
    return academic_mode in {"metodologia", "redaccion_tesis"}


def _collect_serena_context(
    task: TaskEnvelope,
    *,
    mode: str,
    dry_run: bool,
    write_artifacts: bool,
    intent: str,
) -> tuple[dict[str, Any], str | None]:
    payload: dict[str, Any] = {
        "enabled": mode != "off",
        "mode": mode,
        "status": "skipped" if mode == "off" else "pending",
        "tool_invocations": [],
        "available": False,
        "transport": "",
        "references": [],
    }
    if not _should_use_serena(task, mode=mode):
        payload["status"] = "skipped"
        payload["reason"] = "heuristica_desactivada"
        return payload, None

    client = SerenaClient.from_repo(ROOT)
    payload["transport"] = client.transport
    health = client.healthcheck()
    payload["healthcheck"] = health
    payload["available"] = health.get("status") == "ok"
    if health.get("status") != "ok":
        payload["status"] = "unavailable"
        payload["error"] = str(health.get("error", "Serena MCP no disponible"))
        if mode == "required" or not _serena_can_degrade(task, dry_run=dry_run, write_artifacts=write_artifacts):
            payload["blocked"] = True
            return payload, payload["error"]
        payload["degraded"] = True
        return payload, None

    if task.target_paths:
        context_fetch = client.fetch_compact(
            query=_serena_fetch_query(task),
            paths=task.target_paths,
            limit=_serena_limit(task),
            context_lines=1,
        )
        payload["context_fetch"] = context_fetch
        payload["tool_invocations"].append("context.fetch_compact")
        payload["references"] = list(context_fetch.get("references", []))

    if _serena_requires_preflight(task):
        preflight = client.preflight(
            tool_name="canon.apply_controlled_change",
            target_paths=task.target_paths,
            step_id="",
            source_event_id="",
            intent=intent,
        )
        payload["preflight"] = preflight
        payload["tool_invocations"].append("governance.preflight")
        if str(preflight.get("status", "")).strip().lower() == "blocked":
            payload["blocked"] = True

    payload["status"] = "ok"
    return payload, None


def _annotate_diff_summary(base: str, serena: dict[str, Any]) -> str:
    lines: list[str] = []
    status = str(serena.get("status", "")).strip()
    if status:
        lines.append(f"Serena MCP: {status}")
    if serena.get("blocked"):
        lines.append("Serena MCP detectó bloqueo de gobernanza.")
    preflight = serena.get("preflight")
    if isinstance(preflight, dict) and preflight.get("next_required_action"):
        lines.append(f"Acción requerida: {preflight['next_required_action']}")
    if serena.get("references"):
        refs = ", ".join(str(item) for item in serena.get("references", [])[:3])
        lines.append(f"Referencias MCP: {refs}")
    if not lines:
        return base
    note = " | ".join(lines)
    return f"{note}\n{base}" if base else note


def _build_task(args: argparse.Namespace) -> TaskEnvelope:
    extra_context = dict(getattr(args, "extra_context", {}) or {})
    return TaskEnvelope(
        task_id=args.task_id,
        title=args.title,
        domain=args.domain,
        objective=args.objective,
        complexity=args.complexity,
        risk_level=args.risk_level,
        mutates_state=args.mutates_state,
        target_paths=args.target_paths or [],
        requires_citations=args.requires_citations,
        preferred_mode=args.preferred_mode,
        session_id=getattr(args, "session_id", "") or "",
        extra_context=extra_context,
    )


def cmd_doctor(_: argparse.Namespace) -> int:
    policies = load_domain_policies(ROOT)
    registry = load_provider_registry(ROOT)
    store = _store()
    summary = store.audit_summary()
    secret_policies = load_domain_secret_policies(ROOT)
    budget_policy = load_budget_policy(ROOT)
    _persist_secret_status(store, secret_policies, registry)
    budget_snapshot = build_budget_snapshot(store=store, repo_root=ROOT, budget_policy=budget_policy)
    store.save_budget_snapshot(budget_snapshot)
    runtime_probe = build_runtime_probe(ROOT, source_command="doctor")
    store.save_runtime_probe(runtime_probe)
    payload = {
        "status": "ok",
        "deployment_state": runtime_probe.system_state,
        "domains": sorted(policies["domains"].keys()),
        "proveedores": [item["id"] for item in registry.get("providers", [])],
        "nodes": build_nodes_summary(ROOT),
        "web_enabled": True,
        "web_stack": web_stack_name(),
        "store": summary,
        "host": summarize_host(ROOT),
        "runtime_status": runtime_probe.payload,
        "secretos": build_secret_status(secret_policies=secret_policies, provider_registry=registry),
        "presupuesto": budget_snapshot.payload,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_web_session_status(_: argparse.Namespace) -> int:
    print(json.dumps(build_web_session_status(), ensure_ascii=False, indent=2))
    return 0


def cmd_web_session_login(args: argparse.Namespace) -> int:
    ok, detail, status = open_login_session(timeout_seconds=args.timeout)
    payload = {"status": "ok" if ok else "error", "detail": detail, "web_session": status}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def cmd_task_new(args: argparse.Namespace) -> int:
    task = _build_task(args)
    policies = load_domain_policies(ROOT)
    store = _store()
    decision = route_task(task, policies, repo_root=ROOT, store=store)
    serena, error = _collect_serena_context(
        task,
        mode=_resolve_serena_mode(args),
        dry_run=True,
        write_artifacts=False,
        intent=f"Registrar tarea {task.task_id}",
    )
    if error:
        print(json.dumps({"error": error, "serena": serena}, ensure_ascii=False, indent=2))
        return 1
    store.save_task(task, decision)
    _save_resolution_for_decision(store, task.domain, decision.provider)
    print(json.dumps({"task": task.to_dict(), "decision": decision.to_dict(), "serena": serena}, ensure_ascii=False, indent=2))
    return 0


def cmd_task_route(args: argparse.Namespace) -> int:
    task = _build_task(args)
    store = _store()
    decision = route_task(task, load_domain_policies(ROOT), repo_root=ROOT, store=store)
    serena, error = _collect_serena_context(
        task,
        mode=_resolve_serena_mode(args),
        dry_run=True,
        write_artifacts=False,
        intent=f"Enrutar tarea {task.task_id}",
    )
    if error:
        print(json.dumps({"error": error, "serena": serena}, ensure_ascii=False, indent=2))
        return 1
    _save_resolution_for_decision(store, task.domain, decision.provider)
    print(json.dumps({"decision": decision.to_dict(), "serena": serena}, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    task = _build_task(args)
    policies = load_domain_policies(ROOT)
    store = _store()
    decision = route_task(task, policies, repo_root=ROOT, store=store)
    serena, error = _collect_serena_context(
        task,
        mode=_resolve_serena_mode(args),
        dry_run=args.dry_run,
        write_artifacts=False,
        intent=args.diff_summary or args.objective,
    )
    if error:
        print(json.dumps({"error": error, "task": task.to_dict(), "decision": decision.to_dict(), "serena": serena}, ensure_ascii=False, indent=2))
        return 1
    store.save_task(task, decision)
    _save_resolution_for_decision(store, task.domain, decision.provider)
    evidence = build_evidence_record(
        task=task,
        decision=decision,
        prompt=args.prompt,
        response="dry-run",
        context={"mode": "dry-run", "serena": serena},
        estimated_cost=decision.estimated_cost,
        source_links=task.target_paths,
        session_id=args.session_id,
    )
    store.save_evidence(evidence)
    store.save_billing_record(
        build_billing_record(
            task_id=task.task_id,
            session_id=args.session_id,
            domain=task.domain,
            provider=decision.provider,
            billing_mode=decision.billing_mode,
            estimated_tokens=decision.estimated_tokens,
            estimated_cost_usd=decision.estimated_cost,
        )
    )
    result = {
        "task": task.to_dict(),
        "decision": decision.to_dict(),
        "dry_run": args.dry_run,
        "evidence_id": evidence.evidence_id,
        "serena": serena,
    }
    if decision.requires_human_gate:
        approval_id = store.create_approval_request(
            task=task,
            decision=decision,
            diff_summary=_annotate_diff_summary(args.diff_summary or "Pendiente de autorización humana", serena),
            affected_targets=task.target_paths,
            step_id_expected=args.step_id_expected,
            evidence_source_required=args.evidence_source_required,
        )
        result["approval_id"] = approval_id
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    store = _store()
    if args.approval_id:
        store.mark_approval(args.approval_id, args.status)
        print(json.dumps({"approval_id": args.approval_id, "status": args.status}, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps({"pending": store.list_pending_approvals()}, ensure_ascii=False, indent=2))
    return 0


def cmd_audit(_: argparse.Namespace) -> int:
    print(json.dumps(_store().audit_summary(), ensure_ascii=False, indent=2))
    return 0


def cmd_session_close(args: argparse.Namespace) -> int:
    summary = _store().audit_summary()
    summary["session_id"] = args.session_id
    summary["requires_human_review"] = summary["pending_approvals"] > 0
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def cmd_provider_status(_: argparse.Namespace) -> int:
    store = _store()
    registry = load_provider_registry(ROOT)
    secret_policies = load_domain_secret_policies(ROOT)
    budget_policy = load_budget_policy(ROOT)
    runtime_probe = build_runtime_probe(ROOT, source_command="proveedor_estado")
    warnings: list[dict[str, Any]] = []
    warning = _safe_store_write("save_runtime_probe", lambda: store.save_runtime_probe(runtime_probe))
    if warning:
        warnings.append(warning)
    try:
        _persist_secret_status(store, secret_policies, registry)
    except sqlite3.OperationalError as exc:
        warnings.append({"operation": "persist_secret_status", "error": f"sqlite_operational_error:{exc}"})
    budget_snapshot = build_budget_snapshot(store=store, repo_root=ROOT, budget_policy=budget_policy)
    warning = _safe_store_write("save_budget_snapshot", lambda: store.save_budget_snapshot(budget_snapshot))
    if warning:
        warnings.append(warning)
    print(
        json.dumps(
            {
                "registry": registry,
                "runtime_status": runtime_probe.payload,
                "benchmark_history": store.list_benchmark_runs(limit=5),
                "secretos": build_secret_status(secret_policies=secret_policies, provider_registry=registry),
                "presupuesto": budget_snapshot.payload,
                "warnings": warnings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_provider_benchmark(_: argparse.Namespace) -> int:
    store = _store()
    payload = run_runtime_benchmarks(ROOT)
    warnings: list[dict[str, Any]] = []
    for item in payload["results"]:
        warning = _safe_store_write(
            "save_benchmark_record",
            lambda item=item: store.save_benchmark_record(
                BenchmarkRecord(
                    benchmark_id=str(item["benchmark_id"]),
                    provider=str(item["provider"]),
                    status=str(item["status"]),
                    latency_ms=item.get("latency_ms"),
                    details=dict(item.get("details", {})),
                    created_at=str(item["created_at"]),
                )
            ),
        )
        if warning:
            warnings.append(warning)
    if warnings:
        payload["warnings"] = warnings
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * ratio))))
    return float(ordered[index])


def _http_probe(url: str, *, timeout: float = 4.0) -> tuple[str, float | None, str]:
    started = time.perf_counter()
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            _ = response.read(512)
            latency = (time.perf_counter() - started) * 1000.0
            return "ok", round(latency, 3), ""
    except error.HTTPError as exc:
        latency = (time.perf_counter() - started) * 1000.0
        return "degraded", round(latency, 3), f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        latency = (time.perf_counter() - started) * 1000.0
        return "unavailable", round(latency, 3), f"{type(exc).__name__}:{exc}"


def cmd_diagnostico_medir(args: argparse.Namespace) -> int:
    store = _store()
    payload = run_runtime_benchmarks(ROOT)
    warnings: list[dict[str, Any]] = []
    latencies: list[float] = []
    for item in payload["results"]:
        latency = item.get("latency_ms")
        if latency is not None:
            latencies.append(float(latency))
        warning = _safe_store_write(
            "save_benchmark_record",
            lambda item=item: store.save_benchmark_record(
                BenchmarkRecord(
                    benchmark_id=str(item["benchmark_id"]),
                    provider=str(item["provider"]),
                    status=str(item["status"]),
                    latency_ms=item.get("latency_ms"),
                    details=dict(item.get("details", {})),
                    created_at=str(item["created_at"]),
                )
            ),
        )
        if warning:
            warnings.append(warning)

    report = NodeBenchmarkReport(
        report_id=f"NBR-{uuid4().hex[:12]}",
        node=args.node,
        status="ok",
        p50_latency_ms=_percentile(latencies, 0.50),
        p95_latency_ms=_percentile(latencies, 0.95),
        payload=payload,
        created_at=datetime.now(UTC).isoformat(),
    )
    warning = _safe_store_write("save_node_benchmark_report", lambda: store.save_node_benchmark_report(report))
    if warning:
        warnings.append(warning)
    response = {
        "status": "ok",
        "node": args.node,
        "active_runtime": payload.get("active_runtime"),
        "recommended_runtime": payload.get("recommended_runtime"),
        "p50_latency_ms": report.p50_latency_ms,
        "p95_latency_ms": report.p95_latency_ms,
        "results": payload.get("results", []),
        "report_id": report.report_id,
        "warnings": warnings,
    }
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


def cmd_diagnostico_proveedores(_: argparse.Namespace) -> int:
    store = _store()
    providers = {
        "ollama_local": os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/tags",
        "desktop_compute": os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434").rstrip("/") + "/api/tags",
        "pc_native_llamacpp": os.getenv("OPENCLAW_DESKTOP_RUNTIME_BASE_URL", os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434")).rstrip("/") + "/health",
        "chatgpt_plus_web_assisted": "http://127.0.0.1:0/disabled",
        "openai_api": "https://api.openai.com/v1/models",
        "groq_api": "https://api.groq.com/openai/v1/models",
        "gemini_api": "https://generativelanguage.googleapis.com/v1beta/models",
        "rknn_llm_experimental": "http://127.0.0.1:0/disabled",
        "comfyui": os.getenv("OPENCLAW_COMFYUI_BASE_URL", "http://127.0.0.1:28000").rstrip("/") + "/system_stats",
        "telegram": "https://api.telegram.org",
        "matrix": os.getenv("OPENCLAW_MATRIX_HOMESERVER", "http://127.0.0.1:6167").rstrip("/") + "/_matrix/client/versions",
        "serena": os.getenv("OPENCLAW_SERENA_URL", "http://127.0.0.1:8765/mcp"),
    }
    outcomes: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for provider, url in providers.items():
        status = "unavailable"
        latency_ms: float | None = None
        error_code = ""
        if provider in {"openai_api", "groq_api", "gemini_api"}:
            env_name = {"openai_api": "OPENAI_API_KEY", "groq_api": "GROQ_API_KEY", "gemini_api": "GEMINI_API_KEY"}[provider]
            if not os.getenv(env_name, "").strip():
                status = "misconfigured"
                error_code = f"missing_{env_name.lower()}"
            else:
                status, latency_ms, error_code = _http_probe(url, timeout=4.0)
        elif provider in {"chatgpt_plus_web_assisted", "rknn_llm_experimental"}:
            status = "degraded"
            error_code = "manual_or_optional_provider"
        elif provider == "matrix" and not matrix_configured():
            status = "misconfigured"
            error_code = "matrix_not_configured"
        else:
            status, latency_ms, error_code = _http_probe(url, timeout=4.0)

        probe = ProviderProbe(
            probe_id=f"PRB-{uuid4().hex[:12]}",
            provider=provider,
            status=status,
            latency_ms=latency_ms,
            error_code=error_code,
            payload={"url": url},
            created_at=datetime.now(UTC).isoformat(),
        )
        warning = _safe_store_write("save_provider_probe", lambda probe=probe: store.save_provider_probe(probe))
        if warning:
            warnings.append(warning)
        outcomes.append(probe.to_dict())
    print(json.dumps({"status": "ok", "providers": outcomes, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


def cmd_diagnostico_internet(_: argparse.Namespace) -> int:
    checks = {
        "dns_duckduckgo": "https://duckduckgo.com/lite/",
        "ddg_html": "https://html.duckduckgo.com/html/?q=openclaw",
        "crossref": "https://api.crossref.org/works?rows=1",
        "arxiv": "https://export.arxiv.org/api/query?search_query=all:openclaw&max_results=1",
    }
    results: list[dict[str, Any]] = []
    for name, url in checks.items():
        status, latency_ms, error_code = _http_probe(url, timeout=6.0)
        results.append(
            {
                "check": name,
                "url": url,
                "status": status,
                "latency_ms": latency_ms,
                "error_code": error_code,
            }
        )
    print(json.dumps({"status": "ok", "internet": results}, ensure_ascii=False, indent=2))
    return 0


def cmd_diagnostico_calidad(args: argparse.Namespace) -> int:
    store = _store()
    traces = store.list_request_traces(limit=max(1, args.limit))
    latest = traces[0] if traces else {}
    used_sources = list((latest.get("payload") or {}).get("used_sources") or [])
    result = QualityEvalResult(
        eval_id=f"QEV-{uuid4().hex[:12]}",
        task_id=str(latest.get("task_id", "NO_TASK")),
        domain="academico",
        question=str(args.question or "diagnostico_calidad"),
        answer=str((latest.get("payload") or {}).get("response_preview", "")),
        expected_sources=[],
        used_sources=used_sources,
        supported_claims=1 if used_sources else 0,
        partially_supported_claims=0 if used_sources else 1,
        unsupported_claims=0,
        groundedness_score=1.0 if used_sources else 0.5,
        faithfulness_score=1.0 if used_sources else 0.5,
        status="ok",
        payload={"sample_trace": latest},
        created_at=datetime.now(UTC).isoformat(),
    )
    warning = _safe_store_write("save_quality_eval_result", lambda: store.save_quality_eval_result(result))
    payload: dict[str, Any] = {"status": "ok", "quality": result.to_dict()}
    if warning:
        payload["warnings"] = [warning]
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_diagnostico_reporte(args: argparse.Namespace) -> int:
    store = _store()
    traces = store.list_request_traces(limit=20)
    payload = {
        "status": "ok",
        "store": store.audit_summary(),
        "benchmarks": store.list_benchmark_runs(limit=10),
        "node_reports": store.list_node_benchmark_reports(limit=10),
        "provider_probes": store.list_provider_probes(limit=20),
        "request_traces": traces,
        "quality": store.list_quality_eval_results(limit=20),
    }
    if args.otel_jsonl:
        destination = Path(args.otel_jsonl)
        export_request_traces_to_otel_jsonl(traces, destination)
        payload["otel_export"] = {"status": "ok", "path": str(destination)}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_secrets_status(_: argparse.Namespace) -> int:
    store = _store()
    registry = load_provider_registry(ROOT)
    secret_policies = load_domain_secret_policies(ROOT)
    payload = build_secret_status(secret_policies=secret_policies, provider_registry=registry)
    _persist_secret_status(store, secret_policies, registry)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_budget_status(_: argparse.Namespace) -> int:
    store = _store()
    snapshot = build_budget_snapshot(store=store, repo_root=ROOT, budget_policy=load_budget_policy(ROOT))
    store.save_budget_snapshot(snapshot)
    print(json.dumps(snapshot.payload, ensure_ascii=False, indent=2))
    return 0


def cmd_budget_simulate(args: argparse.Namespace) -> int:
    provider_meta = _provider_meta(args.provider)
    payload = simulate_budget_request(
        store=_store(),
        repo_root=ROOT,
        budget_policy=load_budget_policy(ROOT),
        domain=args.domain,
        provider=args.provider,
        estimated_cost_usd=args.costo_estimado if args.costo_estimado is not None else float(provider_meta.get("estimated_cost_usd", 0.0)),
        estimated_tokens=args.tokens_estimados if args.tokens_estimados is not None else int(provider_meta.get("estimated_tokens", 0)),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_proposal_export(args: argparse.Namespace) -> int:
    store = _store()
    saved_task = store.get_task(args.task_id)
    if saved_task is None:
        print(json.dumps({"error": f"No existe task_id {args.task_id} en el store local."}, ensure_ascii=False, indent=2))
        return 1

    evidence = store.get_latest_evidence_for_task(args.task_id)
    if evidence is None:
        print(json.dumps({"error": f"No existe evidencia para {args.task_id}."}, ensure_ascii=False, indent=2))
        return 1

    approval = store.get_latest_approval_for_task(args.task_id) or {
        "status": "not_required",
        "diff_summary": "",
        "affected_targets": [],
        "step_id_expected": "",
        "evidence_source_required": False,
    }

    academic_packet = store.get_latest_academic_packet_for_task(args.task_id)
    academic_payload = _build_academic_payload(academic_packet, saved_task)
    task_payload = dict(saved_task["payload"])
    task_payload["proposal_id"] = args.proposal_id or ""
    decision_payload = dict(saved_task["decision"])
    evidence_payload = dict(evidence)
    approval_payload = dict(approval)

    if args.dry_run:
        event = {
            "event_type": "openclaw_proposal",
            "session_id": args.session_id,
            "linked_reference": args.linked_reference,
            "payload": {
                "proposal_id": task_payload.get("proposal_id") or f"OCP-{args.task_id}",
                "task_id": task_payload.get("task_id", ""),
                "title": task_payload.get("title", ""),
                "domain": task_payload.get("domain", ""),
                "objective": task_payload.get("objective", ""),
                "decision": decision_payload,
                "evidence": evidence_payload,
                "approval": approval_payload,
                "academic_mode": academic_payload.get("academic_mode", ""),
                "target_artifacts": academic_payload.get("target_artifacts", []),
                "scientific_support_summary": academic_payload.get("scientific_support_summary", ""),
                "academic_packet": academic_payload.get("academic_packet", {}),
                "proposal_status": "draft_pending_human_review",
            },
        }
        print(json.dumps({"event": event}, ensure_ascii=False, indent=2))
        return 0

    event = append_openclaw_proposal(
        task_payload=task_payload,
        decision_payload=decision_payload,
        evidence_payload=evidence_payload,
        approval_payload=approval_payload,
        academic_payload=academic_payload,
        session_id=args.session_id,
        linked_reference=args.linked_reference,
    )
    print(
        json.dumps(
            {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "proposal_status": event["payload"]["proposal_status"],
                "proposal_id": event["payload"]["proposal_id"],
                "academic_mode": event["payload"].get("academic_mode", ""),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_proposal_prepare_validation(args: argparse.Namespace) -> int:
    store = _store()
    saved_task = store.get_task(args.task_id)
    if saved_task is None:
        print(json.dumps({"error": f"No existe task_id {args.task_id} en el store local."}, ensure_ascii=False, indent=2))
        return 1

    approval = store.get_latest_approval_for_task(args.task_id) or {}
    step_id = str(approval.get("step_id_expected", "")).strip() or _suggest_step_id()
    proposal_event_id = args.proposal_event_id or "EVT-PENDING-EXPORT"
    proposal_id = args.proposal_id or f"OCP-{args.task_id}"
    title = str(saved_task["payload"].get("title", args.task_id))
    question = (
        f"¿Autorizas aprobar la propuesta OpenClaw {proposal_id} "
        f"para `{title}` y registrarla como {step_id}?"
    )
    package = {
        "proposal_event_id": proposal_event_id,
        "proposal_id": proposal_id,
        "task_id": args.task_id,
        "session_id": args.session_id,
        "step_id": step_id,
        "critical_question": question,
        "commands": {
            "scaffold": f"python 07_scripts/tesis.py source scaffold --session-id {args.session_id}",
            "register_template": (
                "python 07_scripts/tesis.py source register "
                f"--session-id {args.session_id} "
                "--transcript <RUTA_TRANSCRIPCION> "
                "--quote \"<CONFIRMACION_EXACTA>\""
            ),
            "finalize": (
                "python 07_scripts/tesis.py proposal finalize-openclaw "
                f"--proposal-event-id {proposal_event_id} "
                "--source-event-id EVT-XXXX "
                f"--step-id {step_id} "
                f"--session-id {args.session_id} "
                "--confirmation-text \"<CONFIRMACION_EXACTA>\""
            ),
        },
        "technical_requirements": [
            "La confirmación debe ser texto humano exacto.",
            "Debe existir source_event_id con quoted_text igual a la confirmación.",
            "El VAL-STEP solo se registra después de corroborar transcript_path y hashes.",
        ],
        "linked_reference": args.linked_reference,
        "comandos_openclaw": {
            "exportar_propuesta": (
                f"python runtime/openclaw/bin/openclaw_local.py propuesta exportar --id-tarea {args.task_id} --id-sesion {args.session_id}"
            ),
        },
    }
    print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


def cmd_gateway_serve(args: argparse.Namespace) -> int:
    store = _store()
    runtime_status = probe_runtime_status(ROOT)
    notification = dispatch_ready_notification(host=args.host, port=args.port, runtime_status=runtime_status)
    if notification["status"] == "sent":
        print("OPENCLAW_NOTIFY: telegram_sent")
    elif notification["status"] == "error":
        print(f"OPENCLAW_NOTIFY: telegram_error:{notification.get('detail', 'unknown')}")
    registry = load_provider_registry(ROOT)
    secret_policies = load_domain_secret_policies(ROOT)
    budget_snapshot = build_budget_snapshot(store=store, repo_root=ROOT, budget_policy=load_budget_policy(ROOT))
    serve_workspace(
        args.host,
        args.port,
        store.audit_summary(),
        registry,
        repo_root=ROOT,
        store=store,
        academic_packets=store.list_academic_packets(),
        approvals=store.list_pending_approvals(),
        runtime_status=runtime_status,
        preflight=build_preflight_report(ROOT),
        secret_status=build_secret_status(secret_policies=secret_policies, provider_registry=registry),
        budget_status=budget_snapshot.payload,
        billing_history=store.list_billing_records(limit=10),
    )
    return 0


def cmd_gateway_status(_: argparse.Namespace) -> int:
    runtime_probe = build_runtime_probe(ROOT, source_command="pasarela_estado")
    store = _store()
    store.save_runtime_probe(runtime_probe)
    budget_snapshot = build_budget_snapshot(store=store, repo_root=ROOT, budget_policy=load_budget_policy(ROOT))
    store.save_budget_snapshot(budget_snapshot)
    print(
        json.dumps(
            {
                "status": "ok",
                "deployment_state": runtime_probe.system_state,
                "web_enabled": True,
                "web_stack": web_stack_name(),
                "data_dir": str(default_data_dir(ROOT)),
                "repo_root": str(ROOT),
                "nodes": build_nodes_summary(ROOT),
                "providers": build_provider_summary(ROOT),
                "runtime_status": runtime_probe.payload,
                "preflight": build_preflight_report(ROOT),
                "presupuesto": budget_snapshot.payload,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_gateway_preflight(_: argparse.Namespace) -> int:
    report = build_preflight_report(ROOT)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 1


def cmd_gateway_notify_ready(args: argparse.Namespace) -> int:
    payload = dispatch_test_notification(message=args.mensaje)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload["status"] == "sent":
        return 0
    if payload["status"] == "skipped" and not args.obligatorio:
        return 0
    return 1


def cmd_telegram_status(_: argparse.Namespace) -> int:
    store = _store()
    payload = {
        "status": "ok" if telegram_configured() else "not_configured",
        "configured": telegram_configured(),
        "events": store.list_telegram_events(limit=10),
        "store": store.audit_summary(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["configured"] else 1


def cmd_telegram_process(args: argparse.Namespace) -> int:
    store = _store()
    update = {
        "update_id": args.update_id,
        "message": {
            "message_id": args.update_id,
            "chat": {"id": args.chat_id, "type": "private"},
            "text": args.text,
        },
    }
    payload = handle_update(update, repo_root=ROOT, store=store)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") not in {"model_error", "error"} else 1


def cmd_telegram_polling(args: argparse.Namespace) -> int:
    store = _store()
    if args.once:
        payload = poll_once(repo_root=ROOT, store=store, timeout_seconds=args.timeout, limit=args.limit)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    run_polling_loop(repo_root=ROOT, store=store, interval_seconds=args.interval, timeout_seconds=args.timeout)
    return 0


def cmd_telegram_reply(args: argparse.Namespace) -> int:
    store = _store()
    payload = dispatch_command(args.command, args.text, repo_root=ROOT, store=store, chat_id=args.chat_id)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") not in {"model_error", "error"} else 1


def cmd_matrix_status(_: argparse.Namespace) -> int:
    store = _store()
    payload = {
        "status": "ok" if matrix_configured() else "not_configured",
        "configured": matrix_configured(),
        "sessions": store.list_sessions(channel="matrix", limit=20),
        "store": store.audit_summary(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["configured"] else 1


def cmd_matrix_process(args: argparse.Namespace) -> int:
    store = _store()
    event = {
        "type": "m.room.message",
        "sender": args.sender,
        "content": {"body": args.text},
    }
    payload = process_matrix_event(event, room_id=args.room_id, repo_root=ROOT, store=store)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") not in {"error"} else 1


def cmd_matrix_polling(args: argparse.Namespace) -> int:
    store = _store()
    if args.once:
        payload = poll_matrix_once(repo_root=ROOT, store=store)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("status") in {"ok", "skipped"} else 1
    run_matrix_loop(repo_root=ROOT, store=store, interval_seconds=args.interval)
    return 0


def cmd_image_generate(args: argparse.Namespace) -> int:
    payload = generate_image_from_prompt(args.prompt, timeout_seconds=args.timeout)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {"ok", "queued"} else 1


def cmd_academic_literature(args: argparse.Namespace) -> int:
    return _handle_academic_mode(args, mode="estado_del_arte")


def cmd_academic_methodology(args: argparse.Namespace) -> int:
    return _handle_academic_mode(args, mode="metodologia")


def cmd_academic_writing(args: argparse.Namespace) -> int:
    return _handle_academic_mode(args, mode="redaccion_tesis")


def cmd_academic_export_proposal(args: argparse.Namespace) -> int:
    args.linked_reference = getattr(args, "linked_reference", "[DEC-0020]")
    return cmd_proposal_export(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openclaw-local")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)

    task = subparsers.add_parser("tarea", aliases=["task"])
    task_sub = task.add_subparsers(dest="task_command", required=True)
    task_new = _add_task_arguments(task_sub.add_parser("nueva", aliases=["new"]))
    task_new.set_defaults(func=cmd_task_new)
    task_route = _add_task_arguments(task_sub.add_parser("enrutar", aliases=["route"]))
    task_route.set_defaults(func=cmd_task_route)

    run_parser = _add_task_arguments(subparsers.add_parser("ejecutar", aliases=["run"]))
    run_parser.add_argument("--simulacion", "--dry-run", dest="dry_run", action="store_true", default=False)
    run_parser.add_argument("--indicacion", "--prompt", dest="prompt", default="simulacion")
    run_parser.add_argument("--id-sesion", "--session-id", dest="session_id", default=os.getenv("OPENCLAW_SESSION_ID", "SESSION-LOCAL"))
    run_parser.add_argument("--resumen-diff", "--diff-summary", dest="diff_summary", default="")
    run_parser.add_argument("--step-id-esperado", "--step-id-expected", dest="step_id_expected", default="VAL-STEP-PENDING")
    run_parser.add_argument("--requiere-evidencia-fuente", "--evidence-source-required", dest="evidence_source_required", action="store_true", default=False)
    run_parser.set_defaults(func=cmd_run)

    approve = subparsers.add_parser("aprobar", aliases=["approve"])
    approve.add_argument("--id-aprobacion", "--approval-id", dest="approval_id")
    approve.add_argument("--estado", "--status", dest="status", default="approved")
    approve.set_defaults(func=cmd_approve)

    image = subparsers.add_parser("imagen", aliases=["image"])
    image_sub = image.add_subparsers(dest="image_command", required=True)
    image_generate = image_sub.add_parser("generar", aliases=["generate"])
    image_generate.add_argument("--prompt", required=True)
    image_generate.add_argument("--timeout", type=int, default=120)
    image_generate.set_defaults(func=cmd_image_generate)

    audit = subparsers.add_parser("auditar", aliases=["audit"])
    audit.set_defaults(func=cmd_audit)

    session = subparsers.add_parser("sesion", aliases=["session"])
    session_sub = session.add_subparsers(dest="session_command", required=True)
    session_close = session_sub.add_parser("cerrar", aliases=["close"])
    session_close.add_argument("--id-sesion", "--session-id", dest="session_id", default=os.getenv("OPENCLAW_SESSION_ID", "SESSION-LOCAL"))
    session_close.set_defaults(func=cmd_session_close)

    provider = subparsers.add_parser("proveedor", aliases=["provider"])
    provider_sub = provider.add_subparsers(dest="provider_command", required=True)
    provider_status = provider_sub.add_parser("estado", aliases=["status"])
    provider_status.set_defaults(func=cmd_provider_status)
    provider_benchmark = provider_sub.add_parser("medir", aliases=["benchmark"])
    provider_benchmark.set_defaults(func=cmd_provider_benchmark)

    diagnostico = subparsers.add_parser("diagnostico", aliases=["diag"])
    diagnostico_sub = diagnostico.add_subparsers(dest="diagnostico_command", required=True)
    diagnostico_medir = diagnostico_sub.add_parser("medir")
    diagnostico_medir.add_argument("--node", default=os.getenv("OPENCLAW_NODE_NAME", "edge"))
    diagnostico_medir.set_defaults(func=cmd_diagnostico_medir)
    diagnostico_proveedores = diagnostico_sub.add_parser("proveedores")
    diagnostico_proveedores.set_defaults(func=cmd_diagnostico_proveedores)
    diagnostico_internet = diagnostico_sub.add_parser("internet")
    diagnostico_internet.set_defaults(func=cmd_diagnostico_internet)
    diagnostico_calidad = diagnostico_sub.add_parser("calidad")
    diagnostico_calidad.add_argument("--pregunta", "--question", dest="question", default="")
    diagnostico_calidad.add_argument("--limit", dest="limit", type=int, default=20)
    diagnostico_calidad.set_defaults(func=cmd_diagnostico_calidad)
    diagnostico_reporte = diagnostico_sub.add_parser("reporte")
    diagnostico_reporte.add_argument("--json", dest="json", action="store_true", default=False)
    diagnostico_reporte.add_argument("--otel-jsonl", dest="otel_jsonl", default="")
    diagnostico_reporte.set_defaults(func=cmd_diagnostico_reporte)

    secrets = subparsers.add_parser("secretos", aliases=["secrets"])
    secrets_sub = secrets.add_subparsers(dest="secrets_command", required=True)
    secrets_status = secrets_sub.add_parser("estado", aliases=["status"])
    secrets_status.set_defaults(func=cmd_secrets_status)

    budget = subparsers.add_parser("presupuesto", aliases=["budget"])
    budget_sub = budget.add_subparsers(dest="budget_command", required=True)
    budget_status = budget_sub.add_parser("estado", aliases=["status"])
    budget_status.set_defaults(func=cmd_budget_status)
    budget_simulate = budget_sub.add_parser("simular", aliases=["simulate"])
    budget_simulate.add_argument("--dominio", "--domain", dest="domain", required=True, choices=["personal", "profesional", "academico", "edge", "administrativo"])
    budget_simulate.add_argument("--proveedor", "--provider", dest="provider", required=True)
    budget_simulate.add_argument("--costo-estimado", dest="costo_estimado", type=float)
    budget_simulate.add_argument("--tokens-estimados", dest="tokens_estimados", type=int)
    budget_simulate.set_defaults(func=cmd_budget_simulate)

    proposal = subparsers.add_parser("propuesta", aliases=["proposal"])
    proposal_sub = proposal.add_subparsers(dest="proposal_command", required=True)
    proposal_export = proposal_sub.add_parser("exportar", aliases=["export"])
    proposal_export.add_argument("--id-tarea", "--task-id", dest="task_id", required=True)
    proposal_export.add_argument("--id-sesion", "--session-id", dest="session_id", default=os.getenv("OPENCLAW_SESSION_ID", "SESSION-LOCAL"))
    proposal_export.add_argument("--referencia-vinculada", "--linked-reference", dest="linked_reference", default="[DEC-0020]")
    proposal_export.add_argument("--id-propuesta", "--proposal-id", dest="proposal_id", default="")
    proposal_export.add_argument("--simulacion", "--dry-run", dest="dry_run", action="store_true", default=False)
    proposal_export.set_defaults(func=cmd_proposal_export)
    proposal_prepare = proposal_sub.add_parser("preparar-validacion", aliases=["prepare-validation"])
    proposal_prepare.add_argument("--id-tarea", "--task-id", dest="task_id", required=True)
    proposal_prepare.add_argument("--id-sesion", "--session-id", dest="session_id", required=True)
    proposal_prepare.add_argument("--referencia-vinculada", "--linked-reference", dest="linked_reference", default="[DEC-0020]")
    proposal_prepare.add_argument("--id-evento-propuesta", "--proposal-event-id", dest="proposal_event_id", default="")
    proposal_prepare.add_argument("--id-propuesta", "--proposal-id", dest="proposal_id", default="")
    proposal_prepare.set_defaults(func=cmd_proposal_prepare_validation)

    academic = subparsers.add_parser("academico", aliases=["academic"])
    academic_sub = academic.add_subparsers(dest="academic_command", required=True)
    literature = _add_academic_arguments(academic_sub.add_parser("estado-del-arte", aliases=["literature"]), mode="estado_del_arte")
    literature.set_defaults(func=cmd_academic_literature)
    methodology = _add_academic_arguments(academic_sub.add_parser("metodologia", aliases=["methodology"]), mode="metodologia")
    methodology.set_defaults(func=cmd_academic_methodology)
    writing = _add_academic_arguments(academic_sub.add_parser("redaccion", aliases=["writing"]), mode="redaccion_tesis")
    writing.set_defaults(func=cmd_academic_writing)
    academic_export = academic_sub.add_parser("exportar-propuesta", aliases=["export-proposal"])
    academic_export.add_argument("--id-tarea", "--task-id", dest="task_id", required=True)
    academic_export.add_argument("--id-sesion", "--session-id", dest="session_id", default=os.getenv("OPENCLAW_SESSION_ID", "SESSION-LOCAL"))
    academic_export.add_argument("--referencia-vinculada", "--linked-reference", dest="linked_reference", default="[DEC-0020]")
    academic_export.add_argument("--id-propuesta", "--proposal-id", dest="proposal_id", default="")
    academic_export.add_argument("--simulacion", "--dry-run", dest="dry_run", action="store_true", default=False)
    academic_export.set_defaults(func=cmd_academic_export_proposal)

    gateway = subparsers.add_parser("pasarela", aliases=["gateway"])
    gateway_sub = gateway.add_subparsers(dest="gateway_command", required=True)
    gateway_serve = gateway_sub.add_parser("servir", aliases=["serve"])
    gateway_serve.add_argument("--host", default=os.getenv("OPENCLAW_HOST", "127.0.0.1"))
    gateway_serve.add_argument("--puerto", "--port", dest="port", type=int, default=int(os.getenv("OPENCLAW_PORT", "18789")))
    gateway_serve.set_defaults(func=cmd_gateway_serve)
    gateway_status = gateway_sub.add_parser("estado", aliases=["status"])
    gateway_status.set_defaults(func=cmd_gateway_status)
    gateway_preflight = gateway_sub.add_parser("preflight")
    gateway_preflight.set_defaults(func=cmd_gateway_preflight)
    gateway_notify = gateway_sub.add_parser("notificar-listo", aliases=["notify-ready"])
    gateway_notify.add_argument("--mensaje", dest="mensaje", default="OpenClaw listo para ordenes.")
    gateway_notify.add_argument("--obligatorio", dest="obligatorio", action="store_true", default=False)
    gateway_notify.set_defaults(func=cmd_gateway_notify_ready)

    web_session = subparsers.add_parser("sesion-web", aliases=["web-session"])
    web_session_sub = web_session.add_subparsers(dest="web_session_command", required=True)
    web_session_status = web_session_sub.add_parser("estado", aliases=["status"])
    web_session_status.set_defaults(func=cmd_web_session_status)
    web_session_login = web_session_sub.add_parser("login")
    web_session_login.add_argument("--timeout", dest="timeout", type=int, default=int(os.getenv("OPENCLAW_WEB_SESSION_LOGIN_TIMEOUT_SECONDS", "900")))
    web_session_login.set_defaults(func=cmd_web_session_login)

    telegram = subparsers.add_parser("telegram")
    telegram_sub = telegram.add_subparsers(dest="telegram_command", required=True)
    telegram_status = telegram_sub.add_parser("estado", aliases=["status"])
    telegram_status.set_defaults(func=cmd_telegram_status)
    telegram_process = telegram_sub.add_parser("procesar", aliases=["process"])
    telegram_process.add_argument("--chat-id", dest="chat_id", required=True)
    telegram_process.add_argument("--texto", "--text", dest="text", required=True)
    telegram_process.add_argument("--update-id", dest="update_id", type=int, default=1)
    telegram_process.set_defaults(func=cmd_telegram_process)
    telegram_reply = telegram_sub.add_parser("responder", aliases=["reply"])
    telegram_reply.add_argument("--comando", "--command", dest="command", required=True)
    telegram_reply.add_argument("--texto", "--text", dest="text", default="")
    telegram_reply.add_argument("--chat-id", dest="chat_id", default="cli")
    telegram_reply.set_defaults(func=cmd_telegram_reply)
    telegram_polling = telegram_sub.add_parser("polling")
    telegram_polling.add_argument("--once", dest="once", action="store_true", default=False)
    telegram_polling.add_argument("--timeout", dest="timeout", type=int, default=int(os.getenv("OPENCLAW_TELEGRAM_POLL_TIMEOUT_SECONDS", "20")))
    telegram_polling.add_argument("--interval", dest="interval", type=int, default=int(os.getenv("OPENCLAW_TELEGRAM_POLL_INTERVAL_SECONDS", "2")))
    telegram_polling.add_argument("--limit", dest="limit", type=int, default=int(os.getenv("OPENCLAW_TELEGRAM_POLL_LIMIT", "10")))
    telegram_polling.set_defaults(func=cmd_telegram_polling)

    matrix = subparsers.add_parser("matrix")
    matrix_sub = matrix.add_subparsers(dest="matrix_command", required=True)
    matrix_status = matrix_sub.add_parser("estado", aliases=["status"])
    matrix_status.set_defaults(func=cmd_matrix_status)
    matrix_process = matrix_sub.add_parser("procesar", aliases=["process"])
    matrix_process.add_argument("--room-id", dest="room_id", required=True)
    matrix_process.add_argument("--sender", dest="sender", default="@tester:local")
    matrix_process.add_argument("--texto", "--text", dest="text", required=True)
    matrix_process.set_defaults(func=cmd_matrix_process)
    matrix_polling = matrix_sub.add_parser("polling")
    matrix_polling.add_argument("--once", dest="once", action="store_true", default=False)
    matrix_polling.add_argument("--interval", dest="interval", type=int, default=int(os.getenv("OPENCLAW_MATRIX_POLL_INTERVAL_SECONDS", "2")))
    matrix_polling.set_defaults(func=cmd_matrix_polling)

    return parser


def _add_task_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--id-tarea", "--task-id", dest="task_id", required=True)
    parser.add_argument("--titulo", "--title", dest="title", required=True)
    parser.add_argument("--dominio", "--domain", dest="domain", required=True, choices=["personal", "profesional", "academico", "edge", "administrativo"])
    parser.add_argument("--objetivo", "--objective", dest="objective", required=True)
    parser.add_argument("--complejidad", "--complexity", dest="complexity", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--nivel-riesgo", "--risk-level", dest="risk_level", default="medium", choices=["low", "medium", "high", "critical"])
    parser.add_argument("--modo-preferido", "--preferred-mode", dest="preferred_mode", default="auto", choices=["auto", "offline"])
    parser.add_argument("--rutas-objetivo", "--target-paths", dest="target_paths", nargs="*", default=[])
    parser.add_argument("--muta-estado", "--mutates-state", dest="mutates_state", action="store_true", default=False)
    parser.add_argument("--requiere-citas", "--requires-citations", dest="requires_citations", action="store_true", default=False)
    parser.add_argument("--modo-serena", "--serena-mode", dest="serena_mode", default="auto", choices=["auto", "required", "off"])
    return parser


def _add_academic_arguments(parser: argparse.ArgumentParser, *, mode: str) -> argparse.ArgumentParser:
    parser.add_argument("--id-tarea", "--task-id", dest="task_id", required=True)
    parser.add_argument("--titulo", "--title", dest="title", required=True)
    parser.add_argument("--objetivo", "--objective", dest="objective", required=True)
    parser.add_argument("--pregunta", "--question", dest="question", required=True)
    parser.add_argument("--alcance", "--scope", dest="scope", required=True)
    parser.add_argument("--archivo-entrada-json", "--input-json", dest="input_json", required=True)
    parser.add_argument("--id-sesion", "--session-id", dest="session_id", default=os.getenv("OPENCLAW_SESSION_ID", "SESSION-LOCAL"))
    parser.add_argument("--complejidad", "--complexity", dest="complexity", default="high", choices=["low", "medium", "high"])
    parser.add_argument("--nivel-riesgo", "--risk-level", dest="risk_level", default="medium", choices=["low", "medium", "high", "critical"])
    parser.add_argument("--modo-preferido", "--preferred-mode", dest="preferred_mode", default="auto", choices=["auto", "offline"])
    parser.add_argument("--id-propuesta", "--proposal-id", dest="proposal_id", default="")
    parser.add_argument("--referencia-vinculada", "--linked-reference", dest="linked_reference", default="[DEC-0020]")
    parser.add_argument("--step-id-esperado", "--step-id-expected", dest="step_id_expected", default="VAL-STEP-PENDING")
    parser.add_argument("--escribir-artefactos", "--write-artifacts", dest="write_artifacts", action="store_true", default=False)
    parser.add_argument("--cambia-metodologia", "--changes-methodology", dest="changes_methodology", action="store_true", default=False)
    parser.add_argument("--modo-serena", "--serena-mode", dest="serena_mode", default="auto", choices=["auto", "required", "off"])
    parser.add_argument("--prefer-chatgpt-plus", dest="prefer_chatgpt_plus", action="store_true", default=False)
    parser.set_defaults(domain="academico", requires_citations=True, mutates_state=False, academic_mode=mode)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _suggest_step_id() -> str:
    events = load_events()
    numeric_values: list[int] = []
    for event in events:
        event_id = str(event.get("event_id", ""))
        if event_id.startswith("VAL-STEP-"):
            suffix = event_id[len("VAL-STEP-") :]
            if suffix.isdigit():
                numeric_values.append(int(suffix))
    next_value = (max(numeric_values) + 1) if numeric_values else 1
    return f"VAL-STEP-{next_value}"


def _load_json_input(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_academic_payload(academic_packet: dict[str, Any] | None, saved_task: dict[str, Any]) -> dict[str, Any]:
    if not academic_packet:
        return {
            "academic_mode": str(saved_task["payload"].get("extra_context", {}).get("academic_mode", "")),
            "target_artifacts": list(saved_task["payload"].get("target_paths", [])),
            "scientific_support_summary": "",
            "academic_packet": {},
        }
    return {
        "academic_mode": academic_packet.get("mode", ""),
        "target_artifacts": list(academic_packet.get("outputs", [])),
        "scientific_support_summary": academic_packet.get("summary", ""),
        "academic_packet": academic_packet,
    }


def _build_claim_records(items: list[dict[str, Any]]) -> list[ClaimRecord]:
    return [
        ClaimRecord(
            claim_id=str(item["claim_id"]),
            claim_text=str(item["claim_text"]),
            classification=str(item["classification"]),
            source_refs=[str(ref) for ref in item.get("source_refs", [])],
            confidence=str(item.get("confidence", "medio")),
            verification_status=str(item.get("verification_status", "pendiente_de_validacion")),
            impact_on_thesis=str(item.get("impact_on_thesis", "sin especificar")),
        )
        for item in items
    ]


def _build_literature_records(items: list[dict[str, Any]]) -> list[LiteratureRecord]:
    return [
        LiteratureRecord(
            record_id=str(item["record_id"]),
            tema=str(item["tema"]),
            pregunta=str(item["pregunta"]),
            fuente=str(item["fuente"]),
            anio=str(item["anio"]),
            doi=str(item.get("doi", "")),
            nivel_evidencia=str(item["nivel_evidencia"]),
            hallazgos_clave=[str(value) for value in item.get("hallazgos_clave", [])],
            contradicciones=[str(value) for value in item.get("contradicciones", [])],
            relacion_con_hipotesis=str(item["relacion_con_hipotesis"]),
            estado_verificacion=str(item["estado_verificacion"]),
        )
        for item in items
    ]


def _build_writing_draft(payload: dict[str, Any]) -> WritingDraft | None:
    writing = payload.get("writing_draft")
    if not writing:
        return None
    paragraphs = writing.get("paragraphs", [])
    markdown_body = "\n\n".join(_render_markdown_paragraph(item) for item in paragraphs)
    latex_body = "\n\n".join(_render_latex_paragraph(item) for item in paragraphs)
    return WritingDraft(
        section_id=str(writing["section_id"]),
        purpose=str(writing["purpose"]),
        source_refs=[str(ref) for ref in writing.get("source_refs", [])],
        open_questions=[str(item) for item in writing.get("open_questions", [])],
        markdown_body=markdown_body,
        latex_body=latex_body,
    )


def _render_markdown_paragraph(item: dict[str, Any]) -> str:
    text = str(item["text"]).strip()
    refs = [str(ref) for ref in item.get("source_refs", [])]
    if refs:
        return f"{text}\n\nFuentes: {', '.join(refs)}"
    if item.get("non_factual"):
        return f"{text}\n\nEstado: sintesis no factual"
    return f"{text}\n\nEstado: pendiente_de_respaldo"


def _render_latex_paragraph(item: dict[str, Any]) -> str:
    text = _escape_latex(str(item["text"]).strip())
    refs = [str(ref) for ref in item.get("source_refs", [])]
    if refs:
        suffix = "\\\n\\textit{Fuentes: " + ", ".join(_escape_latex(ref) for ref in refs) + "}."
        return text + suffix
    if item.get("non_factual"):
        return text + "\\\n\\textit{Sintesis no factual.}"
    return text + "\\\n\\textbf{Pendiente de respaldo.}"


def _escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def _handle_academic_mode(args: argparse.Namespace, *, mode: str) -> int:
    payload = _load_json_input(args.input_json)
    claims = _build_claim_records(payload.get("claims", []))
    literature_records = _build_literature_records(payload.get("literature_records", []))
    writing_draft = _build_writing_draft(payload)
    target_paths = _academic_target_paths(mode, writing_draft)
    extra_context = {
        "academic_mode": mode,
        "traceability_links": payload.get("traceability_links", []),
        "changes_methodology": bool(args.changes_methodology),
    }
    if getattr(args, "prefer_chatgpt_plus", False):
        extra_context["prefer_chatgpt_plus"] = True
        extra_context["preferred_web_assisted"] = "chatgpt_plus_web_assisted"
    task = TaskEnvelope(
        task_id=args.task_id,
        title=args.title,
        domain="academico",
        objective=args.objective,
        complexity=args.complexity,
        risk_level=args.risk_level,
        mutates_state=False,
        target_paths=target_paths,
        requires_citations=True,
        preferred_mode=args.preferred_mode,
        session_id=args.session_id,
        extra_context=extra_context,
    )
    store = _store()
    decision = route_task(task, load_domain_policies(ROOT), repo_root=ROOT, store=store)
    serena, error = _collect_serena_context(
        task,
        mode=_resolve_serena_mode(args),
        dry_run=not args.write_artifacts,
        write_artifacts=args.write_artifacts,
        intent=args.objective,
    )
    if error:
        print(json.dumps({"error": error, "task": task.to_dict(), "decision": decision.to_dict(), "serena": serena}, ensure_ascii=False, indent=2))
        return 1
    store.save_task(task, decision)
    _save_resolution_for_decision(store, task.domain, decision.provider)

    packet = build_academic_packet(
        task=task,
        question=args.question,
        scope=args.scope,
        sources=[str(item) for item in payload.get("sources", [])],
        claims=claims,
        literature_records=literature_records,
        traceability_links=[str(item) for item in payload.get("traceability_links", [])],
        writing_draft=writing_draft,
        summary=str(payload.get("summary", "")),
    )
    artifacts = render_academic_artifacts(packet)
    context_hash = _context_hash(payload)
    cached = store.get_cached_context(context_hash)
    if cached is None:
        store.cache_context(context_hash, {"task_id": task.task_id, "mode": mode, "artifacts": list(artifacts.keys())})
    evidence = build_evidence_record(
        task=task,
        decision=decision,
        prompt=args.question,
        response=packet.summary,
        context={
            "mode": mode,
            "scope": args.scope,
            "cache_key": context_hash,
            "claims": [item.to_dict() for item in claims],
            "literature_records": [item.to_dict() for item in literature_records],
            "artifacts": list(artifacts.keys()),
            "serena": serena,
        },
        estimated_cost=decision.estimated_cost,
        source_links=packet.sources,
        session_id=args.session_id,
    )
    store.save_evidence(evidence)
    store.save_academic_packet(packet, evidence.payload_hash)
    store.save_billing_record(
        build_billing_record(
            task_id=task.task_id,
            session_id=args.session_id,
            domain=task.domain,
            provider=decision.provider,
            billing_mode=decision.billing_mode,
            estimated_tokens=decision.estimated_tokens,
            estimated_cost_usd=decision.estimated_cost,
        )
    )

    approval_id = None
    if decision.requires_human_gate or mode != "estado_del_arte":
        approval_id = store.create_approval_request(
            task=task,
            decision=decision,
            diff_summary=_annotate_diff_summary(_approval_summary(mode, packet), serena),
            affected_targets=task.target_paths,
            step_id_expected=args.step_id_expected,
            evidence_source_required=True,
        )

    written_paths: list[str] = []
    if args.write_artifacts:
        written_paths = _materialize_artifacts(artifacts)

    result = {
        "task": task.to_dict(),
        "decision": decision.to_dict(),
        "packet_id": packet.packet_id,
        "evidence_id": evidence.evidence_id,
        "cache_key": context_hash,
        "cache_hit": cached is not None,
        "approval_id": approval_id,
        "artifacts": list(artifacts.keys()),
        "written_artifacts": written_paths,
        "summary": packet.summary,
        "serena": serena,
        "proposal_export_command": (
            f"python runtime/openclaw/bin/openclaw_local.py academico exportar-propuesta --id-tarea {task.task_id} --id-sesion {args.session_id}"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _approval_summary(mode: str, packet: Any) -> str:
    if mode == "metodologia":
        return f"Revisar propuesta metodológica: {packet.summary}"
    if mode == "redaccion_tesis":
        return f"Revisar borrador de redacción y fragmento LaTeX: {packet.summary}"
    return f"Revisar propuesta académica: {packet.summary}"


def _academic_target_paths(mode: str, writing_draft: WritingDraft | None) -> list[str]:
    if mode == "redaccion_tesis":
        if writing_draft is None:
            return []
        return [
            f"runtime/openclaw/state/academico/drafts/{writing_draft.section_id}.md",
            f"05_tesis_latex/sections/{writing_draft.section_id}.tex",
        ]
    return list(ACADEMIC_CANONICAL_TARGETS.get(mode, []))


def _materialize_artifacts(artifacts: dict[str, str]) -> list[str]:
    written: list[str] = []
    for rel_path, content in artifacts.items():
        target = ROOT / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
        written.append(rel_path)
    return written


def _context_hash(payload: dict[str, Any]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    import hashlib

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def _persist_secret_status(store: OpenClawStore, secret_policies: dict[str, Any], registry: dict[str, Any]) -> None:
    for domain, payload in build_secret_status(secret_policies=secret_policies, provider_registry=registry)["domains"].items():
        for provider_id in payload["providers"].keys():
            store.save_secret_resolution(resolve_provider_secret(domain, provider_id, secret_policies=secret_policies))


def _save_resolution_for_decision(store: OpenClawStore, domain: str, provider: str) -> None:
    secret_policies = load_domain_secret_policies(ROOT)
    store.save_secret_resolution(resolve_provider_secret(domain, provider, secret_policies=secret_policies))


def _provider_meta(provider_id: str) -> dict[str, Any]:
    registry = load_provider_registry(ROOT)
    for item in registry.get("providers", []):
        if str(item["id"]) == provider_id:
            return dict(item)
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
