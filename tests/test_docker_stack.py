import os
import pytest
import requests
import subprocess
from pathlib import Path

def is_running_in_docker():
    return os.path.exists('/.dockerenv') or os.getenv('SISTEMA_TESIS_RUNTIME', '').startswith('docker')

@pytest.mark.skipif(not is_running_in_docker(), reason="Este test solo corre dentro de los contenedores del stack")
class TestDockerStack:
    
    def test_environment_consistency(self):
        """Verifica que las variables de entorno críticas estén presentes."""
        runtime = os.getenv('SISTEMA_TESIS_RUNTIME')
        assert runtime in ['docker-docs', 'docker-agent', 'docker-test']
        assert os.getenv('PYTHONUNBUFFERED') == '1'

    def test_shared_canon_access(self):
        """Verifica el acceso al volumen compartido del Canon."""
        canon_path = Path("/app/00_sistema_tesis")
        assert canon_path.exists()
        assert (canon_path / "canon").exists()
        # Verificar que podemos leer el events.jsonl
        events_file = canon_path / "canon" / "events.jsonl"
        assert events_file.exists()
        with open(events_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            assert first_line.startswith('{')

    def test_agent_specific_dependencies(self):
        """Verifica que el agente tenga las dependencias pesadas instaladas."""
        if os.getenv('SISTEMA_TESIS_RUNTIME') == 'docker-agent':
            # Verificar FFmpeg
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            assert result.returncode == 0
            assert 'ffmpeg' in result.stdout.lower()
            
            # Verificar Playwright (importación básica)
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                assert p.chromium

    def test_docs_service_health(self):
        """Verifica que el servicio de docs responda (si estamos en la misma red)."""
        # En docker-compose, el hostname es el nombre del servicio
        try:
            response = requests.get("http://siot-docs/", timeout=5)
            assert response.status_code == 200
            assert "Dashboard" in response.text or "Wiki" in response.text
        except requests.exceptions.ConnectionError:
            if os.getenv('SISTEMA_TESIS_RUNTIME') == 'docker-docs':
                # Si soy yo mismo, pruebo localhost
                response = requests.get("http://127.0.0.1/", timeout=5)
                assert response.status_code == 200
            else:
                pytest.skip("El servicio siot-docs no es alcanzable (red distinta o no iniciado)")

def test_host_connectivity():
    """Prueba básica de conectividad a internet desde el contenedor."""
    try:
        response = requests.get("https://www.google.com", timeout=5)
        assert response.status_code == 200
    except Exception as e:
        pytest.fail(f"Sin conectividad a internet: {e}")
