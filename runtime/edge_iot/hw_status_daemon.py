import time
import os
import re
import sys
import shutil
import socket
import subprocess
import logging

# Configurar logging
logging.basicConfig(
    filename='/tmp/hw_daemon_debug.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Añadir path para importar el driver del LED
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from drivers.orange_pi_led import OrangePiLED

# --- CONFIGURACIÓN DE SEÑALES CRÍTICAS ---
# Secuencias: (Encendido, Apagado) en segundos
CODE_NO_NET = [(0.2, 0.2), (0.2, 0.2), (0.2, 0.8)]      # 3 destellos cortos azul
CODE_DISK_FULL = [(0.1, 0.1)] * 5 + [(0.8, 0.8)]      # SOS-like Cyan
CODE_SERVICE_FAIL = [(0.5, 0.1), (0.5, 0.8)]          # Largo-Corto Verde

def get_cpu_load():
    try:
        with open("/proc/stat", "r") as f: line = f.readline()
        parts = line.split()
        return map(int, parts[1:5])
    except: return 0,0,0,0

def get_npu_load():
    try:
        with open("/sys/kernel/debug/rknpu/load", "r") as f: content = f.read()
        loads = re.findall(r"Core\d+: (\d+)%", content)
        return sum(map(int, loads)) / len(loads) if loads else 0
    except: return 0

def check_network():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except: return False

def check_service_health(container_name="siot-edge-gw"):
    try:
        result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_name], 
                                capture_output=True, text=True)
        return "true" in result.stdout.lower()
    except: return True # Si no hay docker, asumimos OK para no generar falsos positivos

def main_loop():
    green = OrangePiLED("green")
    blue = OrangePiLED("blue")
    
    last_u, last_n, last_s, last_i = get_cpu_load()
    
    logging.info("🚀 Hardware Status Daemon v3.0 (Production) Iniciado.")
    
    while True:
        try:
            # 1. Monitoreo de Métricas Básicas
            u, n, s, i = get_cpu_load()
            diff = (u+n+s) - (last_u+last_n+last_s)
            total = diff + (i - last_i)
            cpu = (diff / total * 100) if total > 0 else 0
            last_u, last_n, last_s, last_i = u, n, s, i
            
            npu = get_npu_load()
            temp = int(open("/sys/class/thermal/thermal_zone0/temp").read()) / 1000.0
            disk = shutil.disk_usage("/")
            disk_free_gb = disk.free / (1024**3)
            
            # 2. Diagnóstico de Salud
            net_ok = check_network()
            service_ok = check_service_health()
            
            # 3. MÁQUINA DE ESTADOS LED (Prioridad descendente)
            
            # CRÍTICO 1: Temperatura Extrema
            if temp > 80:
                green.blink(15); blue.blink(15)
            
            # CRÍTICO 2: Disco Casi Lleno (< 1GB)
            elif disk_free_gb < 1.0:
                # Código SOS en Cian
                green.signal_code(CODE_DISK_FULL)
                blue.signal_code(CODE_DISK_FULL)
            
            # CRÍTICO 3: Fallo de Servicio Edge Gateway
            elif not service_ok:
                blue.static(False)
                green.signal_code(CODE_SERVICE_FAIL)
            
            # CRÍTICO 4: Sin Conectividad
            elif not net_ok:
                green.static(False)
                blue.signal_code(CODE_NO_NET)
            
            # NOMINAL: Inferencia NPU activa
            elif npu > 5:
                speed = 1.0 + (npu / 10.0)
                if cpu > 70:
                    green.breathe(speed); blue.breathe(speed)
                else:
                    green.static(False); blue.breathe(speed)
            
            # NOMINAL: Carga de CPU
            else:
                speed = 0.5 + (cpu / 20.0)
                blue.static(False)
                green.breathe(speed)
                
            logging.info(f"Status: CPU={cpu:.1f}%, NPU={npu:.1f}%, Temp={temp:.1f}C, Net={net_ok}, Service={service_ok}")
            time.sleep(3) 
            
        except Exception as e:
            import traceback
            logging.error(f"Error en main_loop: {e}\n{traceback.format_exc()}")
            green.blink(10)
            time.sleep(5)

if __name__ == "__main__":
    main_loop()
