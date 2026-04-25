from __future__ import annotations

import difflib
import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import ab_pilot
import common
from data_io import append_jsonl_path, dump_jsonl_path
from serena_policy import (
    backup_file,
    classify_write_scope,
    file_sha256_text,
    load_serena_config,
    normalize_rel_path,
    preflight,
    resolve_root,
    update_manifest_for_path,
)


TEXT_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".jsonl",
    ".csv",
    ".py",
    ".html",
}


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def _clip(value: str, limit: int = 240) -> str:
    compact = value.strip().replace("\n", " ")
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def fetch_compact(
    *,
    query: str = "",
    paths: list[str] | None = None,
    limit: int = 5,
    context_lines: int = 1,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    config = load_serena_config(resolved_root)
    read_roots = [resolved_root / item for item in config.get("paths", {}).get("read_roots", [])]
    requested_paths = [normalize_rel_path(item) for item in (paths or []) if str(item).strip()]
    candidates: list[Path] = []

    if requested_paths:
        for rel_path in requested_paths:
            target = resolved_root / rel_path
            if target.exists() and target.is_file() and _is_text_file(target):
                candidates.append(target)
    else:
        for base in read_roots:
            if not base.exists():
                continue
            for target in base.rglob("*"):
                if target.is_file() and _is_text_file(target):
                    candidates.append(target)

    normalized_query = query.strip().lower()
    matches: list[dict[str, Any]] = []

    for target in candidates:
        rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        if normalized_query:
            for index, line in enumerate(lines, start=1):
                if normalized_query not in line.lower():
                    continue
                start = max(index - context_lines - 1, 0)
                end = min(index + context_lines, len(lines))
                excerpt = "\n".join(lines[start:end])
                matches.append(
                    {
                        "path": rel_path,
                        "line": index,
                        "snippet": _clip(excerpt, limit=320),
                    }
                )
                if len(matches) >= max(limit, 1):
                    break
        else:
            preview = "\n".join(line for line in lines if line.strip()[:1])[:320]
            matches.append(
                {
                    "path": rel_path,
                    "line": 1,
                    "snippet": _clip(preview, limit=320),
                }
            )
        if len(matches) >= max(limit, 1):
            break

    summary = f"{len(matches)} coincidencias compactas"
    if normalized_query:
        summary += f" para `{query.strip()}`"
    return {
        "summary": summary,
        "matches": matches,
        "references": [item["path"] for item in matches],
    }


def repo_map(
    *,
    query: str = "",
    paths: list[str] | None = None,
    limit: int = 40,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    config = load_serena_config(resolved_root)
    read_roots = [resolved_root / item for item in config.get("paths", {}).get("read_roots", [])]
    requested_paths = [normalize_rel_path(item) for item in (paths or []) if str(item).strip()]
    candidates: list[Path] = []

    if requested_paths:
        for rel_path in requested_paths:
            target = resolved_root / rel_path
            if target.exists() and target.is_file() and _is_text_file(target):
                candidates.append(target)
    else:
        for base in read_roots:
            if not base.exists():
                continue
            for target in base.rglob("*"):
                if target.is_file() and _is_text_file(target):
                    candidates.append(target)

    normalized_query = query.strip().lower()
    items: list[dict[str, Any]] = []
    total_bytes = 0
    for target in candidates:
        rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
        if normalized_query and normalized_query not in rel_path.lower():
            continue
        size_bytes = int(target.stat().st_size)
        total_bytes += size_bytes
        items.append(
            {
                "path": rel_path,
                "bytes": size_bytes,
                "extension": target.suffix.lower(),
            }
        )
        if len(items) >= max(limit, 1):
            break

    return {
        "summary": f"{len(items)} rutas compactas mapeadas",
        "items": items,
        "total_bytes": total_bytes,
        "references": [item["path"] for item in items],
    }


def fetch_changes(
    *,
    paths: list[str] | None = None,
    limit: int = 10,
    max_diff_chars: int = 1400,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    requested_paths = [normalize_rel_path(item) for item in (paths or []) if str(item).strip()]
    status_cmd = ["git", "status", "--porcelain", "--untracked-files=no"]
    status_result = subprocess.run(
        status_cmd,
        cwd=resolved_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if status_result.returncode != 0:
        return {
            "summary": "No se pudo consultar estado git.",
            "changes": [],
            "references": [],
            "error": _clip(status_result.stderr or "git status failed"),
        }

    changes: list[dict[str, Any]] = []
    for raw_line in status_result.stdout.splitlines():
        line = raw_line.rstrip()
        if len(line) < 4:
            continue
        rel_path = normalize_rel_path(line[3:])
        if requested_paths and not any(rel_path.startswith(prefix) or rel_path == prefix for prefix in requested_paths):
            continue
        diff_cmd = ["git", "diff", "--unified=0", "--", rel_path]
        diff_result = subprocess.run(
            diff_cmd,
            cwd=resolved_root,
            capture_output=True,
            text=True,
            check=False,
        )
        diff_text = diff_result.stdout if diff_result.returncode == 0 else (diff_result.stderr or "")
        changes.append(
            {
                "path": rel_path,
                "status": line[:2].strip() or "??",
                "diff_excerpt": _clip(diff_text, limit=max(max_diff_chars, 120)),
            }
        )
        if len(changes) >= max(limit, 1):
            break

    return {
        "summary": f"{len(changes)} cambios detectados en git",
        "changes": changes,
        "references": [item["path"] for item in changes],
    }


def trace_lookup(
    *,
    query: str,
    limit: int = 5,
    context_lines: int = 0,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    targets: list[str] = [
        "00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md",
        "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
    ]
    decisions_dir = resolved_root / "00_sistema_tesis" / "decisiones"
    if decisions_dir.exists():
        decision_files = sorted(
            normalize_rel_path(str(item.relative_to(resolved_root)))
            for item in decisions_dir.glob("*.md")
            if item.is_file()
        )
        targets.extend(decision_files[:20])
    payload = fetch_compact(
        query=query.strip(),
        paths=targets,
        limit=limit,
        context_lines=context_lines,
        root=resolved_root,
    )
    payload["summary"] = f"{len(payload['matches'])} referencias de trazabilidad para `{query.strip()}`"
    return payload


def session_brief(
    *,
    query: str = "",
    paths: list[str] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    map_payload = repo_map(query=query.strip(), paths=paths, limit=12, root=resolved_root)
    change_payload = fetch_changes(paths=paths, limit=6, max_diff_chars=600, root=resolved_root)
    trace_payload: dict[str, Any] = {"summary": "sin consulta de trazabilidad", "matches": [], "references": []}
    if query.strip():
        trace_payload = trace_lookup(query=query.strip(), limit=4, context_lines=0, root=resolved_root)
    summary = (
        f"brief: rutas={len(map_payload['items'])} "
        f"cambios={len(change_payload['changes'])} "
        f"trazas={len(trace_payload.get('matches', []))}"
    )
    references = list(
        dict.fromkeys(
            map_payload["references"]
            + change_payload["references"]
            + list(trace_payload.get("references", []))
        )
    )
    return {
        "summary": summary,
        "repo_map": map_payload["items"],
        "changes": change_payload["changes"],
        "trace_matches": trace_payload.get("matches", []),
        "references": references,
    }


@contextmanager
def _patched_ab_pilot_root(root: Path):
    previous_common_root = common.ROOT
    previous_ab_root = ab_pilot.ROOT
    common.ROOT = root
    ab_pilot.ROOT = root
    try:
        yield
    finally:
        common.ROOT = previous_common_root
        ab_pilot.ROOT = previous_ab_root


def evaluate_serena_artifact(
    *,
    plan_path: str,
    report_path: str = "00_sistema_tesis/config/ab_pilot_report.json",
    markdown_path: str = "06_dashboard/generado/ab_pilot_report.md",
    trace_path: str = "00_sistema_tesis/bitacora/audit_history/ab_pilot_runs.jsonl",
    session_id: str = "",
    step_id: str = "",
    source_event_id: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    for rel_path in (report_path, markdown_path, trace_path):
        scope = classify_write_scope(rel_path, resolved_root)
        if scope not in {"derived", "controlled"}:
            raise ValueError(f"La salida `{rel_path}` no está permitida para artefactos Serena.")
        backup_file(rel_path, resolved_root)

    context = ab_pilot.ExecutionContext(
        session_id=session_id.strip() or "serena-mcp",
        step_id=step_id.strip(),
        source_event_id=source_event_id.strip(),
    )
    with _patched_ab_pilot_root(resolved_root):
        report, markdown, trace, payload = ab_pilot.evaluate_plan(
            plan_relative_path=normalize_rel_path(plan_path),
            report_relative_path=normalize_rel_path(report_path),
            markdown_relative_path=normalize_rel_path(markdown_path),
            trace_relative_path=normalize_rel_path(trace_path),
            context=context,
        )
    return {
        "report_path": normalize_rel_path(str(report.relative_to(resolved_root))),
        "markdown_path": normalize_rel_path(str(markdown.relative_to(resolved_root))),
        "trace_path": normalize_rel_path(str(trace.relative_to(resolved_root))),
        "summary": payload.get("summary", {}),
    }


def write_derived_artifact(
    *,
    path: str,
    content: str,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    normalized = normalize_rel_path(path)
    scope = classify_write_scope(normalized, resolved_root)
    if scope != "derived":
        raise ValueError(f"La ruta `{normalized}` no es un artefacto derivado permitido.")
    target = resolved_root / normalized
    backup_file(normalized, resolved_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {
        "path": normalized,
        "sha256": file_sha256_text(content),
    }


def prepare_change(
    *,
    path: str,
    new_content: str,
    intent: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    normalized = normalize_rel_path(path)
    target = resolved_root / normalized
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    diff_lines = list(
        difflib.unified_diff(
            current.splitlines(),
            new_content.splitlines(),
            fromfile=f"a/{normalized}",
            tofile=f"b/{normalized}",
            lineterm="",
        )
    )
    preview = "\n".join(diff_lines[:200])
    return {
        "path": normalized,
        "intent": intent.strip(),
        "current_sha256": file_sha256_text(current),
        "proposed_sha256": file_sha256_text(new_content),
        "diff_preview": preview,
        "preflight": preflight(tool_name="canon.prepare_change", target_paths=[normalized], intent=intent, root=resolved_root),
    }


def apply_controlled_change(
    *,
    path: str,
    new_content: str,
    step_id: str,
    source_event_id: str,
    intent: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    normalized = normalize_rel_path(path)
    assessment = preflight(
        tool_name="canon.apply_controlled_change",
        target_paths=[normalized],
        step_id=step_id,
        source_event_id=source_event_id,
        intent=intent,
        root=resolved_root,
    )
    if assessment["errors"]:
        raise ValueError("; ".join(assessment["errors"]))

    target = resolved_root / normalized
    backup_file(normalized, resolved_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_content, encoding="utf-8")
    if assessment["write_scope"] in {"controlled", "protected"}:
        update_manifest_for_path(normalized, resolved_root)
    return {
        "path": normalized,
        "sha256": file_sha256_text(new_content),
        "preflight": assessment,
    }


def append_trace_record(
    *,
    tool_name: str,
    intent: str,
    minimized_inputs: dict[str, Any],
    result: dict[str, Any],
    read_paths: list[str] | None = None,
    write_paths: list[str] | None = None,
    step_id: str = "",
    source_event_id: str = "",
    identity: dict[str, Any] | None = None,
    telemetry: dict[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    config = load_serena_config(resolved_root)
    trace_rel_path = normalize_rel_path(str(config.get("trace", {}).get("path", "")))
    if not trace_rel_path:
        raise ValueError("La configuración Serena MCP no define trace.path")
    target = resolved_root / trace_rel_path
    record = {
        "timestamp": common.now_stamp(),
        "tool": tool_name,
        "intent": intent.strip(),
        "inputs": minimized_inputs,
        "read_paths": [normalize_rel_path(item) for item in (read_paths or [])],
        "write_paths": [normalize_rel_path(item) for item in (write_paths or [])],
        "result_hash": file_sha256_text(json.dumps(result, ensure_ascii=False, sort_keys=True)),
        "step_id": step_id.strip(),
        "source_event_id": source_event_id.strip(),
    }
    if identity:
        sanitized_identity = {str(key): str(value).strip() for key, value in identity.items() if str(value).strip()}
        if sanitized_identity:
            record["identity"] = sanitized_identity
    if telemetry:
        sanitized_telemetry = {
            str(key): value for key, value in telemetry.items() if str(key).strip()
        }
        if sanitized_telemetry:
            record["telemetry"] = sanitized_telemetry
    append_jsonl_path(target, record)
    return {
        "path": trace_rel_path,
        "record": record,
    }
