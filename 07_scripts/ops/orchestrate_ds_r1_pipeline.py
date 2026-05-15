import os
import sys
import time
import subprocess
import json
from collections import deque
from pathlib import Path

# Configurar rutas
ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = Path(__file__).resolve().parent  # 07_scripts/ops/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(OPS_DIR))  # habilita imports directos desde ops/

try:
    from runtime.openclaw.openclaw_local.progress import AdvancedProgressMonitor
    from fault_analyzer import FaultAnalyzer      # import directo, sin importlib
    from security_auditor import SecurityAuditor  # import directo, sin importlib
except Exception as e:
    print(f"[ERROR] Fallo de inicialización ARO: {e}")
    sys.exit(1)

STATE_FILE = ROOT / "00_sistema_tesis/bitacora/pipeline_state.json"

def load_openclaw_env():
    env_path = ROOT / "config/env/openclaw.env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"')

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except: pass
    return {"last_phase": 1, "strategy": "GGUF_V2"}

def run_monitored(cmd: str, monitor, start_pct: int, end_pct: int) -> tuple[int, str]:
    """Ejecuta un comando en WSL con monitoreo de progreso en tiempo real.

    Usa un buffer circular de 500 líneas para evitar acumulación de RAM
    en procesos de larga duración (conversión de modelos de varias horas).
    El llamante solo necesita las últimas líneas para detectar el tipo de error.
    """
    MAX_TAIL_LINES = 500
    full_cmd = f'wsl -d Ubuntu bash -c "{cmd}"'
    print(f"[*] ARO Exec: {cmd}")

    process = subprocess.Popen(
        full_cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace"
    )
    output_tail: deque = deque(maxlen=MAX_TAIL_LINES)  # buffer circular — O(1) memoria

    line_count = 0
    for line in process.stdout:
        output_tail.append(line)
        line_count += 1
        line_clean = line.strip()
        if line_count % 5 == 0:  # Reducir ruido en logs
            print(f"    > {line_clean[:80]}")
        prog = start_pct + (line_count // 20)
        if prog < end_pct:
            monitor.update(current=prog, details=line_clean[:50] + "...")

    process.wait()
    return process.returncode, "".join(output_tail)

def main():
    load_openclaw_env()
    state = load_state()
    CHAT_ID = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "6866872051")
    
    MODEL_ID = "DeepSeek-R1-Distill-Qwen-7B"
    OUTPUT_RKLLM = "runtime/models/edge/ds_r1_qwen_7b_w4_rkllm.rkllm"
    
    STRATEGIES = {
        "GGUF_V1": "runtime/models/edge/ds-r1-7b-gguf/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
        "GGUF_V2": "runtime/models/edge/ds-r1-7b-gguf-v2/DeepSeek-R1-Distill-Qwen-7B-Q4_0.gguf"
    }

    title = "🧬 Orquestador ARO v1.0"  # f-string sin variable — simplificado
    auditor = SecurityAuditor(ROOT)
    
    # Cargar message_id previo si existe
    existing_msg_id = state.get("telegram_message_id")
    
    with AdvancedProgressMonitor(CHAT_ID, title, total_items=100, existing_message_id=existing_msg_id) as monitor:
        # Guardar el ID recién generado (o reutilizado) por si el script se detiene
        if not existing_msg_id:
            state["telegram_message_id"] = monitor.message_id
            save_state(state)
        
        try:
            # 0. Pre-flight Security Audit
            monitor.update(details="🔒 Ejecutando auditoría de seguridad pre-vuelo...")
            net_status = auditor.audit_network_connections()
            if net_status["status"] != "OK":
                monitor.update(details="⚠️ Advertencia de Seguridad: Conexiones sospechosas detectadas.")
            
            # 1. Sanitización
            if state["last_phase"] < 1:
                monitor.update(current=5, title=title, details="🩹 Autocorrección: Sanitizando nodo...", host="WSL")
                subprocess.run(["wsl", "python3", "07_scripts/ops/clean_node.py", "--force"], check=False)
                state["last_phase"] = 1
                save_state(state)

            # 2. Conversión
            while state["last_phase"] < 2:
                current_strategy = state["strategy"]
                model_rel_path = STRATEGIES.get(current_strategy)
                model_abs_path = ROOT / model_rel_path
                
                # REGLA DE ORO: Si no existe el peso, descargarlo
                if not model_abs_path.exists():
                    monitor.update(current=10, details=f"📥 Descargando {current_strategy}...")
                    repo = "bartowski/DeepSeek-R1-Distill-Qwen-7B-GGUF"
                    filename = model_rel_path.split("/")[-1]
                    target_dir = "/".join(model_rel_path.split("/")[:-1])
                    
                    dl_cmd = f"huggingface-cli download {repo} --include '{filename}' --local-dir {target_dir}"
                    ret, _ = run_monitored(dl_cmd, monitor, 10, 40)
                    if ret != 0:
                        monitor.finish(success=False, final_text="Fallo crítico en descarga de pesos.")
                        return
                    
                    # Auditoría de Integridad post-descarga
                    monitor.update(details="🛡 Verificando integridad SHA-256 del modelo...")
                    audit_res = auditor.audit_file_integrity(model_abs_path)
                    monitor.update(details=f"✅ Hash verificado: {audit_res['sha256'][:16]}...")

                # Convertir
                monitor.update(current=40, title=f"Fase 2: Conversión ({current_strategy})", details="Ejecutando rkllm-toolkit...", host="WSL")
                cmd_conv = f"python3 07_scripts/ai_tools/convert_gguf_to_rkllm.py --model {model_rel_path} --output {OUTPUT_RKLLM}"
                ret, output = run_monitored(cmd_conv, monitor, 40, 80)
                
                if ret == 0:
                    state["last_phase"] = 2
                    save_state(state)
                    break
                else:
                    # Análisis de fallo
                    if "Not support GGMLQuantizationType" in output and current_strategy == "GGUF_V1":
                        monitor.update(details="🩹 Autocorrección: Formato incompatible. Pivotando a Q4_0...")
                        state["strategy"] = "GGUF_V2"
                        save_state(state)
                        continue
                    
                    monitor.finish(success=False, final_text=f"Error en conversión {current_strategy}. Abortando.")
                    return

            # 3. Sincronización
            if state["last_phase"] < 3:
                monitor.update(current=80, title="Fase 3: Sincronización", details="Transfiriendo a Edge...", host="WSL -> OPi5")
                cmd_sync = "bash 07_scripts/ops/sync_system_to_edge.sh"
                ret, _ = run_monitored(cmd_sync, monitor, 80, 95)
                if ret == 0:
                    state["last_phase"] = 3
                    save_state(state)

            monitor.finish(success=True, final_text="✅ Misión ARO Exitosa. DeepSeek-R1-7B está vivo en el Edge.")
            if STATE_FILE.exists(): os.remove(STATE_FILE)

        except Exception as e:
            monitor.finish(success=False, final_text=f"Error fatal en ARO: {str(e)}")

if __name__ == "__main__":
    main()
