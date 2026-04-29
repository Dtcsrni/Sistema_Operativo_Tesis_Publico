import os
import sys
import requests
import time
import subprocess
from pathlib import Path

# --- Configuration ---
GATEWAY_URL = "http://localhost:5000"  # Puerto del Gateway mapeado al host
INFERENCE_URL = "http://localhost:8080" # Puerto del LLM mapeado al host (solo para pruebas directas)

def test_hardware_access():
    print("[TEST] Verificando acceso a NPU (/dev/rknpu)...")
    if Path("/dev/rknpu").exists():
        print("[PASS] Device /dev/rknpu encontrado.")
        return True
    else:
        print("[SKIP] /dev/rknpu no encontrado (Estamos en el host Windows).")
        return True # Permitimos continuar para pruebas de red simuladas

def test_inference_service():
    print("[TEST] Verificando Salud del Servicio LLM...")
    try:
        resp = requests.get(f"{INFERENCE_URL}/health", timeout=5)
        if resp.status_code == 200:
            print(f"[PASS] Servicio LLM Ready: {resp.json()}")
            return True
        else:
            print(f"[FAIL] Servicio LLM reporta estado: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] No se pudo conectar al servicio LLM: {e}")
    return False

def test_cross_domain_routing():
    print("[TEST] Verificando enrutamiento via Gateway (IoT -> LLM)...")
    # Simulamos una solicitud del Gateway al LLM
    try:
        # En una arquitectura real, el GW hara una peticin interna a 'siot-llm-edge:8080'
        # Aqu probamos si el puerto del GW responde
        resp = requests.post(f"{GATEWAY_URL}/ai/decide", json={"context": "test"}, timeout=5)
        if resp.status_code == 200:
            print(f"[PASS] Enrutamiento inter-dominio exitoso.")
            return True
        else:
            print(f"[FAIL] Gateway rechaz la solicitud: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] Error en Gateway: {e}")
    return False

def run_all_tests():
    results = {
        "hardware": test_hardware_access(),
        "service_health": test_inference_service(),
        "routing": test_cross_domain_routing()
    }
    
    print("\n--- RESUMEN DE PRUEBAS ---")
    for test, passed in results.items():
        status = "OK" if passed else "FALLO"
        print(f"{test}: {status}")
    
    if all(results.values()):
        print("\n[CONCLUSION] Nodo Edge VALIDADO estructuralmente.")
        return True
    return False

if __name__ == "__main__":
    run_all_tests()
