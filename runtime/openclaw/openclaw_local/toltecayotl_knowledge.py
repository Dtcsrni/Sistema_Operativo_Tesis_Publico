from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib import error, request

from .toltecayotl_ingestor import ToltecayotlChunk
from .knowledge_sync import append_chunks_jsonl, default_sync_dir, read_chunks_jsonl


COLLECTION_NAME = "ToltecayotlKnowledgeChunk"


def toltecayotl_enabled() -> bool:
    return os.getenv("TOLTECAYOTL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def toltecayotl_status(repo_root: Path) -> dict[str, Any]:
    url = os.getenv("TOLTECAYOTL_WEAVIATE_URL", "http://localhost:8080").strip()
    sync_dir = default_sync_dir(repo_root)
    local_records = len(read_chunks_jsonl(sync_dir / "chunks.jsonl"))
    status: dict[str, Any] = {
        "status": "ok",
        "enabled": toltecayotl_enabled(),
        "weaviate_url": url,
        "embedding_model": os.getenv("TOLTECAYOTL_EMBEDDING_MODEL", "BAAI/bge-m3"),
        "collection": COLLECTION_NAME,
        "sync_dir": str(sync_dir),
        "local_records": local_records,
        "weaviate": "disabled",
    }
    if not toltecayotl_enabled():
        return status
    try:
        with request.urlopen(f"{url.rstrip('/')}/v1/.well-known/ready", timeout=2) as response:
            status["weaviate"] = "ready" if response.status < 500 else f"http_{response.status}"
    except Exception as exc:
        status["weaviate"] = f"unavailable:{exc}"
    return status


def upsert_chunks(repo_root: Path, chunks: list[ToltecayotlChunk]) -> dict[str, Any]:
    sync_dir = default_sync_dir(repo_root)
    records = [chunk.to_dict() for chunk in chunks]
    append_chunks_jsonl(records, sync_dir / "chunks.jsonl")
    payload = {
        "status": "ok",
        "local_records_added": len(records),
        "sync_jsonl": str(sync_dir / "chunks.jsonl"),
        "weaviate_status": "disabled",
    }
    if toltecayotl_enabled():
        payload["weaviate_status"] = _try_weaviate_upsert(records)
    return payload


def search_knowledge(repo_root: Path, query: str, *, limit: int = 5) -> dict[str, Any]:
    if toltecayotl_enabled():
        remote = _try_weaviate_search(query, limit=limit)
        if remote["status"] == "ok":
            return remote
    records = read_chunks_jsonl(default_sync_dir(repo_root) / "chunks.jsonl")
    ranked = _rank_local(records, query)[:limit]
    return {
        "status": "ok",
        "backend": "local_jsonl",
        "knowledge_context_status": "local_fallback" if records else "empty",
        "results": [_public_result(item) for item in ranked],
    }


def knowledge_context_for_task(repo_root: Path, objective: str, *, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"knowledge_context_status": "disabled", "results": []}
    result = search_knowledge(repo_root, objective, limit=3)
    return {
        "knowledge_context_status": result.get("knowledge_context_status", result.get("backend", "unknown")),
        "results": result.get("results", []),
    }


def _try_weaviate_upsert(records: list[dict[str, Any]]) -> str:
    try:
        import weaviate  # type: ignore
        import weaviate.classes as wvc  # type: ignore

        client = weaviate.connect_to_local()
        try:
            if not client.collections.exists(COLLECTION_NAME):
                client.collections.create(
                    COLLECTION_NAME,
                    vectorizer_config=wvc.config.Configure.Vectorizer.none(),
                    properties=[
                        wvc.config.Property(name="source_path", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="source_type", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="source_hash", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="chunk_hash", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="text", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="verification_status", data_type=wvc.config.DataType.TEXT),
                        wvc.config.Property(name="metadata_json", data_type=wvc.config.DataType.TEXT),
                    ],
                )
            collection = client.collections.get(COLLECTION_NAME)
            vectors = _embed_texts([str(item.get("text", "")) for item in records])
            with collection.batch.fixed_size(batch_size=100) as batch:
                for index, item in enumerate(records):
                    vector = vectors[index] if vectors else None
                    batch.add_object(properties=_weaviate_properties(item), vector=vector)
            return "upserted"
        finally:
            client.close()
    except Exception as exc:
        return f"unavailable:{exc}"


def _try_weaviate_search(query: str, *, limit: int) -> dict[str, Any]:
    try:
        import weaviate  # type: ignore

        client = weaviate.connect_to_local()
        try:
            if not client.collections.exists(COLLECTION_NAME):
                return {"status": "error", "backend": "weaviate", "error": "collection_missing"}
            collection = client.collections.get(COLLECTION_NAME)
            vectors = _embed_texts([query])
            if vectors:
                response = collection.query.near_vector(near_vector=vectors[0], limit=limit)
            else:
                response = collection.query.bm25(query=query, limit=limit)
            results = [_public_result(obj.properties) for obj in response.objects]
            return {"status": "ok", "backend": "weaviate", "knowledge_context_status": "weaviate", "results": results}
        finally:
            client.close()
    except Exception as exc:
        return {"status": "error", "backend": "weaviate", "error": str(exc)}


def _embed_texts(texts: list[str]) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        model = SentenceTransformer(os.getenv("TOLTECAYOTL_EMBEDDING_MODEL", "BAAI/bge-m3"))
        vectors = model.encode(texts, normalize_embeddings=True)
        return [list(map(float, item)) for item in vectors]
    except Exception:
        return []


def _rank_local(records: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    terms = {part.lower() for part in query.split() if len(part) > 2}
    def score(record: dict[str, Any]) -> int:
        text = str(record.get("text", "")).lower()
        return sum(1 for term in terms if term in text)
    return sorted(records, key=score, reverse=True)


def _public_result(item: dict[str, Any]) -> dict[str, Any]:
    text = str(item.get("text", ""))
    return {
        "source_hash": str(item.get("source_hash", "")),
        "chunk_hash": str(item.get("chunk_hash", "")),
        "source_path": str(item.get("source_path", "")),
        "source_type": str(item.get("source_type", "")),
        "verification_status": str(item.get("verification_status", "")),
        "text_preview": text[:500],
    }


def _weaviate_properties(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_path": str(item.get("source_path", "")),
        "source_type": str(item.get("source_type", "")),
        "source_hash": str(item.get("source_hash", "")),
        "chunk_hash": str(item.get("chunk_hash", "")),
        "text": str(item.get("text", "")),
        "verification_status": str(item.get("verification_status", "")),
        "metadata_json": json.dumps(item.get("metadata", {}), ensure_ascii=False, sort_keys=True),
    }
