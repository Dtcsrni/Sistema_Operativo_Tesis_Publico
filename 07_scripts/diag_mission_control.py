#!/usr/bin/env python3
"""
Test script para validar integración de telemetría Toltecayotl -> Mission Control
"""

import json
import urllib.request
import urllib.error
import time

MC_URL = "http://localhost:4000/api/events"

def send_event(event_type, message, metadata=None):
    """Envía un evento a Mission Control"""
    payload = {
        "type": event_type,
        "message": message,
        "metadata": metadata or {}
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            MC_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            print(f"✓ Evento enviado: {result['id']}")
            return True
    except urllib.error.URLError as e:
        print(f"✗ Error de conexión: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_telemetry():
    """Ejecuta pruebas de telemetría"""
    print("[TEST] Iniciando pruebas de telemetría...")
    print(f"[URL] {MC_URL}\n")
    
    # Test 1: Evento de token
    print("[1] Enviando evento de token...")
    send_event(
        "agent.token",
        "[Triage] Token received",
        {
            "agent_name": "Triage",
            "text": "Clasificando petición...",
            "ts": time.time()
        }
    )
    
    # Test 2: Evento de finalización
    print("[2] Enviando evento de finalización...")
    send_event(
        "agent.finish",
        "[Reasoning] Execution completed",
        {
            "agent_name": "Reasoning",
            "response": "Esta es una respuesta completa del modelo.",
            "duration": 2.5,
            "ts": time.time()
        }
    )
    
    # Test 3: Evento personalizado
    print("[3] Enviando evento personalizado...")
    send_event(
        "agent.error",
        "[Triage] Error en procesamiento",
        {
            "agent_name": "Triage",
            "error": "Timeout en modelo",
            "ts": time.time()
        }
    )
    
    print("\n[✓] Pruebas completadas. Verifica http://localhost:4000 para ver los eventos.")

if __name__ == "__main__":
    test_telemetry()
