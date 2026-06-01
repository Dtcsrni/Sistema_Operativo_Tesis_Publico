#!/usr/bin/env python3
"""
ingest_meta_docs.py -- Indexa la documentación del sistema en Toltecayotl.
Permite que el asistente tenga "consciencia" de su propia arquitectura y decisiones.
"""

import os
import sys
from pathlib import Path
import hashlib
from datetime import datetime, UTC
from uuid import uuid4

# Añadir el path para importar módulos de openclaw_local
repo_root = Path(__file__).resolve().parents[2]
sys.path.append(str(repo_root))

from runtime.openclaw.openclaw_local.toltecayotl_ingestor import ToltecayotlChunk
from runtime.openclaw.openclaw_local.toltecayotl_knowledge import upsert_chunks

def get_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def process_file(path: Path, source_type: str) -> list[ToltecayotlChunk]:
    if not path.exists():
        return []
    
    text = path.read_text(encoding="utf-8", errors="replace")
    source_hash = get_file_hash(path)
    
    # Fragmentación simple por encabezados o párrafos largos
    # En un entorno real, usaríamos un text splitter más avanzado
    chunks = []
    sections = text.split("\n## ")
    created_at = datetime.now(UTC).isoformat()
    
    for i, section in enumerate(sections):
        chunk_text = section if i == 0 else "## " + section
        if len(chunk_text.strip()) < 50:
            continue
            
        chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
        chunks.append(ToltecayotlChunk(
            chunk_id=f"SYS-{uuid4().hex[:12]}",
            source_path=str(path.relative_to(repo_root)),
            source_type=source_type,
            source_hash=source_hash,
            chunk_index=i,
            chunk_hash=chunk_hash,
            text=chunk_text,
            verification_status="system_verified",
            metadata={
                "ingested_at": created_at,
                "priority": "high" if source_type == "meta" else "medium"
            },
            created_at=created_at
        ))
    return chunks

def main():
    print(f"--- Iniciando Ingesta de Consciencia de Sistema ---")
    
    files_to_index = [
        (repo_root / "README.md", "meta"),
        (repo_root / "00_sistema_tesis" / "CONTEXT.md", "glossary"),
        (repo_root / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md", "ledger"),
    ]
    
    # Decisiones
    decisiones_dir = repo_root / "00_sistema_tesis" / "decisiones"
    if decisiones_dir.exists():
        for f in decisiones_dir.glob("*.md"):
            files_to_index.append((f, "decision"))

    all_chunks = []
    for path, stype in files_to_index:
        if path.exists():
            print(f"Procesando: {path.name} ({stype})...")
            all_chunks.extend(process_file(path, stype))

    if not all_chunks:
        print("No se encontraron archivos para indexar.")
        return

    print(f"Insertando {len(all_chunks)} fragmentos en Toltecayotl...")
    result = upsert_chunks(repo_root, all_chunks)
    
    if result["status"] == "ok":
        print(f"[SUCCESS] Ingesta completada. {result['local_records_added']} registros añadidos.")
        print(f"Estado Weaviate: {result.get('weaviate_status')}")
    else:
        print(f"[FAIL] Error en la ingesta: {result}")

if __name__ == "__main__":
    main()
