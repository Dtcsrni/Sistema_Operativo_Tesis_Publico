from __future__ import annotations

import difflib
import ast
import json
import re
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


def _read_roots(resolved_root: Path) -> list[Path]:
    config = load_serena_config(resolved_root)
    return [resolved_root / item for item in config.get("paths", {}).get("read_roots", [])]


def _is_under(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve()
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


def _candidate_text_files(resolved_root: Path, paths: list[str] | None = None) -> list[Path]:
    read_roots = _read_roots(resolved_root)
    requested_paths = [normalize_rel_path(item) for item in (paths or []) if str(item).strip()]
    candidates: list[Path] = []
    if requested_paths:
        for rel_path in requested_paths:
            target = resolved_root / rel_path
            if (
                target.exists()
                and target.is_file()
                and _is_text_file(target)
                and (_is_under(target, read_roots) or rel_path == "MEMORY.md")
            ):
                candidates.append(target)
        return candidates
    for base in read_roots:
        if not base.exists():
            continue
        for target in base.rglob("*"):
            if target.is_file() and _is_text_file(target):
                candidates.append(target)
    return candidates


def _line_preview(lines: list[str], index: int, context_lines: int, limit: int = 360) -> str:
    start = max(index - context_lines - 1, 0)
    end = min(index + context_lines, len(lines))
    return _clip("\n".join(lines[start:end]), limit=limit)


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


def search_ranked(
    *,
    query: str,
    paths: list[str] | None = None,
    limit: int = 8,
    context_lines: int = 1,
    max_chars: int = 2400,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    terms = [term for term in re.split(r"\s+", query.strip().lower()) if term]
    if not terms:
        return {"summary": "consulta vacia", "matches": [], "references": [], "omitted": []}
    matches: list[dict[str, Any]] = []
    omitted: list[str] = []
    budget = max(max_chars, 200)
    used_chars = 0
    for target in _candidate_text_files(resolved_root, paths):
        rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        path_score = sum(2 for term in terms if term in rel_path.lower())
        for index, line in enumerate(lines, start=1):
            lowered = line.lower()
            line_score = sum(lowered.count(term) for term in terms)
            if not line_score and not path_score:
                continue
            snippet = _line_preview(lines, index, context_lines)
            projected = used_chars + len(snippet)
            if projected > budget:
                omitted.append(rel_path)
                break
            used_chars = projected
            matches.append(
                {
                    "path": rel_path,
                    "line": index,
                    "score": line_score + path_score,
                    "snippet": snippet,
                }
            )
            if len(matches) >= max(limit, 1):
                break
        if len(matches) >= max(limit, 1):
            break
    matches.sort(key=lambda item: (-int(item["score"]), item["path"], int(item["line"])))
    clipped_matches = matches[: max(limit, 1)]
    return {
        "summary": f"{len(clipped_matches)} coincidencias rankeadas para `{query.strip()}`",
        "matches": clipped_matches,
        "references": list(dict.fromkeys(item["path"] for item in clipped_matches)),
        "omitted": list(dict.fromkeys(omitted)),
    }


def file_digest(
    *,
    paths: list[str],
    max_chars: int = 1200,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    digests: list[dict[str, Any]] = []
    for target in _candidate_text_files(resolved_root, paths):
        rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
        text = target.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        preview_lines = [line for line in lines if line.strip()][:12]
        digests.append(
            {
                "path": rel_path,
                "sha256": file_sha256_text(text),
                "bytes": target.stat().st_size,
                "lines": len(lines),
                "preview": _clip("\n".join(preview_lines), limit=max(max_chars, 160)),
            }
        )
    return {
        "summary": f"{len(digests)} digest(s) de archivo",
        "digests": digests,
        "references": [item["path"] for item in digests],
    }


def symbol_index(
    *,
    paths: list[str] | None = None,
    limit: int = 80,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    symbols: list[dict[str, Any]] = []
    for target in _candidate_text_files(resolved_root, paths):
        rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
        text = target.read_text(encoding="utf-8", errors="replace")
        if target.suffix.lower() == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(
                        {
                            "path": rel_path,
                            "line": int(getattr(node, "lineno", 1)),
                            "kind": node.__class__.__name__,
                            "name": node.name,
                        }
                    )
                    if len(symbols) >= max(limit, 1):
                        break
        elif target.suffix.lower() in {".md", ".markdown"}:
            for index, line in enumerate(text.splitlines(), start=1):
                if line.startswith("#"):
                    symbols.append(
                        {
                            "path": rel_path,
                            "line": index,
                            "kind": "MarkdownHeading",
                            "name": line.lstrip("#").strip(),
                        }
                    )
                    if len(symbols) >= max(limit, 1):
                        break
        if len(symbols) >= max(limit, 1):
            break
    return {
        "summary": f"{len(symbols)} simbolos compactos",
        "symbols": symbols,
        "references": list(dict.fromkeys(item["path"] for item in symbols)),
    }


def dependency_map(
    *,
    paths: list[str],
    limit: int = 80,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    edges: list[dict[str, Any]] = []
    for target in _candidate_text_files(resolved_root, paths):
        rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
        text = target.read_text(encoding="utf-8", errors="replace")
        if target.suffix.lower() == ".py":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        edges.append({"path": rel_path, "type": "import", "target": alias.name})
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    edges.append({"path": rel_path, "type": "from_import", "target": module})
                if len(edges) >= max(limit, 1):
                    break
        else:
            for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
                edges.append({"path": rel_path, "type": "markdown_link", "target": match.group(1)})
                if len(edges) >= max(limit, 1):
                    break
        if len(edges) >= max(limit, 1):
            break
    return {
        "summary": f"{len(edges)} dependencias/referencias compactas",
        "edges": edges,
        "references": list(dict.fromkeys(item["path"] for item in edges)),
    }


def related_paths(
    *,
    paths: list[str],
    limit: int = 20,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    seeds = [normalize_rel_path(item) for item in paths if str(item).strip()]
    terms = {Path(seed).stem.lower() for seed in seeds}
    items: list[dict[str, Any]] = []
    for target in _candidate_text_files(resolved_root):
        rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
        if rel_path in seeds:
            continue
        lowered = rel_path.lower()
        score = sum(1 for term in terms if term and term in lowered)
        if not score:
            continue
        items.append({"path": rel_path, "score": score})
        if len(items) >= max(limit, 1):
            break
    items.sort(key=lambda item: (-int(item["score"]), item["path"]))
    return {
        "summary": f"{len(items)} rutas relacionadas",
        "items": items,
        "references": [item["path"] for item in items],
    }


def context_bundle(
    *,
    query: str = "",
    paths: list[str] | None = None,
    max_chars: int = 3600,
    include_changes: bool = True,
    include_trace: bool = True,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    budget = max(max_chars, 600)
    sections: list[dict[str, Any]] = []
    omitted: list[str] = []
    references: list[str] = []

    def add_section(name: str, payload: dict[str, Any]) -> None:
        nonlocal budget
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if len(encoded) > budget:
            omitted.append(name)
            return
        budget -= len(encoded)
        sections.append({"name": name, "payload": payload})
        references.extend(str(item) for item in payload.get("references", []))

    if query.strip():
        add_section("search_ranked", search_ranked(query=query, paths=paths, limit=6, max_chars=budget // 2, root=resolved_root))
    if paths:
        add_section("file_digest", file_digest(paths=paths, max_chars=min(1000, budget), root=resolved_root))
    else:
        add_section("repo_map", repo_map(query=query, limit=12, root=resolved_root))
    if include_changes:
        add_section("changes", fetch_changes(paths=paths, limit=6, max_diff_chars=700, root=resolved_root))
    if include_trace and query.strip():
        add_section("trace", trace_lookup(query=query, limit=4, root=resolved_root))
    return {
        "summary": f"bundle compacto con {len(sections)} secciones",
        "sections": sections,
        "references": list(dict.fromkeys(references)),
        "omitted": omitted,
        "remaining_chars": budget,
    }


def change_impact(
    *,
    paths: list[str] | None = None,
    limit: int = 20,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    changes = fetch_changes(paths=paths, limit=limit, max_diff_chars=700, root=resolved_root)
    impacted = []
    for item in changes.get("changes", []):
        rel_path = str(item.get("path", ""))
        related = related_paths(paths=[rel_path], limit=5, root=resolved_root)
        impacted.append(
            {
                "path": rel_path,
                "status": item.get("status", ""),
                "related_paths": related.get("references", []),
            }
        )
    return {
        "summary": f"{len(impacted)} cambios con impacto compacto",
        "impacted": impacted,
        "references": list(dict.fromkeys([item["path"] for item in impacted] + sum((item["related_paths"] for item in impacted), []))),
    }


def todo_scan(
    *,
    paths: list[str] | None = None,
    limit: int = 30,
    root: Path | None = None,
) -> dict[str, Any]:
    pattern = re.compile(r"\b(TODO|FIXME|PENDIENTE|XXX)\b", re.IGNORECASE)
    resolved_root = resolve_root(root)
    items: list[dict[str, Any]] = []
    for target in _candidate_text_files(resolved_root, paths):
        rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        for index, line in enumerate(lines, start=1):
            if not pattern.search(line):
                continue
            items.append({"path": rel_path, "line": index, "snippet": _clip(line, limit=260)})
            if len(items) >= max(limit, 1):
                break
        if len(items) >= max(limit, 1):
            break
    return {
        "summary": f"{len(items)} pendientes compactos",
        "items": items,
        "references": list(dict.fromkeys(item["path"] for item in items)),
    }


def memory_lookup(
    *,
    query: str,
    limit: int = 8,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    targets = [
        path
        for path in [
            "MEMORY.md",
            "00_sistema_tesis/bitacora/indice_fuentes_conversacion.md",
            "00_sistema_tesis/canon/events.jsonl",
        ]
        if (resolved_root / path).exists()
    ]
    payload = search_ranked(query=query, paths=targets, limit=limit, context_lines=0, root=resolved_root)
    payload["summary"] = f"{len(payload['matches'])} referencias de memoria para `{query.strip()}`"
    return payload


def session_recap(
    *,
    session_id: str,
    limit: int = 12,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    events_path = resolved_root / "00_sistema_tesis/canon/events.jsonl"
    rows: list[dict[str, Any]] = []
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if session_id not in line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(
                {
                    "event_id": row.get("event_id", ""),
                    "event_type": row.get("event_type", ""),
                    "occurred_at": row.get("occurred_at", ""),
                    "summary": _clip(json.dumps(row.get("payload", {}), ensure_ascii=False, sort_keys=True), limit=420),
                }
            )
            if len(rows) >= max(limit, 1):
                break
    return {
        "summary": f"{len(rows)} eventos para sesion `{session_id}`",
        "events": rows,
        "references": ["00_sistema_tesis/canon/events.jsonl"] if rows else [],
    }


def derived_index(
    *,
    query: str = "",
    limit: int = 30,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    roots = [
        resolved_root / "06_dashboard/generado",
        resolved_root / "06_dashboard/wiki",
        resolved_root / "00_sistema_tesis/bitacora/audit_history",
    ]
    items: list[dict[str, Any]] = []
    normalized_query = query.strip().lower()
    for base in roots:
        if not base.exists():
            continue
        for target in base.rglob("*"):
            if not target.is_file() or not _is_text_file(target):
                continue
            rel_path = normalize_rel_path(str(target.relative_to(resolved_root)))
            if normalized_query and normalized_query not in rel_path.lower():
                continue
            items.append({"path": rel_path, "bytes": target.stat().st_size, "sha256": file_sha256_text(target.read_text(encoding="utf-8", errors="replace"))})
            if len(items) >= max(limit, 1):
                break
        if len(items) >= max(limit, 1):
            break
    return {
        "summary": f"{len(items)} artefactos derivados indexados",
        "items": items,
        "references": [item["path"] for item in items],
    }


def evidence_digest(
    *,
    query: str,
    limit: int = 8,
    root: Path | None = None,
) -> dict[str, Any]:
    return memory_lookup(query=query, limit=limit, root=root)


def step_status(
    *,
    step_id: str,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    events_path = resolved_root / "00_sistema_tesis/canon/events.jsonl"
    found: dict[str, Any] = {}
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if step_id not in line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("event_id") == step_id or row.get("human_validation", {}).get("step_id") == step_id:
                found = row
    if not found:
        return {"summary": f"{step_id} no encontrado", "status": "not_found", "references": []}
    validation = dict(found.get("human_validation", {}) or {})
    return {
        "summary": f"{step_id}: {validation.get('status', found.get('event_type', 'unknown'))}",
        "status": validation.get("status", found.get("event_type", "")),
        "event_id": found.get("event_id", ""),
        "source_event_id": validation.get("source_event_id", ""),
        "references": ["00_sistema_tesis/canon/events.jsonl"],
    }


def trace_gap_scan(
    *,
    limit: int = 20,
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    events_path = resolved_root / "00_sistema_tesis/canon/events.jsonl"
    source_events: dict[str, dict[str, Any]] = {}
    validated_sources: set[str] = set()
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_id = str(row.get("event_id", ""))
            if row.get("event_type") == "conversation_source_registered":
                source_events[event_id] = row
            source_event_id = str(row.get("human_validation", {}).get("source_event_id", ""))
            if source_event_id:
                validated_sources.add(source_event_id)
    gaps = []
    for event_id, row in reversed(list(source_events.items())):
        if event_id in validated_sources:
            continue
        gaps.append(
            {
                "event_id": event_id,
                "session_id": row.get("session_id", ""),
                "quoted_text_hash": row.get("payload", {}).get("quoted_text_hash", ""),
            }
        )
        if len(gaps) >= max(limit, 1):
            break
    return {
        "summary": f"{len(gaps)} fuentes sin validacion vinculada detectadas",
        "gaps": gaps,
        "references": ["00_sistema_tesis/canon/events.jsonl"] if gaps else [],
    }


def protected_path_check(
    *,
    paths: list[str],
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    items = []
    for path in paths:
        normalized = normalize_rel_path(path)
        target = resolved_root / normalized
        text = target.read_text(encoding="utf-8", errors="replace") if target.exists() and target.is_file() else ""
        items.append(
            {
                "path": normalized,
                "write_scope": classify_write_scope(normalized, resolved_root),
                "protected_marker": "<!-- SISTEMA_TESIS:PROTEGIDO -->" in text,
                "exists": target.exists(),
            }
        )
    return {
        "summary": f"{len(items)} rutas evaluadas",
        "items": items,
        "references": [item["path"] for item in items],
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


def write_memory_derived_artifact(
    *,
    path: str,
    content: str,
    root: Path | None = None,
) -> dict[str, Any]:
    normalized = normalize_rel_path(path)
    if Path(normalized).name.upper() == "MEMORY.MD":
        raise ValueError("MEMORY.md es generado y no debe editarse manualmente.")
    if "memory" not in normalized.lower() and "memoria" not in normalized.lower():
        raise ValueError("La ruta debe identificar explicitamente un artefacto derivado de memoria.")
    return write_derived_artifact(path=normalized, content=content, root=root)


def prepare_multi_change(
    *,
    changes: list[dict[str, Any]],
    intent: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    prepared: list[dict[str, Any]] = []
    errors: list[str] = []
    for change in changes:
        path = str(change.get("path", "")).strip()
        if not path:
            errors.append("Cambio sin path.")
            continue
        try:
            payload = prepare_change(
                path=path,
                new_content=str(change.get("new_content", "")),
                intent=intent,
                root=resolved_root,
            )
            prepared.append(payload)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return {
        "summary": f"{len(prepared)} cambios preparados",
        "changes": prepared,
        "errors": errors,
        "references": [item["path"] for item in prepared],
    }


def apply_multi_change(
    *,
    changes: list[dict[str, Any]],
    step_id: str,
    source_event_id: str,
    intent: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    assessments: list[dict[str, Any]] = []
    errors: list[str] = []
    normalized_changes: list[dict[str, str]] = []
    for change in changes:
        normalized = normalize_rel_path(str(change.get("path", "")).strip())
        if not normalized:
            errors.append("Cambio sin path.")
            continue
        assessment = preflight(
            tool_name="canon.apply_multi_change",
            target_paths=[normalized],
            step_id=step_id,
            source_event_id=source_event_id,
            intent=intent,
            root=resolved_root,
        )
        assessments.append(assessment)
        if assessment["errors"]:
            errors.extend(f"{normalized}: {error}" for error in assessment["errors"])
        normalized_changes.append({"path": normalized, "new_content": str(change.get("new_content", ""))})
    if errors:
        raise ValueError("; ".join(errors))

    artifacts: list[dict[str, Any]] = []
    for change in normalized_changes:
        target = resolved_root / change["path"]
        backup_file(change["path"], resolved_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(change["new_content"], encoding="utf-8")
        scope = classify_write_scope(change["path"], resolved_root)
        if scope in {"controlled", "protected"}:
            update_manifest_for_path(change["path"], resolved_root)
        artifacts.append({"path": change["path"], "sha256": file_sha256_text(change["new_content"])})
    return {
        "summary": f"{len(artifacts)} cambios aplicados",
        "artifacts": artifacts,
        "preflight": assessments,
        "references": [item["path"] for item in artifacts],
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
