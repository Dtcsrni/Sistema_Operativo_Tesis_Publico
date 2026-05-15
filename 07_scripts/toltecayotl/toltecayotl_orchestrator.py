import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import time

import os
import json
import threading

try:
    import requests
except Exception:
    requests = None
from rkllm_wrapper import RKLLMWrapper, RKLLMParam, LLMResultCallback, LLMCallState

# --- Configuración Maestra ---
MODEL_TRIAGE = "/home/ErickV/runtime/models/edge/qwen2.5_0.5b_rkllm_triage.rkllm"
MODEL_REASONING = "/home/ErickV/runtime/models/edge/qwen2.5_1.5b_rkllm.rkllm"
LIB_PATH = "/home/ErickV/SIOT_Benchmark/runtime/drivers/rknn/librkllmrt.so"

class AgentState:
    def __init__(self, name):
        self.name = name
        self.response = ""
        self.done = False
        self.start_time = 0
        self.first_token_time = 0

current_agent = None


class TelemetryClient:
    def __init__(self):
        self.url = os.getenv("MISSION_CONTROL_URL", "http://localhost:4000/api/events")
        self._requests = requests

    def send(self, payload: dict):
        def _post():
            try:
                if self._requests:
                    self._requests.post(self.url, json=payload, timeout=2)
                else:
                    # fallback to urllib
                    import urllib.request
                    data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"})
                    urllib.request.urlopen(req, timeout=2)
            except Exception as e:
                print(f"[Telemetry] error sending: {e}")

        t = threading.Thread(target=_post, daemon=True)
        t.start()


telemetry_client = TelemetryClient()

@LLMResultCallback
def orchestrator_callback(result_ptr, userdata, state):
    global current_agent
    res = result_ptr.contents
    if res.text:
        if current_agent.first_token_time == 0:
            current_agent.first_token_time = time.perf_counter()
        current_agent.response += res.text.decode('utf-8', errors='ignore')
        # Enviar evento de token a Mission Control
        try:
            telemetry_client.send({
                "type": "agent.token",
                "message": f"[{current_agent.name}] Token received",
                "metadata": {
                    "agent_name": current_agent.name,
                    "text": res.text.decode('utf-8', errors='ignore'),
                    "ts": time.time(),
                }
            })
        except Exception:
            pass
    
    if state == LLMCallState.RKLLM_RUN_FINISH:
        current_agent.done = True
        # Evento de finalización
        try:
            telemetry_client.send({
                "type": "agent.finish",
                "message": f"[{current_agent.name}] Execution completed",
                "metadata": {
                    "agent_name": current_agent.name,
                    "response": current_agent.response,
                    "duration": time.perf_counter() - current_agent.start_time if current_agent.start_time else None,
                    "ts": time.time(),
                }
            })
        except Exception:
            pass
    return 0

class AtzinOrchestrator:
    def __init__(self):
        print("[INIT] Cargando Sistema de Dos Niveles Atzin...")
        self.triage = RKLLMWrapper(LIB_PATH)
        self.reasoning = RKLLMWrapper(LIB_PATH)
        
    def setup(self):
        # Setup Triage (0.5B)
        p_triage = self.triage.create_default_param()
        p_triage.model_path = MODEL_TRIAGE.encode('utf-8')
        p_triage.max_context_len = 512
        self.triage.init(p_triage, orchestrator_callback)
        
        # Setup Reasoning (1.5B)
        p_reason = self.reasoning.create_default_param()
        p_reason.model_path = MODEL_REASONING.encode('utf-8')
        p_reason.max_context_len = 4096
        self.reasoning.init(p_reason, orchestrator_callback)
        print("[SUCCESS] Cerebros Atzin Sincronizados.")

    def ask(self, prompt):
        global current_agent
        
        # FASE 1: TRIAGE
        print(f"\n[USER] {prompt}")
        current_agent = AgentState("Triage")
        current_agent.start_time = time.perf_counter()
        
        triage_prompt = f"Clasifica esta petición como 'SIMPLE' o 'COMPLEJA'. Responde solo con una palabra: {prompt}"
        self.triage.run(triage_prompt)
        
        while not current_agent.done: time.sleep(0.01)
        
        decision = current_agent.response.strip().upper()
        print(f"[TRIAGE] Decisión: {decision}")
        
        # FASE 2: EJECUCIÓN
        current_agent = AgentState("Reasoning" if "COMPLEJA" in decision else "Triage")
        current_agent.start_time = time.perf_counter()
        
        if "COMPLEJA" in decision:
            print("[EXEC] Delegando a Modelo 1.5B (Razonamiento Profundo)...")
            self.reasoning.run(prompt)
        else:
            print("[EXEC] Resolviendo con Modelo 0.5B (Respuesta Rápida)...")
            self.triage.run(prompt)
            
        while not current_agent.done: 
            if current_agent.response.endswith("\n"): break
            time.sleep(0.01)
            
        print(f"[{current_agent.name}] {current_agent.response}")
        return current_agent.response

def main():
    orch = AtzinOrchestrator()
    orch.setup()
    
    # Pruebas de Benchmark
    orch.ask("¿Qué hora es?")
    orch.ask("Escribe un script en Python para leer el RSSI de un módulo LoRa Heltec.")

if __name__ == "__main__":
    main()
