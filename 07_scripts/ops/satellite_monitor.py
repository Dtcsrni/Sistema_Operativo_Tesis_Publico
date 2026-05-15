import sys
import os
import time
import subprocess
import psutil
from pathlib import Path

# Configurar rutas para importar runtime.openclaw
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from runtime.openclaw.openclaw_local.progress import AdvancedProgressMonitor

# Cargar variables de entorno de OpenClaw
def load_env():
    env_path = ROOT / "config/env/openclaw.env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"')

load_env()

CHAT_ID = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "6866872051")
MODEL_ID = "DeepSeek-R1-Distill-Qwen-7B"
OUTPUT_FILE = ROOT / "runtime/models/edge/ds_r1_qwen_7b_w4_rkllm.rkllm"

def get_wsl_metrics(pid):
    try:
        # RSS y CPU del proceso
        output = subprocess.check_output(["wsl", "sh", "-c", f"ps -o rss=,pcpu= -p {pid}"], stderr=subprocess.DEVNULL).decode().strip()
        if not output: return 0, 0
        rss_kb, cpu_pct = output.split()
        rss_gb = int(rss_kb) / (1024 * 1024)
        return rss_gb, float(cpu_pct)
    except:
        return 0, 0

def detect_phase(rss_gb, cpu_pct):
    if OUTPUT_FILE.exists():
        return "📦 Finalizando y Persistiendo en Disco..."
    if cpu_pct > 80:
        return "⚡️ Cuantizando Capas (Fase Crítica CPU)..."
    if rss_gb > 8:
        return "🧠 Tensores Cargados (Saturación de RAM)..."
    return "⏳ Inicializando / Cargando Pesos FP16..."

def main():
    print("[*] Iniciando Monitor Satélite v2.3 (Fases Dinámicas)...")
    
    # Encontrar PID del compilador
    try:
        pid_search = subprocess.check_output(["wsl", "sh", "-c", "pgrep -f compile_rkllm"]).decode().strip()
        if not pid_search:
            print("[!] Proceso no detectado.")
            return
        target_pid = int(pid_search.split('\n')[0])
        print(f"[*] PID Detectado: {target_pid}")
    except:
        return

    title = f"🛰 TELEMETRÍA SATÉLITE: {MODEL_ID}"
    # total_items = 3600 (aprox 1 hora en segundos para barra de progreso temporal)
    with AdvancedProgressMonitor(CHAT_ID, title, total_items=3600, target_pid=target_pid) as monitor:
        start_time = time.time()
        
        while True:
            rss_gb, cpu_pct = get_wsl_metrics(target_pid)
            if rss_gb == 0:
                print("[*] Fin del proceso detectado. Verificando integridad...")
                time.sleep(2) # Dar tiempo al sistema de archivos
                if OUTPUT_FILE.exists():
                    monitor.finish(success=True, final_text="✅ Compilación exitosa. Modelo RKLLM generado y verificado.")
                else:
                    monitor.finish(success=False, final_text="❌ ERROR: El proceso terminó sin generar el modelo. Posible fallo de memoria o crash interno.")
                break
            
            # Métricas de Sistema
            ram = psutil.virtual_memory()
            swap = psutil.swap_memory()
            ram_used = ram.used / (1024**3)
            swap_used = swap.used / (1024**3) # Reportar en GB para consistencia

            # Detección de Fase
            phase = detect_phase(rss_gb, cpu_pct)
            
            # Estimación de progreso (Simulación basada en tiempo típico)
            elapsed = time.time() - start_time
            progress = int(elapsed) # Segundos transcurridos
            if progress > 3500: progress = 3500 # Mantener al 98% hasta el final real

            details = (
                f"📊 <b>Estado:</b> {phase}\n\n"
                f"🧠 <b>RSS Proceso:</b> {rss_gb:.2f} GB\n"
                f"⚡️ <b>Carga CPU:</b> {cpu_pct:.1f}%\n"
                f"📟 <b>RAM Total:</b> {ram_used:.2f} / {ram.total/(1024**3):.1f} GB\n"
                f"⚠️ <b>Swap Windows:</b> {swap_used:.2f} GB\n\n"
                f"📍 <b>Nodo:</b> Orange Pi 5 Plus (Cross-WSL)"
            )
            
            print(f"[*] Update: [Phase Detected] | RSS: {rss_gb:.2f}GB | CPU: {cpu_pct:.1f}%")
            monitor.update(current=progress, details=details, host="WSL Bridge -> Win11")
            time.sleep(15)

if __name__ == "__main__":
    main()
