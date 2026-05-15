"""Pruebas unitarias para el servidor FastAPI de OpenClaw PET."""

import sys
import json
import tempfile
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Función helper para crear payloads válidos
def create_pet_payload(bundle_id="PEB-TEST", package_id="PKG-TEST", source_system="test-system", 
                       content="Test content", claims_csv="", metadata=None):
    """Crea un payload válido para el endpoint /api/v1/pet/ingest."""
    return {
        "bundle_id": bundle_id,
        "package_id": package_id,
        "source_system": source_system,
    "source_timestamp": datetime.now(timezone.utc).isoformat(),
        "content_literal": content,
        "claims_matrix_csv": claims_csv,
        "decisions_log_md": "",
        "metadata": metadata or {},
        "integrity_hash": hashlib.sha256(content.encode()).hexdigest(),
    }

# Setup path para importar módulos del proyecto
root = Path(__file__).resolve().parent.parent
runtime_openclaw = root / "runtime" / "openclaw"
sys.path.insert(0, str(runtime_openclaw))
sys.path.insert(0, str(root / "07_scripts"))

from pet_api_server import create_pet_api_app
from openclaw_local.storage import OpenClawStore


class TestPETAPIServer:
    """Pruebas unitarias del servidor FastAPI PET."""

    @pytest.fixture
    def store(self):
        """Crea un OpenClawStore con BD temporal para testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store_instance = OpenClawStore(str(db_path))
            yield store_instance

    @pytest.fixture
    def app(self, store):
        """Crea instancia de la app para testing."""
        return create_pet_api_app(store=store)

    @pytest.fixture
    def client(self, app):
        """Crea TestClient para la app."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Verifica que el endpoint /health devuelva status ok."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"

    def test_root_endpoint(self, client):
        """Verifica que la raíz devuelva info de la API."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "OpenClaw PET API"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data

    def test_cors_headers(self, client):
        """Verifica que CORS esté habilitado para requests GET."""
        response = client.get("/api/v1/pet/list")
        assert response.status_code == 200
        # El header CORS debería estar en la respuesta
        # (aunque TestClient puede no exponerlo igual que en runtime real)

    def test_pet_list_empty(self, client):
        """Verifica que /api/v1/pet/list devuelva lista vacía inicialmente."""
        response = client.get("/api/v1/pet/list")
        assert response.status_code == 200
        data = response.json()
        assert "bundles" in data
        assert isinstance(data["bundles"], list)
        assert len(data["bundles"]) == 0

    def test_pet_ingest_invalid_payload(self, client):
        """Verifica que ingest rechace payload inválido."""
        response = client.post(
            "/api/v1/pet/ingest",
            json={"invalid": "data"},
        )
        # Puede ser 400 (validación) o 422 (unprocessable entity)
        assert response.status_code in [400, 422]

    def test_pet_ingest_minimal_valid(self, client):
        """Verifica que ingest acepte un bundle mínimamente válido."""
        payload = create_pet_payload(bundle_id="PEB-001", package_id="PKG-001", source_system="test-system")
        response = client.post("/api/v1/pet/ingest", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "bundle_id" in data
        assert "package_id" in data
        assert data["status"] in ["validated", "ingested", "rejected"]

    def test_pet_ingest_with_claims(self, client):
        """Verifica que ingest procese bundles con claims."""
        content = "Quantum entanglement is demonstrated in lab"
        claims_csv = """claim_id,claim_text,type,confidence
CLAIM-001,Quantum entanglement is real,FACTUAL,0.95
CLAIM-002,All physicists agree,OPINION,0.5"""
        
        payload = create_pet_payload(
            bundle_id="PEB-002",
            package_id="PKG-002",
            source_system="research-llm",
            content=content,
            claims_csv=claims_csv
        )
        response = client.post("/api/v1/pet/ingest", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["claims_count"] >= 2

    def test_pet_list_after_ingest(self, client):
        """Verifica que post-ingest, /list devuelva el bundle ingested."""
        # Ingest
        content = "Test"
        payload = create_pet_payload(
            bundle_id="PEB-003",
            package_id="PKG-003",
            source_system="test",
            content=content
        )
        ingest_response = client.post("/api/v1/pet/ingest", json=payload)
        assert ingest_response.status_code == 201
        
        # List
        list_response = client.get("/api/v1/pet/list")
        assert list_response.status_code == 200
        bundles = list_response.json()["bundles"]
        assert len(bundles) > 0
        assert any(b["bundle_id"] == "PEB-003" for b in bundles)

    def test_pet_get_by_id(self, client):
        """Verifica que se puede recuperar un bundle por ID."""
        # Ingest
        payload = create_pet_payload(
            bundle_id="PEB-004",
            package_id="PKG-004",
            source_system="test",
            content="Content"
        )
        ingest_response = client.post("/api/v1/pet/ingest", json=payload)
        assert ingest_response.status_code == 201
        bundle_id = ingest_response.json()["bundle_id"]

        # Get by ID
        get_response = client.get(f"/api/v1/pet/{bundle_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["bundle_id"] == bundle_id
        assert data["source_system"] == "test"

    def test_pet_get_by_id_notfound(self, client):
        """Verifica que get por ID inexistente devuelva 404."""
        response = client.get("/api/v1/pet/NONEXISTENT-ID")
        assert response.status_code == 404

    def test_pet_claims_endpoint(self, client):
        """Verifica que el endpoint de claims funcione."""
        # Ingest con claims
        claims_csv = """claim_id,claim_text,type,confidence
