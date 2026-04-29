import time
import psutil
import os

def get_temp():
    try:
        # Specific for RK3588 (Linux/OPi)
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return float(f.read()) / 1000.0
    except:
        return 0.0

def monitor_system(duration_sec=60, interval_sec=1):
    print(f"[BENCHMARK] Iniciando monitoreo de recursos por {duration_sec}s...")
    print("Time(s), CPU(%), RAM(MB), Temp(C)")
    
    start_time = time.time()
    while (time.time() - start_time) < duration_sec:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().used / (1024 * 1024)
        temp = get_temp()
        
        elapsed = time.time() - start_time
        print(f"{elapsed:.1f}, {cpu}, {ram:.1f}, {temp:.1f}")
        time.sleep(interval_sec)

if __name__ == "__main__":
    monitor_system()
