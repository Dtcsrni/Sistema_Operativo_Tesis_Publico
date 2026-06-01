#!/usr/bin/env python3
"""start_backends_auto.py - Levanta automáticamente Ollama en Edge si está caído."""

import os
import sys
import socket
import time
import platform
import subprocess
from pathlib import Path


def check_backend_ready(host, port, timeout=3):
    """Verifica si un backend esta disponible."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except Exception:
        return False


def start_ollama_edge():
    """Intenta iniciar Ollama en Orange Pi (via SSH)."""
    print("[CHECK] Intentando iniciar Ollama en Orange Pi (192.168.1.124)...")

    orangepi_ip = "192.168.1.124"
    orangepi_user = "tesisai"
    orangepi_port = 22

    key_path = os.getenv("ORANGEPI_KEY_PATH", str(Path.home() / ".ssh" / "orangepi_rsa"))


    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["ping", "-n", "1", orangepi_ip],
                capture_output=True,
                timeout=5
            )
        else:
            result = subprocess.run(
                ["ping", "-c", "1", orangepi_ip],
                capture_output=True,
                timeout=5
            )

        if result.returncode != 0:
            print("[NO] No se puede alcanzar Orange Pi ({})".format(orangepi_ip))
            return False

        print("[OK] Orange Pi disponible ({})".format(orangepi_ip))

        ssh_cmd = [
            "ssh",
            "-i", key_path,
            "-p", str(orangepi_port),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=5",
            "{}@{}".format(orangepi_user, orangepi_ip),
            "systemctl restart ollama || ollama serve --host 0.0.0.0:11434 &"
        ]

        print("[SSH] Conectando via SSH...")
        result = subprocess.run(ssh_cmd, capture_output=True, timeout=15, text=True)

        if result.returncode == 0:
            print("[OK] Ollama iniciado en Orange Pi")
            for _ in range(10):
                time.sleep(1)
                if check_backend_ready("192.168.1.124", 11434):
                    print("[OK] Ollama en Orange Pi respondiendo")
                    return True
            print("[WAIT] Ollama en Orange Pi iniciado pero aun preparando...")
            return True
        else:
            print("[NO] SSH fallo: {}".format(result.stderr[:100]))
            return False

    except Exception as e:
        print("[NO] Error SSH: {}: {}".format(type(e).__name__, str(e)[:80]))
        return False


def ensure_backends_ready(verbose=False):
    """Verifica disponibilidad de backend Edge y lo inicia si es necesario."""
    status = {"edge": False, "timestamp": time.time()}

    edge_host = "192.168.1.124"
    edge_port = 11434
    print("\n" + "="*70)
    print("VERIFICACION Y AUTOARRANQUE DE BACKENDS")
    print("="*70 + "\n")

    print("1) Edge (Ollama - Orange Pi 192.168.1.124:11434)")
    if check_backend_ready(edge_host, edge_port):
        print("   [OK] Disponible")
        status["edge"] = True
    else:
        print("   [NO] No disponible - Intentando iniciar...")
        if start_ollama_edge():
            status["edge"] = True
        else:
            print("   [WARN] No se pudo iniciar Edge automaticamente")

    print("\n" + "="*70)
    print("RESULTADO")
    print("="*70)

    if status["edge"]:
        print("[OK] Edge disponible")
        print("   Edge (Ollama):        [OK]")
    else:
        print("[CRITICAL] Edge caido")
        print("   Edge (Ollama):        [NO]")

    print("="*70 + "\n")

    return status


if __name__ == "__main__":
    status = ensure_backends_ready(verbose=True)
    sys.exit(0 if status["edge"] else 1)