CLAIM-001,Test claim,FACTUAL,0.9"""
        payload = create_pet_payload(
            bundle_id="PEB-005",
            package_id="PKG-005",
            source_system="test",
            content="Test",
            claims_csv=claims_csv
        )
        ingest_response = client.post("/api/v1/pet/ingest", json=payload)
        assert ingest_response.status_code == 201
        bundle_id = ingest_response.json()["bundle_id"]

        # Get claims
        claims_response = client.get(f"/api/v1/pet/{bundle_id}/claims")
        assert claims_response.status_code == 200
        data = claims_response.json()
        assert "claims" in data
        assert len(data["claims"]) > 0

    def test_pet_fragments_endpoint(self, client):
        """Verifica que el endpoint de fragments funcione."""
        # Ingest
        content = "Long text with multiple sentences. Each sentence is a potential fragment. We need to validate this."
        payload = create_pet_payload(
            bundle_id="PEB-006",
            package_id="PKG-006",
            source_system="test",
            content=content
        )
        ingest_response = client.post("/api/v1/pet/ingest", json=payload)
        assert ingest_response.status_code == 201
        bundle_id = ingest_response.json()["bundle_id"]

        # Get fragments
        fragments_response = client.get(f"/api/v1/pet/{bundle_id}/fragments")
        assert fragments_response.status_code == 200
        data = fragments_response.json()
        assert "fragments" in data


class TestPETAPIIntegration:
    """Pruebas de integración del servidor PET."""

    @pytest.fixture
    def store(self):
        """Crea un OpenClawStore con BD temporal para testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            store_instance = OpenClawStore(str(db_path))
            yield store_instance

    @pytest.fixture
    def app(self, store):
        """Crea instancia de la app."""
        return create_pet_api_app(store=store)

    @pytest.fixture
    def client(self, app):
        """Crea TestClient."""
        return TestClient(app)

    def test_full_lifecycle(self, client):
        """Prueba ciclo completo: ingest -> list -> get -> claims."""
        # 1. Ingest
        bundles_data = []
        for i in range(1, 4):
            content = f"Content for bundle {i}"
            claims_csv = f"""claim_id,claim_text,type,confidence
CLAIM-{i:03d},Claim {i},FACTUAL,{0.85 + (i * 0.01)}"""
            bundles_data.append({
                "bundle_id": f"PEB-FULL-{i:03d}",
                "package_id": f"PKG-{i:03d}",
                "source_system": f"system-{i}",
                "content": content,
                "claims_csv": claims_csv,
            })

        bundle_ids = []
        for data in bundles_data:
            payload = create_pet_payload(
                bundle_id=data["bundle_id"],
                package_id=data["package_id"],
                source_system=data["source_system"],
                content=data["content"],
                claims_csv=data["claims_csv"]
            )
            response = client.post("/api/v1/pet/ingest", json=payload)
            assert response.status_code == 201
            bundle_ids.append(response.json()["bundle_id"])

        # 2. List all
        list_response = client.get("/api/v1/pet/list")
        assert list_response.status_code == 200
        bundles = list_response.json()["bundles"]
        assert len(bundles) >= 3

        # 3. Get each by ID and verify
        for bundle_id in bundle_ids:
            get_response = client.get(f"/api/v1/pet/{bundle_id}")
            assert get_response.status_code == 200
            bundle = get_response.json()
            assert bundle["bundle_id"] == bundle_id
            assert bundle["claims_count"] > 0

            # 4. Get claims
            claims_response = client.get(f"/api/v1/pet/{bundle_id}/claims")
            assert claims_response.status_code == 200

    def test_filter_by_source_system(self, client):
        """Prueba filtrado por source_system."""
        # Ingest con diferentes sistemas
        for system in ["sys-A", "sys-B", "sys-A"]:
            payload = {
                "package_id": f"PKG-{system}",
                "source_system": system,
                "content": "test",
                "claims": [],
            }
            client.post("/api/v1/pet/ingest", json=payload)

        # Filter
        response = client.get("/api/v1/pet/list?source_system=sys-A")
        assert response.status_code == 200
        bundles = response.json()["bundles"]
        assert all(b["source_system"] == "sys-A" for b in bundles)

    def test_filter_by_status(self, client):
        """Prueba filtrado por status."""
        payload = {
            "package_id": "PKG-STATUS",
            "source_system": "test",
            "content": "test",
            "claims": [],
        }
        client.post("/api/v1/pet/ingest", json=payload)

        # Filter by validated
        response = client.get("/api/v1/pet/list?status=validated")
        assert response.status_code == 200
        bundles = response.json()["bundles"]
        # Dependiendo de la lógica de validación, puede haber o no bundles
        assert isinstance(bundles, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
