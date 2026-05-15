#!/usr/bin/env python3
"""
start_backends_auto_v2.py - Levanta automaticamente backends caidos de OpenClaw.
Detecta el SO e intenta iniciar servicios faltantes sin intervención humana.
"""

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
    orangepi_user = "ErickV"
    orangepi_port = 22

    key_path = os.getenv("ORANGEPI_KEY_PATH", str(Path.home() / ".ssh" / "id_ed25519_orangepi_nopass"))

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


def start_llamacpp_desktop():
    """Intenta iniciar LlamaCPP en Desktop local."""
    print("[CHECK] Intentando iniciar LlamaCPP en Desktop (127.0.0.1:21434)...")

    env_bin = os.getenv("OPENCLAW_LLAMACPP_SERVER_BIN") or os.getenv("LLAMACPP_SERVER_BIN") or os.getenv("OPENCLAW_LLAMACPP_PATH")
    env_model = os.getenv("OPENCLAW_LLAMACPP_MODEL_PATH") or os.getenv("LLAMACPP_MODEL_PATH")
    env_bind_port = int(os.getenv("OPENCLAW_LLAMACPP_BIND_PORT", os.getenv("LLAMACPP_BIND_PORT", "21434")))
    env_bind_host = os.getenv("OPENCLAW_LLAMACPP_BIND_HOST", os.getenv("LLAMACPP_BIND_HOST", "127.0.0.1"))
    docker_image = os.getenv("OPENCLAW_LLAMACPP_DOCKER_IMAGE")
    model_host_dir = os.getenv("OPENCLAW_LLAMACPP_MODEL_HOST_DIR")

    if docker_image:
        print("[DOCKER] Intentando levantar LlamaCPP en Docker ({}) bind {}:{}...".format(docker_image, env_bind_host, env_bind_port))
        
        host_model_dir = model_host_dir
        if not host_model_dir and env_model:
            host_model_dir = str(Path(env_model).parent)

        docker_cmd = [
            "docker", "run", "--rm", "-d",
            "--name", "openclaw-llamacpp",
            "-p", "{}:{}:21434".format(env_bind_host, env_bind_port),
        ]
        
        if host_model_dir:
            docker_cmd += ["-v", "{}:/models:ro".format(host_model_dir)]
        
        docker_cmd += [docker_image]
        
        try:
            r = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                print("[OK] Contenedor LlamaCPP iniciado")
                for _ in range(20):
                    time.sleep(1)
                    if check_backend_ready(env_bind_host, env_bind_port):
                        print("[OK] LlamaCPP (docker) respondiendo")
                        return True
                print("[WAIT] Contenedor iniciado pero aun no responde")
                return True
            else:
                print("[NO] Fallo al crear contenedor: {}".format(r.stderr[:200]))
        except Exception as e:
            print("[NO] Error docker: {} {}".format(type(e).__name__, e))

    llamacpp_exe = None
    if env_bin:
        p = Path(env_bin)
        if p.is_dir():
            candidate = p / "llama-server.exe"
            if candidate.exists():
                llamacpp_exe = candidate
            else:
                candidate = p / "llama-server"
                if candidate.exists():
                    llamacpp_exe = candidate
        elif p.exists():
            llamacpp_exe = p

    if not llamacpp_exe:
        possible_paths = [
            Path("C:/Program Files/llama.cpp"),
            Path(os.path.expanduser("~/llama.cpp")),
            Path("./llama.cpp"),
            Path(os.getenv("LLAMACPP_PATH", "")),
        ]
        for base_path in possible_paths:
            if base_path and (base_path / "llama-server.exe").exists():
                llamacpp_exe = base_path / "llama-server.exe"
                break
            if base_path and (base_path / "llama-server").exists():
                llamacpp_exe = base_path / "llama-server"
                break

    if not llamacpp_exe or not llamacpp_exe.exists():
        print("[NO] LlamaCPP no encontrado en rutas estandar ni en OPENCLAW_LLAMACPP_SERVER_BIN")
        print("[NO] Buscar en: {} | env OPENCLAW_LLAMACPP_SERVER_BIN={}".format([str(p) for p in possible_paths if p], env_bin))
        return False

    print("[OK] LlamaCPP encontrado: {}".format(llamacpp_exe))

    model_path = None
    if env_model and Path(env_model).exists():
        model_path = Path(env_model)
    else:
        model_paths = [
            Path("runtime/models/pc/mistral-nemo-12b.gguf"),
            Path("models/mistral-nemo-12b.gguf"),
            Path(os.path.expanduser("~/.cache/ollama/models/mistral-nemo-12b.gguf")),
        ]
        for mp in model_paths:
            if mp.exists():
                model_path = mp
                break

    if not model_path:
        print("[NO] Modelo mistral-nemo-12b.gguf no encontrado y OPENCLAW_LLAMACPP_MODEL_PATH no definido")
        print("[NO] Busqueda en: {} | env OPENCLAW_LLAMACPP_MODEL_PATH={}".format([str(p) for p in model_paths], env_model))
        return False

    print("[OK] Modelo encontrado: {}".format(model_path))

    try:
        cmd = [
            str(llamacpp_exe),
            "-m", str(model_path),
            "-ngl", "35",
            "--port", str(env_bind_port),
            "--host", str(env_bind_host),
            "--log-format", "text"
        ]
        print("[START] Iniciando LlamaCPP (bin) {}...".format(llamacpp_exe))
        if platform.system() == "Windows":
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        for _ in range(20):
            time.sleep(1)
            if check_backend_ready(env_bind_host, env_bind_port):
                print("[OK] LlamaCPP iniciado y respondiendo")
                return True

        print("[WAIT] LlamaCPP iniciado pero aun preparando...")
        return True

    except Exception as e:
        print("[NO] Error al iniciar LlamaCPP: {}: {}".format(type(e).__name__, e))
        return False


def ensure_backends_ready(verbose=False):
    """Verifica disponibilidad de backends y los inicia si es necesario."""
    status = {"edge": False, "desktop": False, "timestamp": time.time()}

    edge_host = "192.168.1.124"
    edge_port = 11434
    desktop_host = "127.0.0.1"
    desktop_port = 21434

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

    print("\n2) Desktop (LlamaCPP - 127.0.0.1:21434)")
    if check_backend_ready(desktop_host, desktop_port):
        print("   [OK] Disponible")
        status["desktop"] = True
    else:
        print("   [NO] No disponible - Intentando iniciar...")
        if start_llamacpp_desktop():
            status["desktop"] = True
        else:
            print("   [WARN] No se pudo iniciar Desktop automaticamente")

    print("\n" + "="*70)
    print("RESULTADO")
    print("="*70)

    if status["edge"] and status["desktop"]:
        print("[OK] Todos los backends estan listos")
        print("   Edge (Ollama):        [OK]")
        print("   Desktop (LlamaCPP):   [OK]")
    elif status["edge"]:
        print("[WARN] Edge disponible, Desktop caido")
        print("   Edge (Ollama):        [OK]")
        print("   Desktop (LlamaCPP):   [NO]")
    elif status["desktop"]:
        print("[WARN] Desktop disponible, Edge caido")
        print("   Edge (Ollama):        [NO]")
        print("   Desktop (LlamaCPP):   [OK]")
    else:
        print("[CRITICAL] Ambos backends estan caidos")
        print("   Edge (Ollama):        [NO]")
        print("   Desktop (LlamaCPP):   [NO]")

    print("="*70 + "\n")

    return status


if __name__ == "__main__":
    status = ensure_backends_ready(verbose=True)
    sys.exit(0 if (status["edge"] or status["desktop"]) else 1)
