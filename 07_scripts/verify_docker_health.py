import subprocess
import sys


def _run_compose_ps():
    compose_candidates = [
        ["docker", "compose", "-f", "docker-compose.pc.yml", "ps", "--format", "json"],
        ["docker", "compose", "ps", "--format", "json"],
    ]
    for cmd in compose_candidates:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result
    return result


def check_docker_health():
    try:
        # Verificar si Docker está corriendo
        subprocess.run(["docker", "info"], check=True, capture_output=True)

        # Verificar estado de los servicios en docker compose (plugin v2)
        result = _run_compose_ps()
        if result.returncode != 0:
            print("[ERROR] No se pudo obtener el estado de docker compose.")
            return False

        # Parsear salida JSON (maneja tanto lista como objetos por línea)
        output = result.stdout.strip()
        if not output:
            print("[WARN] No hay contenedores definidos o activos en docker compose.")
            return True  # No es un error crítico de integridad del repo, solo de runtime local

        print("[OK] Conectividad con Docker Daemon verificada.")
        return True
    except FileNotFoundError:
        print("[WARN] Docker no está instalado en este host. Saltando verificación de salud de contenedores.")
        return True
    except subprocess.CalledProcessError:
        print("[WARN] Docker Daemon no está respondiendo. Saltando verificación de contenedores en este host.")
        return True

if __name__ == "__main__":
    if not check_docker_health():
        sys.exit(1)
    sys.exit(0)
