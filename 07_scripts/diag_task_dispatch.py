#!/usr/bin/env python3
"""
test_task_dispatch.py - Dispara una tarea de prueba hacia el gateway via WebSocket RPC
"""

import json
import sys
import time
import threading
from pathlib import Path

try:
    import websocket
except ImportError:
    print("ERROR: websocket-client no instalado. Instálalo con: pip install websocket-client")
    sys.exit(1)

# URL del gateway
GATEWAY_URL = "ws://localhost:18789"
GATEWAY_TOKEN = "38fd7f653b48a66207f73cfd2d0d56fee2c362b7721026df"

def dispatch_test_task():
    """Dispara una tarea de prueba al gateway via WebSocket RPC."""
    
    print("[TEST] Conectando al gateway...")
    print(f"  URL: {GATEWAY_URL}")
    print()
    
    response_received = threading.Event()
    response_data = {}
    challenge_nonce = None
    rpc_sent = False
    last_activity_time = time.time()
    
    def on_message(ws, message):
        """Callback para mensajes recibidos."""
        nonlocal response_data, challenge_nonce, rpc_sent, last_activity_time
        last_activity_time = time.time()
        data = json.loads(message)
        print(f"[RX] {data.get('type', 'unknown')}")
        
        # Manejar challenge
        if data.get("type") == "event" and data.get("event") == "connect.challenge":
            challenge_nonce = data.get("payload", {}).get("nonce")
            print(f"  → Challenge: {challenge_nonce[:8]}...")
            # Responder con connect
            connect_request = {
                "type": "req",
                "id": 0,
                "method": "connect",
                "params": {
                    "auth": {
                        "token": GATEWAY_TOKEN
                    }
                }
            }
            ws.send(json.dumps(connect_request))
            print("[AUTH] Connect request enviado")
        
        # Manejar autorización exitosa
        elif data.get("type") == "res" and data.get("id") == 0 and data.get("ok"):
            print("  → Conectado y autenticado!")
            if not rpc_sent:
                rpc_sent = True
                # Enviar RPC call después de auth
                rpc_call = {
                    "id": 1,
                    "type": "req",
                    "method": "chat.send",
                    "params": {
                        "session_key": "test_smoke_session",
                        "message": "Dame un resumen en una línea de cómo funciona el control de misiones",
                        "channel": "web"
                    }
                }
                print(f"[TX] RPC call: {rpc_call['method']}")
                ws.send(json.dumps(rpc_call))
        
        # Buscar respuesta final
        elif data.get("type") == "res" and data.get("id") == 1 and data.get("ok"):
            response_data = data.get("result", {})
            print("\n[FINAL] Respuesta recibida del RPC")
            response_received.set()
        
        # Capturar streaming de agente
        elif data.get("type") == "event" and data.get("event") == "agent":
            payload = data.get("payload", {})
            if payload.get("data"):
                print(f"{payload['data']}", end="", flush=True)
    
    def on_error(ws, error):
        print(f"[ERROR WebSocket] {error}")
        response_received.set()
    
    def on_close(ws, close_status_code, close_msg):
        print(f"[CLOSE] {close_status_code}: {close_msg}")
        response_received.set()
    
    def on_open(ws):
        print("[OPEN] Conexión establecida, esperando challenge...")
        # No enviar nada aquí; esperar al challenge
    
    # Conectar
    ws = websocket.WebSocketApp(
        f"{GATEWAY_URL}/?token={GATEWAY_TOKEN}",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Ejecutar en thread
    ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
    ws_thread.start()
    
    # Esperar respuesta con timeout inteligente: esperamos actividad
    # Si hay 3 segundos sin actividad después de enviar RPC, asumir que terminó
    start_time = time.time()
    rpc_send_time = None
    
    while time.time() - start_time < 60:
        if rpc_sent and not rpc_send_time:
            rpc_send_time = time.time()
        
        # Si pasaron 3s sin actividad desde que enviamos RPC, considerar terminado
        if rpc_send_time and time.time() - last_activity_time > 3:
            print("\n\n[OK] Streaming completado (inactividad)")
            ws.close()
            return True
        
        # Si recibimos respuesta RPC final, salir inmediatamente
        if response_received.is_set():
            print("\n\n[OK] Respuesta RPC recibida")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))
            ws.close()
            return True
        
        time.sleep(0.1)
    
    print("\n✗ TIMEOUT: No se recibió respuesta en 60s")
    ws.close()
    return False

if __name__ == "__main__":
    success = dispatch_test_task()
    sys.exit(0 if success else 1)
