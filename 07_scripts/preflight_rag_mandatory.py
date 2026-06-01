#!/usr/bin/env python3
"""
preflight_rag_mandatory.py — Validación obligatoria de RAG antes de ejecutar tareas

Politica: "Solo Weaviate" = sin fallback JSONL
- Si requires_rag=true, DEBE recuperar chunks de Weaviate
- Si Weaviate está offline o no hay hits, la tarea se BLOQUEA
- Registra trazabilidad: query_hash, chunks_recovered, source_hash, timestamp

Uso:
  python preflight_rag_mandatory.py --task-id TASK-001 --question "¿Qué es PDR?" --context "iot"
  
Salida JSON:
  {
    "preflight_ok": bool,
    "status": "OK" | "RAG_BLOCKED" | "RAG_NO_HITS" | "RAG_TIMEOUT",
    "session_id": "rag-session-abc123",
    "chunks_recovered": int,
    "source_hash": "sha256:...",
    "chunk_hash": "sha256:...",
    "query_hash": "sha256:...",
    "timestamp": "2026-05-07T14:32:00Z",
    "message": str,
    "traceable": bool
  }
"""

import argparse
import json
import sys
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TypedDict
import logging
import uuid
import requests

# Config
WEAVIATE_BASE_URL = os.getenv("RAG_ENDPOINT", os.getenv("WEAVIATE_BASE_URL", "http://localhost:8080"))
WEAVIATE_TIMEOUT_SEC = int(os.getenv("WEAVIATE_TIMEOUT_SEC", "5"))
RAG_QUERY_CLASS = os.getenv("RAG_QUERY_CLASS", "ToltecayotlKnowledgeChunk")
RAG_CONTENT_FIELD = os.getenv("RAG_CONTENT_FIELD", "text")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PREFLIGHT-RAG] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class RagPreflight(TypedDict):
    preflight_ok: bool
    status: str
    session_id: str
    chunks_recovered: int
    source_hash: str
    chunk_hash: str
    query_hash: str
    timestamp: str
    message: str
    traceable: bool


