from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
from .doc_converter import converter


SUPPORTED_SOURCE_TYPES = {"pdf", "markdown", "latex", "jsonl", "docx", "xlsx", "pptx", "html", "csv"}
DEFAULT_CHUNK_CHARS = 1800
MIN_CHUNK_CHARS = 240


@dataclass(slots=True)
class ToltecayotlChunk:
    chunk_id: str
    source_path: str
    source_type: str
    source_hash: str
    chunk_index: int
    chunk_hash: str
    text: str
    metadata: dict[str, Any]
    verification_status: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ingest_document(
    *,
    repo_root: Path,
    source_path: str,
    source_type: str,
    chunk_chars: int = DEFAULT_CHUNK_CHARS,
) -> list[ToltecayotlChunk]:
    normalized_type = source_type.strip().lower()
    if normalized_type not in SUPPORTED_SOURCE_TYPES:
        raise ValueError(f"Tipo Toltecayotl no soportado: {source_type}")
    path = _resolve_path(repo_root, source_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    source_hash = file_sha256(path)
    text, metadata = extract_text(path=path, source_type=normalized_type)
    chunks = split_text(text, chunk_chars=chunk_chars)
    created_at = datetime.now(UTC).isoformat()
    rel_path = _display_path(repo_root, path)
    return [
        ToltecayotlChunk(
            chunk_id=f"ATZ-{uuid4().hex[:12]}",
            source_path=rel_path,
            source_type=normalized_type,
            source_hash=source_hash,
            chunk_index=index,
            chunk_hash=hash_text(chunk),
            text=chunk,
            metadata={**metadata, "chunk_chars": chunk_chars},
            verification_status="hash_verificado",
            created_at=created_at,
        )
        for index, chunk in enumerate(chunks)
    ]


def extract_text(*, path: Path, source_type: str) -> tuple[str, dict[str, Any]]:
    if source_type in {"pdf", "docx", "xlsx", "pptx", "html", "csv"}:
        return converter.convert(path)
    if source_type == "jsonl":
        return _extract_jsonl(path)
    raw = path.read_text(encoding="utf-8", errors="replace")
    if source_type == "latex":
        return _strip_latex(raw), {"extractor": "latex_text_fallback"}
    return raw, {"extractor": "markdown_text"}


def split_text(text: str, *, chunk_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    size = max(chunk_chars, MIN_CHUNK_CHARS)
    paragraphs = re.split(r"(?<=[.!?])\s+", normalized)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current} {paragraph}".strip() if current else paragraph.strip()
        if len(candidate) <= size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = paragraph.strip()
        while len(current) > size:
            chunks.append(current[:size].strip())
            current = current[size:].strip()
    if current:
        chunks.append(current)
    return chunks


def chunks_to_jsonl(chunks: list[ToltecayotlChunk]) -> str:
    return "\n".join(json.dumps(chunk.to_dict(), ensure_ascii=False, sort_keys=True) for chunk in chunks) + ("\n" if chunks else "")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_jsonl(path: Path) -> tuple[str, dict[str, Any]]:
    texts: list[str] = []
    records = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        records += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            texts.append(line)
            continue
        texts.append(_json_text(payload))
    return "\n".join(texts), {"extractor": "jsonl_flatten", "records": records}


def _json_text(payload: Any) -> str:
    if isinstance(payload, dict):
        values = []
        for key in ("title", "abstract", "summary", "text", "content", "claim_text"):
            value = payload.get(key)
            if value:
                values.append(str(value))
        return " ".join(values) if values else json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return str(payload)


def _strip_latex(text: str) -> str:
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\\(?:cite|ref|label)\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^}]*)\})?", r" \1 ", text)
    text = text.replace("{", " ").replace("}", " ")
    return text


def _resolve_path(repo_root: Path, source_path: str) -> Path:
    path = Path(source_path)
    if path.is_absolute():
        return path
    return repo_root / path


def _display_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
