"""Web API endpoints para ingesta y consulta de PET bundles en OpenClaw."""

from __future__ import annotations

import json
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.responses import JSONResponse
except ImportError:
    FastAPI = None
    HTTPException = None
    Query = None
    JSONResponse = None


def register_pet_routes(app: FastAPI, store: Any) -> None:
    """Registra rutas REST para gestión de PET bundles.

    Args:
        app: Instancia FastAPI
        store: OpenClawStore para persistencia
    """
    from .epistemic import ingest_pet_bundle, sha256_dict, audit_pet_bundle_claims, extract_fragments_from_content_literal

    @app.post("/api/v1/pet/ingest", status_code=201)
    async def ingest_pet_bundle_endpoint(request: dict[str, Any]) -> dict[str, Any]:
        """Ingesta un PET bundle desde JSON.

        Request body:
        ```json
        {
          "bundle_id": "PEB-...",
          "package_id": "PKG-...",
          "source_system": "ResearchLLM-v2",
          "source_timestamp": "2026-05-02T...",
          "content_literal": "FRAGMENTO: ...",
          "claims_matrix_csv": "claim_id,...",
          "decisions_log_md": "# Decisiones",
          "metadata": {...},
          "integrity_hash": "sha256:..."
        }
        ```

        Returns:
        ```json
        {
          "status": "validated|ingested|rejected",
          "bundle_id": "PEB-...",
          "package_id": "PKG-...",
          "claims_count": 2,
          "fragments_count": 1,
          "validation_errors": [],
          "message": "OK"
        }
        ```
        """
        try:
            # Extraer campos
            bundle_id = request.get("bundle_id", "")
            package_id = request.get("package_id", "")
            source_system = request.get("source_system", "")
            source_timestamp = request.get("source_timestamp", "")
            content_literal = request.get("content_literal", "")
            claims_matrix_csv = request.get("claims_matrix_csv", "")
            decisions_log_md = request.get("decisions_log_md", "")
            metadata = request.get("metadata", {})
            integrity_hash = request.get("integrity_hash", "")

            if not all([bundle_id, package_id, source_system, source_timestamp, integrity_hash]):
                raise ValueError("Campos requeridos faltando: bundle_id, package_id, source_system, source_timestamp, integrity_hash")

            # Validar e ingestar
            result, validation_errors = ingest_pet_bundle(
                bundle_id=bundle_id,
                package_id=package_id,
                source_system=source_system,
                source_timestamp=source_timestamp,
                content_literal=content_literal,
                claims_matrix_csv=claims_matrix_csv,
                decisions_log_md=decisions_log_md,
                metadata=metadata,
                integrity_hash=integrity_hash,
            )

            # Persistir
            store.ingest_pet_bundle(
                bundle_id=result.bundle_id,
                package_id=result.package_id,
                source_system=result.source_system,
                source_timestamp=result.source_timestamp,
                content_literal=content_literal,
                claims_matrix_csv=claims_matrix_csv,
                decisions_log_md=decisions_log_md,
                metadata=metadata,
                integrity_hash=result.integrity_hash,
                status=result.status,
                claims_count=result.claims_count,
                fragments_count=result.fragments_count,
            )

            return {
                "status": result.status,
                "bundle_id": result.bundle_id,
                "package_id": result.package_id,
                "claims_count": result.claims_count,
                "fragments_count": result.fragments_count,
                "validation_errors": validation_errors,
                "message": "OK" if validation_errors == [] else "Validado con advertencias",
            }

        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/v1/pet/list")
    async def list_pet_bundles_endpoint(
        source_system: str | None = Query(None),
        status: str | None = Query(None),
        limit: int = Query(10, ge=1, le=100),
    ) -> dict[str, Any]:
        """Lista PET bundles ingestados con filtros opcionales.

        Query parameters:
        - source_system: Filtrar por sistema origen (ej. ResearchLLM-v2)
        - status: Filtrar por estado (validated|ingested|rejected)
        - limit: Máximo de resultados (default 10, max 100)

        Returns:
        ```json
        {
          "total": 5,
          "bundles": [
            {
              "bundle_id": "PEB-...",
              "package_id": "PKG-...",
              "source_system": "...",
              "status": "validated",
              "claims_count": 2,
              "created_at": "..."
            },
            ...
          ]
        }
        ```
        """
        bundles = store.list_ingested_pet_bundles(
            source_system=source_system,
            status=status,
            limit=limit,
        )

        return {
            "total": len(bundles),
            "bundles": [
                {
                    "bundle_id": b.get("bundle_id"),
                    "package_id": b.get("package_id"),
                    "source_system": b.get("source_system"),
                    "status": b.get("status"),
                    "claims_count": b.get("claims_count"),
                    "fragments_count": b.get("fragments_count"),
                    "created_at": b.get("created_at"),
                }
                for b in bundles
            ],
        }

    @app.get("/api/v1/pet/{bundle_id}")
    async def get_pet_bundle_endpoint(bundle_id: str) -> dict[str, Any]:
        """Recupera un PET bundle específico.

        Args:
            bundle_id: ID del bundle (ej. PEB-abc123)

        Returns:
        ```json
        {
          "bundle_id": "PEB-...",
          "package_id": "PKG-...",
          "source_system": "ResearchLLM-v2",
          "source_timestamp": "...",
          "integrity_hash": "...",
          "status": "validated",
          "claims_count": 2,
          "fragments_count": 1,
          "created_at": "2026-05-02T..."
        }
        ```
        """
        bundle = store.get_pet_bundle_by_id(bundle_id)
        if bundle is None:
            raise HTTPException(status_code=404, detail=f"Bundle {bundle_id} no encontrado")

        return {
            "bundle_id": bundle.get("bundle_id"),
            "package_id": bundle.get("package_id"),
            "source_system": bundle.get("source_system"),
            "source_timestamp": bundle.get("source_timestamp"),
            "integrity_hash": bundle.get("integrity_hash"),
            "status": bundle.get("status"),
            "claims_count": bundle.get("claims_count"),
            "fragments_count": bundle.get("fragments_count"),
            "created_at": bundle.get("created_at"),
            "content_literal": bundle.get("content_literal", "")[: 500],  # Preview
        }

    @app.get("/api/v1/pet/{bundle_id}/claims")
    async def get_bundle_claims_endpoint(bundle_id: str) -> dict[str, Any]:
        """Recupera los claims auditados de un bundle.

        Args:
            bundle_id: ID del bundle

        Returns:
        ```json
        {
          "bundle_id": "PEB-...",
          "claims": [
            {
              "claim_id": "C001",
              "afirmacion": "...",
              "estado_auditoria": "aprobado|pendiente|bloqueado",
              "hash_soporte": "...",
              "observaciones": "..."
            },
            ...
          ]
        }
        ```
        """
        from .epistemic import audit_pet_bundle_claims

        bundle = store.get_pet_bundle_by_id(bundle_id)
        if bundle is None:
            raise HTTPException(status_code=404, detail=f"Bundle {bundle_id} no encontrado")

        audited, errors = audit_pet_bundle_claims(claims_matrix_csv=bundle.get("claims_matrix_csv", ""))

        return {
            "bundle_id": bundle_id,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "afirmacion": c.afirmacion,
                    "tipo_afirmacion": c.tipo_afirmacion,
                    "estado_auditoria": c.estado_auditoria,
                    "hash_soporte": c.hash_soporte,
                    "autoridad": c.autoridad,
                    "certeza": c.certeza,
                    "observaciones": c.observaciones,
                }
                for c in audited
            ],
            "audit_errors": errors,
        }

    @app.get("/api/v1/pet/{bundle_id}/fragments")
    async def get_bundle_fragments_endpoint(bundle_id: str) -> dict[str, Any]:
        """Recupera los fragmentos académicos de un bundle.

        Args:
            bundle_id: ID del bundle

        Returns:
        ```json
        {
          "bundle_id": "PEB-...",
          "fragments": [
            {
              "fragment_id": "F001",
              "hash_sha256": "abc123...",
              "authority": "ResearchPaper",
              "certainty": "Alta",
              "fundamento": "doi:...",
              "text_literal": "..."
            },
            ...
          ]
        }
        ```
        """
        from .epistemic import extract_fragments_from_content_literal

        bundle = store.get_pet_bundle_by_id(bundle_id)
        if bundle is None:
            raise HTTPException(status_code=404, detail=f"Bundle {bundle_id} no encontrado")

        fragments = extract_fragments_from_content_literal(bundle.get("content_literal", ""))

        return {
            "bundle_id": bundle_id,
            "fragments": fragments,
        }
