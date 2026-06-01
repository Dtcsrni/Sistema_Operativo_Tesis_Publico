from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ToltecayotlSyncPackage:
    package_id: str
    created_at: str
    record_count: int
    content_hash: str
    records: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_sync_dir(repo_root: Path) -> Path:
    raw = os.getenv("TOLTECAYOTL_SYNC_DIR", "").strip()
    path = Path(raw) if raw else repo_root / "runtime" / "openclaw" / "state" / "toltecayotl_sync"
    if not path.is_absolute():
        path = repo_root / path
    return path


def append_chunks_jsonl(chunks: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")


def read_chunks_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        records.append(json.loads(line))
    return records


def export_sync_package(repo_root: Path, *, source_jsonl: Path | None = None, destination: Path | None = None) -> ToltecayotlSyncPackage:
    sync_dir = default_sync_dir(repo_root)
    source = source_jsonl or sync_dir / "chunks.jsonl"
    records = read_chunks_jsonl(source)
    content = "\n".join(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in records)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    package = ToltecayotlSyncPackage(
        package_id=f"ATZSYNC-{uuid4().hex[:12]}",
        created_at=datetime.now(UTC).isoformat(),
        record_count=len(records),
        content_hash=digest,
        records=records,
    )
    target = destination or sync_dir / f"{package.package_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(package.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return package


def import_sync_package(repo_root: Path, package_path: Path, *, target_jsonl: Path | None = None) -> dict[str, Any]:
    payload = json.loads(package_path.read_text(encoding="utf-8"))
    records = list(payload.get("records") or [])
    content = "\n".join(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in records)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    expected = str(payload.get("content_hash", "")).strip()
    if expected and digest != expected:
        raise ValueError("content_hash_mismatch")
    target = target_jsonl or default_sync_dir(repo_root) / "chunks.jsonl"
    append_chunks_jsonl(records, target)
    return {
        "status": "ok",
        "package_id": payload.get("package_id", ""),
        "imported": len(records),
        "content_hash": digest,
        "target_jsonl": str(target),
    }
