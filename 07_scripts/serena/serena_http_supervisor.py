from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



import argparse
import os
import signal
import socket
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_ENDPOINT = "/mcp"

def detect_python_bin(root: Path) -> str:
    if os.name == "nt":
        candidates = [
            root / ".venv" / "Scripts" / "python.exe",
            root / ".venv" / "bin" / "python.exe",
        ]
    else:
        candidates = [
            root / ".venv" / "bin" / "python",
            Path(sys.executable) if sys.executable else Path("python3"),
            root / ".venv" / "bin" / "python.exe",
        ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable or "python3"

def port_open(host: str, port: int, timeout: float = 0.3) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0

def wait_for_port(host: str, port: int, deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        if port_open(host, port):
            return True
        time.sleep(0.2)
    return False

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Supervisa Serena HTTP para tareas IDE de larga vida.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--startup-timeout", type=float, default=8.0)
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    host = str(args.host)
    port = int(args.port)
    endpoint = str(args.endpoint)
    env = dict(os.environ)
    env["SISTEMA_TESIS_ROOT"] = str(ROOT)
    env.setdefault(
        "SERENA_MCP_DEBUG_LOG",
        str(ROOT / "00_sistema_tesis" / "bitacora" / "audit_history" / "serena_mcp_debug.log"),
    )
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONUTF8", "1")

    if port_open(host, port):
        print(f"HTTP_READY http://{host}:{port}{endpoint}", flush=True)
        print("[serena-http-supervisor] Serena HTTP ya estaba escuchando; manteniendo tarea IDE viva.", flush=True)
        try:
            while port_open(host, port, timeout=1.0):
                time.sleep(2.0)
        except KeyboardInterrupt:
            return 0
        return 0

    python_bin = detect_python_bin(ROOT)
    server_script = ROOT / "07_scripts" / "serena_mcp.py"
    process = subprocess.Popen(
        [
            python_bin,
            "-u",
            str(server_script),
            "--transport",
            "http",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
    )

    stopping = False

    def stop_child(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True
        if process.poll() is None:
            process.terminate()

    signal.signal(signal.SIGTERM, stop_child)
    signal.signal(signal.SIGINT, stop_child)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, stop_child)

    if not wait_for_port(host, port, float(args.startup_timeout)):
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        print(f"[serena-http-supervisor] No se logro levantar http://{host}:{port}{endpoint}", file=sys.stderr)
        return 1

    print(f"HTTP_READY http://{host}:{port}{endpoint}", flush=True)
    print(f"[serena-http-supervisor] Serena HTTP iniciado pid={process.pid}", flush=True)
    while process.poll() is None:
        time.sleep(0.5)

    if stopping:
        print("[serena-http-supervisor] Serena HTTP detenido por cierre del IDE.", flush=True)
        return 0
    return int(process.returncode or 0)

if __name__ == "__main__":
    raise SystemExit(main())
