import psutil
import os
import time
import json
import logging
from typing import List, Dict, Any

# <!-- SISTEMA_TESIS:PROTEGIDO -->

# Configuración de Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("SystemSanitizer")

# Lista blanca de procesos críticos que NUNCA deben cerrarse
CRITICAL_PROCESS_KEYWORDS = [
    "ollama", "rkllm", "ssh", "bash", "systemd", "kernel", 
    "python", "tesis", "openclaw", "serena", "antigravity",
    "init", "kthreadd", "dbus", "networkmanager", "wpa_supplicant",
    "rpcbind", "avahi", "chrony", "rsyslog"
]

# Lista de procesos "pesados" conocidos como no esenciales (para PC)
NON_ESSENTIAL_KEYWORDS = [
    "chrome", "edge", "firefox", "teams", "discord", "slack", 
    "spotify", "excel", "winword", "powerpnt", "skype", "telegram"
]

class SystemSanitizer:
    def __init__(self):
        self.persistent_noise = []

    def get_background_noise(self) -> Dict[str, Any]:
        """Captura el estado actual del sistema antes de sanitizar."""
        cpu_pct = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        
        # Top 5 procesos por consumo de CPU
        top_procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                top_procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        top_procs = sorted(top_procs, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:5]
        
        return {
            "total_cpu_percent": cpu_pct,
            "total_mem_percent": mem.percent,
            "available_mem_gb": round(mem.available / (1024**3), 2),
            "top_processes": top_procs,
            "timestamp": time.time()
        }

    def sanitize(self, dry_run: bool = False) -> List[str]:
        """Intenta cerrar procesos no esenciales y registra los remanentes."""
        logger.info("Iniciando fase de sanitización de entorno...")
        killed_procs = []
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                p_name = proc.info['name'].lower()
                p_pid = proc.info['pid']
                
                # Omitir si es un proceso crítico
                if any(k in p_name for k in CRITICAL_PROCESS_KEYWORDS):
                    continue
                
                # Intentar cerrar si está en la lista de no esenciales
                if any(k in p_name for k in NON_ESSENTIAL_KEYWORDS):
                    if not dry_run:
                        logger.info(f"Terminando proceso no esencial: {p_name} (PID: {p_pid})")
                        proc.terminate()
                        killed_procs.append(p_name)
                    else:
                        logger.info(f"[DRY-RUN] Se cerraría: {p_name}")
                        killed_procs.append(p_name)
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if not dry_run:
            time.sleep(2) # Esperar a que se liberen recursos
            
        logger.info(f"Sanitización completada. Procesos cerrados: {len(killed_procs)}")
        return killed_procs

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sanitizador de Sistema para Benchmarking")
    parser.add_argument("--dry-run", action="store_true", help="No cerrar procesos, solo listar")
    parser.add_argument("--report", action="store_true", help="Mostrar ruido de fondo actual")
    args = parser.parse_args()
    
    sanitizer = SystemSanitizer()
    if args.report:
        noise = sanitizer.get_background_noise()
        print(json.dumps(noise, indent=2))
    
    if args.dry_run:
        sanitizer.sanitize(dry_run=True)
    else:
        sanitizer.sanitize(dry_run=False)
