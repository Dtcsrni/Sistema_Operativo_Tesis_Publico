from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def request_trace_to_otel_event(trace: dict[str, Any]) -> dict[str, Any]:
    payload = dict(trace.get("payload") or {})
    return {
        "name": "gen_ai.request",
        "attributes": {
            "gen_ai.operation.name": "chat.completions",
            "gen_ai.request.model": str(trace.get("selected_model", "")),
            "gen_ai.response.model": str(trace.get("selected_model", "")),
            "gen_ai.system": str(trace.get("selected_provider", "")),
            "gen_ai.input_tokens": int(trace.get("prompt_tokens_est", 0) or 0),
            "gen_ai.output_tokens": int(payload.get("output_tokens", 0) or 0),
            "gen_ai.latency.ms": float(trace.get("total_ms", 0.0) or 0.0),
            "openclaw.trace_id": str(trace.get("trace_id", "")),
            "openclaw.task_id": str(trace.get("task_id", "")),
            "openclaw.fallback_reason": str(trace.get("fallback_reason", "")),
        },
        "body": {
            "request_kind": trace.get("request_kind", ""),
            "complexity": trace.get("complexity", ""),
            "metrics": {
                "parse_ms": trace.get("parse_ms"),
                "profile_ms": trace.get("profile_ms"),
                "semantic_ms": trace.get("semantic_ms"),
                "routing_ms": trace.get("routing_ms"),
                "web_search_ms": trace.get("web_search_ms"),
                "provider_ms": trace.get("provider_ms"),
                "delivery_ms": trace.get("delivery_ms"),
                "total_ms": trace.get("total_ms"),
            },
        },
    }


def export_request_traces_to_otel_jsonl(traces: list[dict[str, Any]], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(request_trace_to_otel_event(trace), ensure_ascii=False) for trace in traces]
    destination.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return destination
