from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request
from uuid import uuid4

from .contracts import ReferenceRecord


DOI_RE = re.compile(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)


def default_source_jsonl(repo_root: Path) -> Path:
    raw = os.getenv("OPENCLAW_SOURCE_JSONL", "").strip()
    if raw:
        return Path(raw)
    return repo_root / "runtime" / "openclaw" / "state" / "sources" / "references.jsonl"


def ingest_reference(
    *,
    repo_root: Path,
    source_type: str,
    title: str = "",
    authors: list[str] | None = None,
    year: str = "",
    doi: str = "",
    url: str = "",
    local_path: str = "",
    publisher: str = "",
    container_title: str = "",
    evidence_level: str = "pendiente",
    claims: list[str] | None = None,
    tags: list[str] | None = None,
    verify_online: bool = True,
) -> ReferenceRecord:
    normalized_doi = normalize_doi(doi)
    metadata: dict[str, Any] = {}
    notes: list[str] = []
    verification_status = "no_verificada"
    if verify_online and normalized_doi:
        crossref = fetch_crossref_metadata(normalized_doi)
        metadata["crossref"] = crossref
        if crossref.get("status") == "ok":
            verification_status = "doi_verificado_crossref"
            msg = crossref.get("message") or {}
            title = title or _first(msg.get("title"))
            authors = authors or _authors_from_crossref(msg.get("author") or [])
            year = year or _year_from_crossref(msg)
            publisher = publisher or str(msg.get("publisher", "") or "")
            container_title = container_title or _first(msg.get("container-title"))
            url = url or str(msg.get("URL", "") or "")
            notes.append("doi metadata resolved through Crossref REST API")
        else:
            verification_status = "no_verificable"
            notes.append(str(crossref.get("error", "crossref_lookup_failed")))
    if verify_online and url:
        url_status = probe_url(url)
        metadata["url_probe"] = url_status
        if url_status.get("status") == "ok" and verification_status == "no_verificada":
            verification_status = "url_verificada"
        elif url_status.get("status") != "ok":
            notes.append(str(url_status.get("error", "url_probe_failed")))
    local_hash = hash_local_file(repo_root, local_path) if local_path else ""
    if local_path and not local_hash:
        notes.append("local_file_missing_or_unreadable")
    if not title:
        notes.append("title_missing")
    if not (normalized_doi or url or local_hash):
        verification_status = "no_verificable"
        notes.append("missing_doi_url_or_local_hash")
    record_payload = {
        "source_type": source_type,
        "title": title,
        "authors": authors or [],
        "year": year,
        "doi": normalized_doi,
        "url": url,
        "publisher": publisher,
        "container_title": container_title,
        "evidence_level": evidence_level,
        "local_hash": local_hash,
        "claims": claims or [],
        "tags": tags or [],
        "metadata": metadata,
    }
    source_hash = hashlib.sha256(json.dumps(record_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    apa_reference = render_apa_reference(
        authors=authors or [],
        year=year,
        title=title,
        source_type=source_type,
        container_title=container_title,
        publisher=publisher,
        doi=normalized_doi,
        url=url,
    )
    return ReferenceRecord(
        reference_id=f"REF-{uuid4().hex[:12]}",
        source_type=source_type,
        title=title,
        authors=authors or [],
        year=year,
        doi=normalized_doi,
        url=url,
        publisher=publisher,
        container_title=container_title,
        evidence_level=evidence_level,
        verification_status=verification_status,
        verification_notes=notes,
        apa_reference=apa_reference,
        source_hash=source_hash,
        local_path=local_path,
        claims=claims or [],
        tags=tags or [],
        metadata=metadata,
        created_at=datetime.now(UTC).isoformat(),
    )


def append_reference_jsonl(record: ReferenceRecord, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def list_reference_jsonl(path: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records: list[dict[str, Any]] = []
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            records.append({"status": "error", "error": "invalid_jsonl_line"})
        if len(records) >= limit:
            break
    return list(reversed(records))


def source_policy_snapshot(repo_root: Path, *, store: Any | None = None, limit: int = 10) -> dict[str, Any]:
    jsonl_path = default_source_jsonl(repo_root)
    records = []
    if store is not None:
        try:
            records = store.list_reference_records(limit=limit)
        except Exception:
            records = []
    if not records:
        records = list_reference_jsonl(jsonl_path, limit=limit)
    return {
        "status": "ok",
        "primary_store": "jsonl",
        "jsonl_path": str(jsonl_path),
        "sqlite_mirror": bool(store is not None),
        "apa_style": "APA 7",
        "verification_policy": "doi_or_url_or_local_hash_required; Crossref DOI metadata preferred; failures stay no_verificable",
        "crossref_mailto_configured": bool(os.getenv("OPENCLAW_CROSSREF_MAILTO", "").strip()),
        "recent": records,
    }


def normalize_doi(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    value = value.removeprefix("doi:").strip()
    value = value.replace("https://doi.org/", "").replace("http://doi.org/", "")
    match = DOI_RE.search(value)
    return match.group(1).rstrip(".").lower() if match else value.rstrip(".").lower()


def fetch_crossref_metadata(doi: str, *, timeout_seconds: int = 20) -> dict[str, Any]:
    encoded = parse.quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded}"
    mailto = os.getenv("OPENCLAW_CROSSREF_MAILTO", "").strip()
    if mailto:
        url = f"{url}?{parse.urlencode({'mailto': mailto})}"
    req = request.Request(url)
    req.add_header("User-Agent", _crossref_user_agent(mailto))
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except error.HTTPError as exc:
        return {"status": "error", "error": f"crossref_http_{exc.code}"}
    except (error.URLError, json.JSONDecodeError) as exc:
        return {"status": "error", "error": f"crossref_lookup_failed:{exc}"}
    if payload.get("status") != "ok":
        return {"status": "error", "error": "crossref_status_not_ok", "payload": payload}
    return {"status": "ok", "message": payload.get("message", {})}


def probe_url(url: str, *, timeout_seconds: int = 15) -> dict[str, Any]:
    if not url.strip():
        return {"status": "skipped", "error": "url_missing"}
    req = request.Request(url, method="HEAD")
    req.add_header("User-Agent", "OpenClaw-SourceVerifier/1.0")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return {"status": "ok", "status_code": int(getattr(response, "status", 200)), "final_url": response.geturl()}
    except error.HTTPError as exc:
        if exc.code in {403, 405}:
            return _probe_url_get(url, timeout_seconds=timeout_seconds)
        return {"status": "error", "error": f"url_http_{exc.code}"}
    except error.URLError as exc:
        return {"status": "error", "error": f"url_probe_failed:{exc}"}


def render_apa_reference(
    *,
    authors: list[str],
    year: str,
    title: str,
    source_type: str,
    container_title: str,
    publisher: str,
    doi: str,
    url: str,
) -> str:
    author_text = _apa_authors(authors) if authors else "Autor desconocido"
    year_text = year if year else "s. f."
    title_text = title.rstrip(".") if title else "Titulo no disponible"
    source_bits: list[str] = []
    if container_title:
        source_bits.append(container_title.rstrip("."))
    elif publisher and source_type in {"book", "dataset", "report"}:
        source_bits.append(publisher.rstrip("."))
    source = f" {' '.join(source_bits)}." if source_bits else ""
    locator = f" https://doi.org/{doi}" if doi else (f" {url}" if url else "")
    return f"{author_text} ({year_text}). {title_text}.{source}{locator}".strip()


def hash_local_file(repo_root: Path, local_path: str) -> str:
    path = Path(local_path)
    if not path.is_absolute():
        path = repo_root / path
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return ""


def _probe_url_get(url: str, *, timeout_seconds: int) -> dict[str, Any]:
    req = request.Request(url, method="GET")
    req.add_header("User-Agent", "OpenClaw-SourceVerifier/1.0")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return {"status": "ok", "status_code": int(getattr(response, "status", 200)), "final_url": response.geturl()}
    except Exception as exc:
        return {"status": "error", "error": f"url_probe_failed:{exc}"}


def _crossref_user_agent(mailto: str) -> str:
    suffix = f" mailto:{mailto}" if mailto else ""
    return f"OpenClaw-SourceVerifier/1.0 (tesis-iot; https://crossref.org){suffix}"


def _first(value: Any) -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    return str(value or "")


def _authors_from_crossref(items: list[dict[str, Any]]) -> list[str]:
    authors: list[str] = []
    for item in items:
        family = str(item.get("family", "") or "").strip()
        given = str(item.get("given", "") or "").strip()
        name = " ".join(part for part in [given, family] if part)
        if name:
            authors.append(name)
    return authors


def _year_from_crossref(message: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "created", "issued"):
        parts = ((message.get(key) or {}).get("date-parts") or [])
        if parts and parts[0]:
            return str(parts[0][0])
    return ""


def _apa_authors(authors: list[str]) -> str:
    formatted = [_format_author_name(author) for author in authors if author.strip()]
    if not formatted:
        return "Autor desconocido"
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]}, & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def _format_author_name(author: str) -> str:
    parts = [part for part in author.replace(",", " ").split() if part]
    if len(parts) <= 1:
        return author.strip()
    family = parts[-1]
    initials = " ".join(f"{part[0].upper()}." for part in parts[:-1] if part)
    return f"{family}, {initials}"
