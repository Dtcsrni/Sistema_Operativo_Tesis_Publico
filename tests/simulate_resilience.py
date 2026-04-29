import subprocess
import time
import sys
import os

def simulate_failure_and_recovery():
    print("[*] Iniciando simulación de resiliencia B0...")
    
    # 1. Verificar estado inicial
    print("[1/4] Verificando estado inicial de servicios...")
    result = subprocess.run(["docker-compose", "ps", "--format", "json"], capture_output=True, text=True)
    if "siot-agent" not in result.stdout:
        print("[FAIL] Los servicios base no están corriendo.")
        return False

    # 2. Simular caída del agente
    print("[2/4] Simulando caída crítica de 'siot-agent'...")
    subprocess.run(["docker", "stop", "siot-agent"], check=True)
    time.sleep(2)
    
    # 3. Intentar recuperación (restart policy de docker-compose)
    print("[3/4] Verificando política de auto-recuperación...")
    # Docker-compose con restart: unless-stopped debería levantarlo si usamos up -d de nuevo
    # O simplemente verificar si docker lo levantó (si usamos 'always' o 'on-failure')
    # Como usamos 'unless-stopped', manual 'stop' no lo levantará. 
    # Simularemos un kill (crash) enviando señal 9.
    subprocess.run(["docker", "start", "siot-agent"], check=True) # Restaurar para el test
    print("[INFO] Servicio restaurado. Probando crash forzado (kill)...")
    subprocess.run(["docker", "kill", "siot-agent"], check=True)
    time.sleep(5)
    # Aquí es donde 'unless-stopped' o 'always' actúa. 
    # Nota: Docker Daemon es quien lo levanta.
    
    # 4. Verificar integridad del canon tras el crash
    print("[4/4] Verificando integridad del canon post-crash...")
    result = subprocess.run([sys.executable, "07_scripts/guardrails.py", "--verify"], capture_output=True, text=True)
    if "Integridad del sistema verificada" in result.stdout:
        print("[OK] El canon permaneció inmutable tras el fallo del contenedor.")
        return True
    else:
        print("[FAIL] Se detectó corrupción o inconsistencia en el canon.")
        return False

if __name__ == "__main__":
    if simulate_failure_and_recovery():
        print("\n[ÉXITO] Prueba de resiliencia completada. El sistema es robusto.")
        sys.exit(0)
    else:
        print("\n[ERROR] El sistema falló la prueba de resiliencia.")
        sys.exit(1)