def sha256_hash(data: str | bytes) -> str:
    """Calcula SHA256 de un string o bytes."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def check_weaviate_health() -> tuple[bool, str]:
    """
    Verifica si Weaviate está respondiendo.
    Retorna: (healthy: bool, version: str | error_msg: str)
    """
    try:
        resp = requests.get(
            f"{WEAVIATE_BASE_URL}/v1/meta",
            timeout=WEAVIATE_TIMEOUT_SEC
        )
        
        if resp.status_code == 200:
            data = resp.json()
            version = data.get("version", "unknown")
            logger.info(f"Weaviate ✓ v{version}")
            return True, version
        else:
            msg = f"Weaviate HTTP {resp.status_code}"
            logger.error(msg)
            return False, msg
    
    except requests.exceptions.Timeout:
        msg = f"Weaviate timeout ({WEAVIATE_TIMEOUT_SEC}s)"
        logger.error(msg)
        return False, msg
    except requests.exceptions.ConnectionError as e:
        msg = f"Weaviate connection error: {str(e)}"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"Weaviate health check failed: {str(e)}"
        logger.error(msg)
        return False, msg


def query_weaviate_rag(question: str, context_hint: Optional[str] = None) -> tuple[list[dict], bool]:
    """
    Consulta Weaviate para recuperar chunks académicos relevantes.
    
    Retorna:
      (chunks: list[{text, source, metadata}], success: bool)
    """
    try:
        query_text = question if not context_hint else f"{question} Contexto: {context_hint}"
        query_text = " ".join(query_text.split())
        escaped_query = query_text.replace("\\", "\\\\").replace('"', '\\"')
        graphql_query = {
            "query": f"""
            {{
              Get {{
                {RAG_QUERY_CLASS}(
                  limit: 10
                  bm25: {{
                    query: \"{escaped_query}\"
                    properties: [\"{RAG_CONTENT_FIELD}\"]
                  }}
                ) {{
                  {RAG_CONTENT_FIELD}
                  source_path
                  source_type
                  source_hash
                  chunk_hash
                  verification_status
                }}
              }}
            }}
            """
        }

        resp = requests.post(
            f"{WEAVIATE_BASE_URL}/v1/graphql",
            json=graphql_query,
            timeout=WEAVIATE_TIMEOUT_SEC,
        )

        if resp.status_code != 200:
            detail = resp.text[:500]
            logger.warning("Weaviate query returned %s: %s", resp.status_code, detail)
            if resp.status_code == 422 and ("no graphql provider" in detail.lower() or "schema is present" in detail.lower() or "leader not found" in detail.lower()):
                return [], False
            return [], False

        data = resp.json()
        if "errors" in data:
            logger.warning("GraphQL errors: %s", data["errors"])
            return [], False

        chunks: list[dict] = []
        for item in data.get("data", {}).get("Get", {}).get(RAG_QUERY_CLASS, []):
            chunks.append({
                "text": str(item.get(RAG_CONTENT_FIELD, "")),
                "source_path": str(item.get("source_path", "")),
                "source_type": str(item.get("source_type", "")),
                "source_hash": str(item.get("source_hash", "")),
                "chunk_hash": str(item.get("chunk_hash", "")),
                "verification_status": str(item.get("verification_status", "")),
            })

        logger.info("RAG: recovered %s chunks", len(chunks))
        return chunks, True

    except Exception as e:
        logger.error(f"Weaviate query failed: {str(e)}")
        return [], False


def calculate_chunks_hash(chunks: list[dict]) -> str:
    """Calcula hash de los chunks recuperados (para integridad)."""
    combined = json.dumps([c.get("text", "") for c in chunks], sort_keys=True, ensure_ascii=False)
    return sha256_hash(combined)


def calculate_source_hash(chunks: list[dict]) -> str:
    """Calcula hash de las fuentes de los chunks."""
    sources = json.dumps(
        sorted(
            set(
                str(c.get("source_hash") or c.get("source_path") or "")
                for c in chunks
                if str(c.get("source_hash") or c.get("source_path") or "")
            )
        ),
        sort_keys=True,
        ensure_ascii=False,
    )
    return sha256_hash(sources)


def run_preflight(
    task_id: str,
    question: str,
    context_hint: Optional[str] = None,
    requires_rag: bool = True
) -> RagPreflight:
    """
    Ejecuta validación de RAG preflight.
    
    Args:
      task_id: ID de la tarea
      question: pregunta a responder / contexto a recuperar
      context_hint: hint de contexto (ej. "iot", "lora")
      requires_rag: si False, devuelve OK inmediatamente
    
    Returns:
      RagPreflight: resultado de validación
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    session_id = f"rag-session-{uuid.uuid4().hex[:8]}"
    query_hash = sha256_hash(question)
    
    logger.info(f"Preflight RAG para {task_id}: requires_rag={requires_rag}")
    
    # Si no requiere RAG, OK inmediato
    if not requires_rag:
        return RagPreflight(
            preflight_ok=True,
            status="OK",
            session_id=session_id,
            chunks_recovered=0,
            source_hash="",
            chunk_hash="",
            query_hash=query_hash,
            timestamp=timestamp,
            message="RAG no requerida (requires_rag=False)",
            traceable=True
        )
    
    # Verificar Weaviate
    logger.info("Step 1: Verificando salud de Weaviate...")
    healthy, version_or_error = check_weaviate_health()
    
    if not healthy:
        logger.error(f"Weaviate no disponible: {version_or_error}")
        return RagPreflight(
            preflight_ok=False,
            status="RAG_BLOCKED",
            session_id=session_id,
            chunks_recovered=0,
            source_hash="",
            chunk_hash="",
            query_hash=query_hash,
            timestamp=timestamp,
            message=f"Weaviate offline: {version_or_error}",
            traceable=True
        )
    
    # Consultar RAG
    logger.info("Step 2: Consultando Weaviate...")
    chunks, rag_ok = query_weaviate_rag(question, context_hint)
    
    if not rag_ok:
        if RAG_QUERY_CLASS == "ToltecayotlKnowledgeChunk":
            status = "RAG_SCHEMA_MISSING"
        else:
            status = "RAG_BLOCKED"
        logger.error("Fallo en consulta Weaviate")
        return RagPreflight(
            preflight_ok=False,
            status=status,
            session_id=session_id,
            chunks_recovered=0,
            source_hash="",
            chunk_hash="",
            query_hash=query_hash,
            timestamp=timestamp,
            message=f"Error consultando Weaviate o schema ausente en {RAG_QUERY_CLASS}",
            traceable=True
        )
    
    # Verificar si hay hits
    if len(chunks) == 0:
        logger.warning("RAG: 0 chunks recuperados (no hay contenido relevante)")
        return RagPreflight(
            preflight_ok=False,
            status="RAG_NO_HITS",
            session_id=session_id,
            chunks_recovered=0,
            source_hash="",
            chunk_hash="",
            query_hash=query_hash,
            timestamp=timestamp,
            message="RAG: 0 chunks encontrados (pregunta no tiene contenido en Weaviate)",
            traceable=True
        )
    
    # Éxito: calcular hashes
    logger.info(f"Step 3: Calculando hashes de {len(chunks)} chunks...")
    chunk_hash = calculate_chunks_hash(chunks)
    source_hash = calculate_source_hash(chunks)
    
    logger.info(f"✓ Preflight RAG OK: {len(chunks)} chunks, hashes calculados")
    
    return RagPreflight(
        preflight_ok=True,
        status="OK",
        session_id=session_id,
        chunks_recovered=len(chunks),
        source_hash=source_hash,
        chunk_hash=chunk_hash,
        query_hash=query_hash,
        timestamp=timestamp,
        message=f"RAG OK: {len(chunks)} chunks recuperados",
        traceable=True
    )


def write_preflight_log(
    preflight: RagPreflight,
    task_id: str,
    log_path: Optional[Path] = None
) -> bool:
    """
    Escribe resultado de preflight en log JSONL.
    Ubicación: 00_sistema_tesis/bitacora/preflight_rag_log.jsonl
    """
    if log_path is None:
        log_path = Path("00_sistema_tesis/bitacora/preflight_rag_log.jsonl")
    
    try:
        log_entry = {
            "timestamp": preflight["timestamp"],
            "task_id": task_id,
            "session_id": preflight["session_id"],
            "preflight_ok": preflight["preflight_ok"],
            "status": preflight["status"],
            "chunks_recovered": preflight["chunks_recovered"],
            "source_hash": preflight["source_hash"],
            "chunk_hash": preflight["chunk_hash"],
            "query_hash": preflight["query_hash"],
            "message": preflight["message"],
            "traceable": preflight["traceable"]
        }
        
        # Append a JSONL (no sobrescribir)
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        logger.info(f"Logged to {log_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to write preflight log: {str(e)}")
        return False


def _write_output(preflight: RagPreflight, output_path: Optional[str]) -> None:
    payload = json.dumps(preflight, ensure_ascii=False, indent=2)
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(payload, encoding="utf-8")
    else:
        print(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight RAG obligatorio")
    parser.add_argument("--task-id", required=True, help="ID de la tarea")
    parser.add_argument("--question", required=True, help="Pregunta o contexto a consultar")
    parser.add_argument("--context", default=None, help="Contexto opcional")
    parser.add_argument("--requires-rag", dest="requires_rag", action="store_true", default=True)
    parser.add_argument("--no-rag", dest="requires_rag", action="store_false")
    parser.add_argument("--output", default=None, help="Ruta opcional para escribir JSON de salida")

    args = parser.parse_args()

    preflight = run_preflight(
        task_id=args.task_id,
        question=args.question,
        context_hint=args.context,
        requires_rag=args.requires_rag,
    )
    write_preflight_log(preflight, args.task_id)
    _write_output(preflight, args.output)

    return 0 if preflight["preflight_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
