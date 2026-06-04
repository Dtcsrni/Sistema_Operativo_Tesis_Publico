#!/usr/bin/env python3
"""
siot_launcher.py — Lanzador inteligente de servicios SIOT con diagnóstico de Docker.
Este script actúa como punto de entrada para los accesos directos del usuario:
1. Verifica si el puerto destino (ej. 4000) ya está activo.
2. Si está activo, redirige de inmediato abriendo el navegador.
3. Si está inactivo (Docker apagado), arranca un servidor de diagnóstico local temporal
   en el puerto 5005 con una interfaz web premium para que el usuario inicie el stack con un clic.
"""
import os
import sys
import time
import socket
import json
import threading
import subprocess
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configuración
LAUNCHER_PORT = 5005
DOCKER_DESKTOP_PATH = r"C:\Program Files\Docker\Docker\Docker Desktop.exe"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Estado global del launcher
lock = threading.Lock()
state = {
    "status": "idle",       # idle, starting_docker, docker_ready, starting_compose, waiting_service, ready, failed
    "message": "Sistema listo para iniciar",
    "error_detail": "",
    "target_port": 4000,
    "progress": 0           # 0 to 100
}

def check_port(host: str, port: int, timeout: float = 0.5) -> bool:
    """Verifica si un puerto TCP está abierto."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((host, port)) == 0
    except Exception:
        return False

def check_docker_installed() -> bool:
    """Verifica si docker.exe está en el PATH."""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def check_docker_daemon() -> bool:
    """Verifica si el daemon de Docker responde."""
    try:
        res = subprocess.run(["docker", "info"], capture_output=True, timeout=3)
        return res.returncode == 0
    except Exception:
        return False

def check_docker_desktop_running() -> bool:
    """Verifica si el proceso Docker Desktop.exe está corriendo en Windows."""
    try:
        output = subprocess.check_output('tasklist /FI "IMAGENAME eq Docker Desktop.exe"', shell=True, text=True)
        return "Docker Desktop.exe" in output
    except Exception:
        return False

def launch_docker_desktop():
    """Inicia la aplicación de Docker Desktop."""
    if os.path.exists(DOCKER_DESKTOP_PATH):
        try:
            # os.startfile inicia el proceso de forma no bloqueante y respeta los permisos de Windows
            os.startfile(DOCKER_DESKTOP_PATH)
            return True
        except Exception as e:
            print(f"[ERROR] No se pudo ejecutar Docker Desktop con os.startfile: {e}")
            
    # Intento de fallback por subprocess
    try:
        subprocess.Popen([DOCKER_DESKTOP_PATH], start_new_session=True)
        return True
    except Exception as e:
        print(f"[ERROR] Intento alternativo de iniciar Docker Desktop falló: {e}")
        return False

def run_docker_compose():
    """Ejecuta docker compose up -d en la raíz del repo."""
    try:
        # Se buscan archivos de docker-compose
        cmd = ["docker", "compose", "up", "-d"]
        res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=90)
        if res.returncode == 0:
            return True, ""
        else:
            return False, res.stderr or res.stdout
    except Exception as e:
        return False, str(e)

def start_sequence_thread():
    """Hilo de ejecución para la secuencia de arranque del stack."""
    global state
    
    with lock:
        target_port = state["target_port"]
        state["status"] = "starting_docker"
        state["message"] = "Verificando el motor de contenedores Docker..."
        state["error_detail"] = ""
        state["progress"] = 10

    # 1. Verificar si Docker está instalado
    if not check_docker_installed():
        with lock:
            state["status"] = "failed"
            state["message"] = "Docker no está instalado en este equipo"
            state["error_detail"] = "No se encontró el comando 'docker'. Instale Docker Desktop para continuar."
            state["progress"] = 0
        return

    # 2. Verificar daemon
    if not check_docker_daemon():
        with lock:
            state["message"] = "Docker Desktop está apagado. Iniciando aplicación..."
            state["progress"] = 25
        
        # Arrancar Docker Desktop si no está corriendo el proceso
        if not check_docker_desktop_running():
            if not launch_docker_desktop():
                with lock:
                    state["status"] = "failed"
                    state["message"] = "No se pudo iniciar Docker Desktop automáticamente"
                    state["error_detail"] = f"Por favor inicie Docker Desktop manualmente desde la ruta:\n{DOCKER_DESKTOP_PATH}"
                    state["progress"] = 0
                return
        
        # Esperar a que el daemon responda
        daemon_ready = False
        for i in range(40):  # Esperar hasta 40 segundos
            time.sleep(1.5)
            with lock:
                state["message"] = f"Esperando que el motor de Docker responda... ({i+1}/40s)"
                state["progress"] = 25 + int((i / 40.0) * 25) # sube de 25% a 50%
            if check_docker_daemon():
                daemon_ready = True
                break
        
        if not daemon_ready:
            with lock:
                state["status"] = "failed"
                state["message"] = "El motor de Docker tardó demasiado en responder"
                state["error_detail"] = "Docker Desktop se inició pero el daemon no respondió a tiempo. Intente de nuevo."
                state["progress"] = 0
            return

    with lock:
        state["status"] = "docker_ready"
        state["message"] = "Motor de Docker activo. Levantando contenedores SIOT..."
        state["progress"] = 55

    # 3. Correr docker compose
    success, err_msg = run_docker_compose()
    if not success:
        with lock:
            state["status"] = "failed"
            state["message"] = "Error al ejecutar 'docker compose up -d'"
            state["error_detail"] = err_msg
            state["progress"] = 0
        return

    with lock:
        state["status"] = "starting_compose"
        state["message"] = "Contenedores creados. Esperando respuesta del portal..."
        state["progress"] = 75

    # 4. Esperar a que el puerto responda
    port_ready = False
    for i in range(30):  # Esperar hasta 30 segundos
        time.sleep(1.0)
        with lock:
            state["message"] = f"Esperando que el portal en el puerto {target_port} responda... ({i+1}/30s)"
            state["progress"] = 75 + int((i / 30.0) * 20) # sube de 75% a 95%
        if check_port("127.0.0.1", target_port):
            port_ready = True
            break
            
    if not port_ready:
        with lock:
            state["status"] = "failed"
            state["message"] = f"El servicio en el puerto {target_port} no respondió"
            state["error_detail"] = "El contenedor del servicio se inició pero no responde en la URL local. Verifique los logs con 'docker compose logs'."
            state["progress"] = 0
        return

    # 5. Todo listo
    with lock:
        state["status"] = "ready"
        state["message"] = "¡Sistema iniciado con éxito! Redirigiendo..."
        state["progress"] = 100

class SIOTLauncherHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Desactivar logs ruidosos en consola
        pass

    def _serve_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        
        # Detectar el nombre del servicio según el puerto
        with lock:
            port = state["target_port"]
        
        if port == 4000:
            srv_name = "Tablero de Misiones (Mission Control)"
            icon = "📊"
        elif port == 8081:
            srv_name = "Visor del Canon y Documentación"
            icon = "📖"
        elif port == 8082:
            srv_name = "Monitor de Telemetría y Observabilidad"
            icon = "🔬"
        else:
            srv_name = f"Servicio SIOT (Puerto {port})"
            icon = "⚙️"

        # Docker initial diagnostics
        docker_installed = check_docker_installed()
        docker_running = check_docker_daemon() if docker_installed else False
        
        status_card_html = ""
        if not docker_installed:
            status_card_html = """
            <div class="status-badge error">
                <span class="dot"></span> Docker no está instalado
            </div>
            """
        elif not docker_running:
            status_card_html = """
            <div class="status-badge warning">
                <span class="dot"></span> Docker Desktop está apagado
            </div>
            """
        else:
            status_card_html = """
            <div class="status-badge success">
                <span class="dot"></span> Docker activo, servicio inactivo
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIOT Smart Launcher</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent: #6366f1;
            --accent-glow: rgba(99, 102, 241, 0.4);
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
            --warning: #f59e0b;
            --warning-glow: rgba(245, 158, 11, 0.2);
            --error: #ef4444;
            --error-glow: rgba(239, 68, 68, 0.2);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.1) 0%, transparent 40%);
            color: var(--text-primary);
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow-x: hidden;
        }}

        .container {{
            width: 100%;
            max-width: 520px;
            perspective: 1000px;
        }}

        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            text-align: center;
            position: relative;
            overflow: hidden;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--accent), var(--success));
        }}

        .logo-area {{
            font-size: 64px;
            margin-bottom: 24px;
            display: inline-block;
            filter: drop-shadow(0 0 12px var(--accent-glow));
            animation: float 4s ease-in-out infinite;
        }}

        h1 {{
            font-family: 'Outfit', sans-serif;
            font-weight: 800;
            font-size: 28px;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 60%, #a5b4fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 15px;
            margin-bottom: 30px;
            font-weight: 300;
        }}

        .status-badge {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 50px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .status-badge.error {{
            background: var(--error-glow);
            color: #fca5a5;
        }}
        .status-badge.error .dot {{ background-color: var(--error); }}

        .status-badge.warning {{
            background: var(--warning-glow);
            color: #fde047;
        }}
        .status-badge.warning .dot {{ background-color: var(--warning); }}

        .status-badge.success {{
            background: var(--success-glow);
            color: #a7f3d0;
        }}
        .status-badge.success .dot {{ background-color: var(--success); }}

        .dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px currentColor;
        }}

        .btn {{
            background: linear-gradient(135deg, var(--accent) 0%, #4f46e5 100%);
            color: white;
            border: none;
            border-radius: 14px;
            padding: 16px 32px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s ease;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }}

        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(99, 102, 241, 0.5);
            background: linear-gradient(135deg, #818cf8 0%, var(--accent) 100%);
        }}

        .btn:active {{
            transform: translateY(1px);
        }}

        .btn:disabled {{
            background: #374151;
            color: #9ca3af;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }}

        /* Loading Area */
        .loader-box {{
            display: none;
            margin-top: 20px;
        }}

        .progress-container {{
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 16px;
            position: relative;
        }}

        .progress-bar {{
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--accent), var(--success));
            border-radius: 10px;
            transition: width 0.3s ease;
        }}

        .loader-message {{
            font-size: 14px;
            color: var(--text-primary);
            margin-bottom: 8px;
            font-weight: 600;
        }}

        .loader-sub {{
            font-size: 12px;
            color: var(--text-secondary);
        }}

        /* Error Details */
        .error-detail-box {{
            display: none;
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 12px;
            padding: 16px;
            margin-top: 24px;
            text-align: left;
        }}

        .error-title {{
            color: #fca5a5;
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 6px;
        }}

        .error-desc {{
            color: #f87171;
            font-size: 12px;
            font-family: monospace;
            white-space: pre-wrap;
            word-break: break-word;
        }}

        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-8px); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="logo-area">{icon}</div>
            <h1>SIOT Launcher</h1>
            <p class="subtitle">Conexión requerida con <strong>{srv_name}</strong></p>
            
            {status_card_html}

            <div id="action-box">
                <button id="start-btn" class="btn" onclick="startSystem()">
                    🚀 Iniciar Sistema SIOT
                </button>
            </div>

            <div id="loader-box" class="loader-box">
                <div class="loader-message" id="loader-msg">Inicializando...</div>
                <div class="progress-container">
                    <div id="progress-bar" class="progress-bar"></div>
                </div>
                <div class="loader-sub" id="loader-sub">Estableciendo entorno de tesis...</div>
            </div>

            <div id="error-box" class="error-detail-box">
                <div class="error-title">❌ Error de Ejecución</div>
                <div class="error-desc" id="error-desc">Detalles del error aquí</div>
            </div>
        </div>
    </div>

    <script>
        let pollingInterval = null;

        function startSystem() {{
            document.getElementById('start-btn').disabled = true;
            document.getElementById('action-box').style.display = 'none';
            document.getElementById('loader-box').style.display = 'block';
            document.getElementById('error-box').style.display = 'none';

            fetch('/start', {{ method: 'POST' }})
                .then(res => res.json())
                .then(data => {{
                    if (data.status === 'error') {{
                        showError(data.message, data.detail);
                    }} else {{
                        startPolling();
                    }}
                }})
                .catch(err => {{
                    showError("Fallo de conexión", err.toString());
                }});
        }}

        function startPolling() {{
            if (pollingInterval) clearInterval(pollingInterval);
            pollingInterval = setInterval(() => {{
                fetch('/status')
                    .then(res => res.json())
                    .then(data => {{
                        document.getElementById('loader-msg').innerText = data.message;
                        document.getElementById('progress-bar').style.width = data.progress + '%';
                        
                        if (data.status === 'ready') {{
                            clearInterval(pollingInterval);
                            document.getElementById('loader-sub').innerText = "¡Todo listo! Redirigiendo en segundos...";
                            setTimeout(() => {{
                                window.location.href = data.redirect;
                            }}, 1000);
                        }} else if (data.status === 'failed') {{
                            clearInterval(pollingInterval);
                            showError(data.message, data.error_detail);
                        }}
                    }})
                    .catch(err => {{
                        console.error("Error al consultar estado:", err);
                    }});
            }}, 800);
        }}

        function showError(msg, detail) {{
            document.getElementById('loader-box').style.display = 'none';
            document.getElementById('action-box').style.display = 'block';
            document.getElementById('start-btn').disabled = false;
            
            const errBox = document.getElementById('error-box');
            errBox.style.display = 'block';
            document.getElementById('error-desc').innerText = detail || msg;
        }}
    </script>
