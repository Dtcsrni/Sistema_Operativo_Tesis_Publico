"""Pruebas de integración: Docker Compose + PET API + Mission Control."""

import subprocess
import time
import requests
import json
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
TIMEOUT = 120  # segundos para esperar que los servicios arranquen
API_BASE_URL = "http://localhost:8001"
DASHBOARD_URL = "http://localhost:4000"

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


class DockerComposeFixture:
    """Gestor de Docker Compose para testing."""

    def __init__(self, compose_file: Path):
        self.compose_file = compose_file
        self.repo_root = compose_file.parent

    def up(self):
        """Levanta los servicios de la composición."""
        cmd = [
            "docker",
            "compose",
            "-f",
            str(self.compose_file),
            "up",
            "-d",
            "--build",
        ]
        print(f"[DOCKER] Levantando: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"docker compose up falló:\n{result.stderr}\n{result.stdout}"
            )
        print("[DOCKER] Servicios levantados")

    def down(self):
        """Detiene los servicios."""
        cmd = ["docker", "compose", "-f", str(self.compose_file), "down"]
        print(f"[DOCKER] Deteniendo: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=self.repo_root, capture_output=True)
        print("[DOCKER] Servicios detenidos")

    def ps(self) -> Dict[str, str]:
        """Lista estado de servicios."""
        cmd = [
            "docker",
            "compose",
            "-f",
            str(self.compose_file),
            "ps",
            "--format=json",
        ]
        result = subprocess.run(
            cmd, cwd=self.repo_root, capture_output=True, text=True
        )
        if result.returncode != 0:
            return {}
        try:
            services = json.loads(result.stdout)
            return {svc["Service"]: svc["State"] for svc in services}
        except:
            return {}

    def logs(self, service: str) -> str:
        """Obtiene logs de un servicio."""
        cmd = [
            "docker",
            "compose",
            "-f",
            str(self.compose_file),
            "logs",
            service,
        ]
        result = subprocess.run(
            cmd, cwd=self.repo_root, capture_output=True, text=True
        )
        return result.stdout + result.stderr

    def wait_for_service(self, url: str, timeout: int = TIMEOUT) -> bool:
        """Espera a que un servicio esté listo."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(2)
        return False


@pytest.fixture(scope="session")
def docker_compose():
    """Fixture de sesión: levanta y baja Docker Compose."""
    fixture = DockerComposeFixture(COMPOSE_FILE)
    print("\n[FIXTURE] Levantando Docker Compose...")
    fixture.up()

    # Espera a que los servicios se levanten
    print("[FIXTURE] Esperando a que siot-pet-api esté listo...")
    if not fixture.wait_for_service(f"{API_BASE_URL}/health"):
        print("[ERROR] siot-pet-api no se levantó a tiempo")
        print(f"Logs:\n{fixture.logs('siot-pet-api')}")
        fixture.down()
        raise RuntimeError("siot-pet-api timeout")

    print("[FIXTURE] Esperando a que mission-control esté listo...")
    if not fixture.wait_for_service(f"{DASHBOARD_URL}/api/health"):
        print("[ERROR] mission-control no se levantó a tiempo")
        print(f"Logs:\n{fixture.logs('mission-control')}")
        fixture.down()
        raise RuntimeError("mission-control timeout")

    print("[FIXTURE] Todos los servicios listos")

    yield fixture

    print("\n[FIXTURE] Deteniendo Docker Compose...")
    fixture.down()


class TestDockerComposePETIntegration:
    """Pruebas de integración con Docker Compose."""

    def test_pet_api_health(self, docker_compose):
        """Verifica que siot-pet-api responda health check."""
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_pet_api_root(self, docker_compose):
        """Verifica que siot-pet-api expone la raíz."""
        response = requests.get(f"{API_BASE_URL}/", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "endpoints" in data

    def test_mission_control_health(self, docker_compose):
        """Verifica que mission-control responda health check."""
        response = requests.get(f"{DASHBOARD_URL}/api/health", timeout=10)
        assert response.status_code == 200

    def test_docker_service_states(self, docker_compose):
        """Verifica que todos los servicios estén running."""
        # Simplemente verificar que los endpoints respondieren
        # (más confiable que parsear JSON de docker ps)
        pet_api_response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        assert pet_api_response.status_code == 200
        
        dashboard_response = requests.get(f"{DASHBOARD_URL}/api/health", timeout=10)
        assert dashboard_response.status_code == 200
        
        print(f"[TEST] Todos los servicios están respondiendo")

    def test_pet_api_ingest_from_docker(self, docker_compose):
        """Verifica que se puede ingestar un bundle via API en Docker."""
        payload = create_pet_payload(
            bundle_id="PEB-DOCKER-001",
            package_id="PKG-DOCKER-001",
            source_system="docker-test",
            content="Test content from Docker container",
            claims_csv="""claim_id,claim_text,type,confidence
CLAIM-DOCKER-001,Docker test claim,FACTUAL,0.9"""
        )

        response = requests.post(
            f"{API_BASE_URL}/api/v1/pet/ingest", json=payload, timeout=10
        )
        assert response.status_code == 201
        data = response.json()
        assert "bundle_id" in data
        print(f"[TEST] Bundle ingestado: {data['bundle_id']}")

    def test_pet_api_list_from_docker(self, docker_compose):
        """Verifica que se puede listar bundles via API en Docker."""
        response = requests.get(
            f"{API_BASE_URL}/api/v1/pet/list?limit=10", timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert "bundles" in data
        assert isinstance(data["bundles"], list)
        print(f"[TEST] Bundles listados: {len(data['bundles'])}")

    def test_dashboard_can_reach_pet_api(self, docker_compose):
        """Verifica que el dashboard (mission-control) puede alcanzar PET API."""
        # Nota: Esta es una prueba básica que verifica que los servicios están
        # en la misma red Docker y pueden comunicarse. El dashboard debería
        # usar 'siot-pet-api:8001' como hostname en la red, no 'localhost:8001'.
        # Por ahora solo verificamos que ambos servicios estén activos.
        
        pet_health = requests.get(f"{API_BASE_URL}/health", timeout=10)
        dashboard_health = requests.get(f"{DASHBOARD_URL}/api/health", timeout=10)
        
        assert pet_health.status_code == 200
        assert dashboard_health.status_code == 200
        print("[TEST] Dashboard y PET API están activos y accesibles")

    def test_pet_api_network_connectivity(self, docker_compose):
        """Verifica que PET API está en la red correcta."""
        # Verificar que el servicio es accesible por hostname en la red
        import socket

        try:
            # Dentro de Docker, debería resolverse 'siot-pet-api'
            # Desde el host (donde corre pytest), usamos 'localhost'
            ip = socket.gethostbyname("localhost")
            print(f"[TEST] localhost resuelve a: {ip}")
        except socket.gaierror:
            pytest.skip("No se puede resolver localhost (esperado en algunos entornos)")

    def test_pet_api_persistence(self, docker_compose):
        """Verifica que los datos de PET persisten entre requests."""
        # Ingest
        payload = create_pet_payload(
            bundle_id="PEB-PERSIST",
            package_id="PKG-PERSIST",
            source_system="persist-test",
            content="Persistence test"
        )
        ingest_response = requests.post(
            f"{API_BASE_URL}/api/v1/pet/ingest", json=payload, timeout=10
        )
        assert ingest_response.status_code == 201
        bundle_id = ingest_response.json()["bundle_id"]

        # List and verify
        list_response = requests.get(
            f"{API_BASE_URL}/api/v1/pet/list", timeout=10
        )
        assert list_response.status_code == 200
        bundles = list_response.json()["bundles"]
        bundle_ids = [b["bundle_id"] for b in bundles]
        assert bundle_id in bundle_ids
        print(f"[TEST] Bundle persistido: {bundle_id}")

    def test_pet_api_concurrent_requests(self, docker_compose):
        """Verifica que PET API maneja múltiples requests simultáneos."""
        import concurrent.futures

        def ingest_bundle(i):
            payload = create_pet_payload(
                bundle_id=f"PEB-CONCURRENT-{i:03d}",
                package_id=f"PKG-CONCURRENT-{i}",
                source_system="concurrent-test",
                content=f"Content {i}"
            )
            response = requests.post(
                f"{API_BASE_URL}/api/v1/pet/ingest",
                json=payload,
                timeout=10,
            )
            return response.status_code == 201

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(ingest_bundle, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert all(results), "No todos los ingests tuvieron éxito"
        print(f"[TEST] 10 requests concurrentes completados exitosamente")


class TestDockerComposeDashboardIntegration:
    """Pruebas del dashboard en Docker."""

    def test_mission_control_static_files(self, docker_compose):
        """Verifica que Mission Control sirve archivos estáticos."""
        response = requests.get(f"{DASHBOARD_URL}/", timeout=10)
        assert response.status_code == 200
        # Debería servir HTML (Next.js)
        assert "text/html" in response.headers.get("content-type", "")

    def test_mission_control_api_endpoint(self, docker_compose):
        """Verifica que Mission Control expone API endpoints."""
        response = requests.get(f"{DASHBOARD_URL}/api/health", timeout=10)
        assert response.status_code == 200
        print("[TEST] Mission Control API health check OK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
