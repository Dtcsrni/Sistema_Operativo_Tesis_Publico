import time
import os
import sys

def get_cma_info():
    """Lee info de CMA desde /proc/meminfo."""
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
        
        cma_total = 0
        cma_free = 0
        for line in lines:
            if "CmaTotal" in line:
                cma_total = int(line.split()[1])
            if "CmaFree" in line:
                cma_free = int(line.split()[1])
        
        return cma_total, cma_free
    except Exception as e:
        return 0, 0

def main():
    log_file = "cma_monitoring.log"
    interval = 5 # segundos
    
    print(f"[*] Iniciando monitoreo de CMA en Orange Pi 5 Plus...")
    print(f"[*] Guardando resultados en: {log_file}")
    print(f"{'Timestamp':<20} | {'Total (KB)':<12} | {'Free (KB)':<12} | {'Used (KB)':<12} | {'Usage (%)':<10}")
    print("-" * 75)

    with open(log_file, "a") as f:
        f.write(f"\n--- Sesión de Monitoreo: {time.ctime()} ---\n")
        f.write(f"{'Timestamp':<20} | {'Total (KB)':<12} | {'Free (KB)':<12} | {'Used (KB)':<12} | {'Usage (%)':<10}\n")
        
        try:
            while True:
                total, free = get_cma_info()
                used = total - free
                usage_pct = (used / total * 100) if total > 0 else 0
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                
                line = f"{ts:<20} | {total:<12} | {free:<12} | {used:<12} | {usage_pct:<10.2f}\n"
                print(line.strip())
                f.write(line)
                f.flush()
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[*] Monitoreo finalizado por el usuario.")
            f.write(f"--- Fin de Sesión: {time.ctime()} ---\n")

if __name__ == "__main__":
    main()