</body>
</html>
"""
        self.wfile.write(html.encode("utf-8"))

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == "/":
            # Si se pasa un puerto destino, se registra
            params = parse_qs(parsed_url.query)
            target_p = params.get("port")
            if target_p:
                try:
                    with lock:
                        state["target_port"] = int(target_p[0])
                except ValueError:
                    pass
            self._serve_html()
            
        elif path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            with lock:
                target_p = state["target_port"]
                status_copy = dict(state)
                
            status_copy["redirect"] = f"http://localhost:{target_p}"
            self.wfile.write(json.dumps(status_copy).encode("utf-8"))
            
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        if path == "/start":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            with lock:
                curr_status = state["status"]
                
            if curr_status not in ["starting_docker", "docker_ready", "starting_compose", "waiting_service"]:
                # Iniciar la secuencia en un hilo de fondo
                t = threading.Thread(target=start_sequence_thread)
                t.daemon = True
                t.start()
                
            self.wfile.write(json.dumps({"status": "acknowledged"}).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

def start_server_and_browser(target_port: int):
    """Levanta el servidor HTTP local en port 5005 y abre el navegador."""
    global state
    with lock:
        state["target_port"] = target_port
        
    server = HTTPServer(("127.0.0.1", LAUNCHER_PORT), SIOTLauncherHandler)
    url = f"http://localhost:{LAUNCHER_PORT}/?port={target_port}"
    print(f"[LAUNCHER] Servidor de diagnóstico activo en {url}")
    
    # Abrir navegador
    webbrowser.open(url)
    
    # Mantener el servidor escuchando hasta que el estado cambie a ready o el usuario cierre la app.
    # Para evitar colgarse por siempre, si pasa a 'ready' o a 'failed', podemos terminar tras un tiempo.
    try:
        while True:
            server.handle_request()
            with lock:
                curr_status = state["status"]
            if curr_status == "ready":
                # Esperar 3 segundos adicionales para asegurar que el navegador hace la redirección
                print("[LAUNCHER] ¡Redirección completada! Apagando launcher.")
                time.sleep(3.0)
                break
    except KeyboardInterrupt:
        print("[LAUNCHER] Detenido por usuario.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SIOT Smart Launcher")
    parser.add_argument("--port", type=int, default=4000, help="Puerto destino de la aplicación (default: 4000)")
    args = parser.parse_args()
    
    # 1. Comprobar si el puerto destino ya está respondiendo
    if check_port("127.0.0.1", args.port):
        print(f"[LAUNCHER] Puerto {args.port} ya está activo. Abriendo navegador directamente...")
        webbrowser.open(f"http://localhost:{args.port}")
        return 0
        
    # 2. Si está apagado, iniciar el launcher interactivo
    start_server_and_browser(args.port)
    return 0

if __name__ == "__main__":
    sys.exit(main())
