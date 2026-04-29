import platform
import subprocess
import json
import os
import sys

def get_cpu_info():
    sys_type = platform.system()
    if sys_type == "Windows":
        try:
            out = subprocess.check_output("wmic cpu get name", shell=True).decode().splitlines()
            return out[2].strip() if len(out) > 2 else platform.processor()
        except:
            return platform.processor()
    elif sys_type == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        except:
            pass
    return platform.processor()

def get_gpu_info():
    try:
        # Intentar nvidia-smi
        out = subprocess.check_output("nvidia-smi --query-gpu=name --format=csv,noheader", shell=True).decode().strip()
        return out
    except:
        return "No NVIDIA GPU detected"

def get_npu_info():
    # Especialmente para Orange Pi 5 / RK3588
    if platform.system() == "Linux":
        if os.path.exists("/dev/rknn"):
            return "Rockchip NPU (RK3588 family)"
    return "No NPU detected"

def get_model_identity(runtime, model_name):
    identity = {"requested": model_name, "actual": "unknown", "status": "unknown"}
    
    if runtime == "ollama_local":
        try:
            # Intentar local primero
            try:
                cmd = "ollama list"
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
            except:
                # Fallback a WSL
                cmd = "wsl ollama list"
                out = subprocess.check_output(cmd, shell=True).decode()
                
            for line in out.splitlines()[1:]:
                parts = line.split()
                if parts and parts[0] == model_name:
                    identity["actual"] = parts[0]
                    identity["digest"] = parts[1]
                    identity["size"] = parts[2]
                    identity["status"] = "verified"
                    return identity
            identity["status"] = "not_found"
        except Exception as e:
            identity["status"] = f"error: {str(e)}"
            
    elif runtime == "rk3588_npu":
        # Placeholder para lógica rknn-toolkit-lite2
        identity["actual"] = model_name
        identity["status"] = "presumed (npu runtime)"
        
    return identity

def get_full_identity(runtime="ollama_local", model_name="mistral-nemo:12b"):
    return {
        "node_name": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu": get_cpu_info(),
        "gpu": get_gpu_info(),
        "npu": get_npu_info(),
        "python": sys.version.split()[0],
        "model": get_model_identity(runtime, model_name)
    }

if __name__ == "__main__":
    # Test output
    print(json.dumps(get_full_identity(), indent=2))
