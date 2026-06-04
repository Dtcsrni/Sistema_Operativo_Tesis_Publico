#!/usr/bin/env python3
"""
Diagnóstico exhaustivo de backends de inferencia para OpenClaw.
Identifica cuál backend falla y por qué.
"""

import os
import sys
import json
import time
import sqlite3
from pathlib import Path
from urllib import request, error
from collections import defaultdict

# Configuración de backends desde env
EDGE_BASE = os.getenv("OPENCLAW_EDGE_INFERENCE_BASE_URL", os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:8085/v1"))
DESKTOP_RUNTIME_BASE = os.getenv("OPENCLAW_DESKTOP_RUNTIME_BASE_URL", os.getenv("OPENCLAW_DESKTOP_RUNTIME_BASE", "http://127.0.0.1:8085/v1"))
DESKTOP_COMPUTE_BASE = os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:8085/v1")

print("\n" + "="*80)
print("🔧 DIAGNÓSTICO DE BACKENDS - OpenClaw Telegram Bot")
print("="*80 + "\n")

# 1. Verificar configuración
print("1️⃣  CONFIGURACIÓN DE BACKENDS")
print("-" * 80)
print(f"  🌐 Edge (LlamaCPP):          {EDGE_BASE}")
print(f"  💻 Desktop Runtime:          {DESKTOP_RUNTIME_BASE}")
print(f"  💻 Desktop Compute:          {DESKTOP_COMPUTE_BASE}")
print()

backends_to_check = {
    "edge": {
        "url": EDGE_BASE,
        "endpoint": "/models" if EDGE_BASE.rstrip("/").endswith("/v1") else "/v1/models",
        "type": "openai_compat"
    },
    "desktop_runtime": {
        "url": DESKTOP_RUNTIME_BASE,
        "endpoint": "/models" if DESKTOP_RUNTIME_BASE.rstrip("/").endswith("/v1") else "/v1/models",
        "type": "openai_compat"
    },
    "desktop_compute": {
        "url": DESKTOP_COMPUTE_BASE,
        "endpoint": "/models" if DESKTOP_COMPUTE_BASE.rstrip("/").endswith("/v1") else "/v1/models",
        "type": "openai_compat"
    }
}

# 2. Verificar disponibilidad de endpoints
print("\n2️⃣  DISPONIBILIDAD DE ENDPOINTS")
print("-" * 80)

backend_status = {}
for name, config in backends_to_check.items():
    url = config["url"] + config["endpoint"]
    try:
        req = request.Request(url, method="GET")
        req.add_header("User-Agent", "OpenClaw-Diagnostic/1.0")
        
        start = time.time()
        with request.urlopen(req, timeout=5) as response:
            latency = (time.time() - start) * 1000
            data = json.loads(response.read().decode("utf-8"))
            
            # Extraer información según tipo
            if config["type"] == "ollama":
                models = [m.get("name") for m in data.get("models", [])]
                status_msg = f"✅ OK ({len(models)} modelos, {latency:.0f}ms)"
                backend_status[name] = {"ok": True, "models": models, "latency": latency}
            else:
                models = [m.get("id") for m in data.get("data", [])]
                status_msg = f"✅ OK ({len(models)} modelos, {latency:.0f}ms)"
                backend_status[name] = {"ok": True, "models": models, "latency": latency}
            
            print(f"  {name:20} → {status_msg}")
            print(f"     Modelos: {', '.join(models[:3])} {'...' if len(models) > 3 else ''}")
            
    except error.URLError as e:
        print(f"  {name:20} → ❌ No disponible (URL Error: {e.reason})")
        backend_status[name] = {"ok": False, "error": str(e.reason), "type": "url_error"}
    except error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        print(f"  {name:20} → ❌ HTTP {e.code} ({e.reason})")
        backend_status[name] = {"ok": False, "error": f"HTTP {e.code}", "type": "http_error", "detail": detail[:100]}
    except Exception as e:
        print(f"  {name:20} → ❌ Error: {type(e).__name__}: {str(e)[:50]}")
        backend_status[name] = {"ok": False, "error": f"{type(e).__name__}: {e}", "type": "exception"}

# 3. Analizar eventos de error en BD
print("\n\n3️⃣  ANÁLISIS DE ERRORES EN BD")
print("-" * 80)

DB_PATH = Path("runtime/openclaw/state/openclaw.db")
if DB_PATH.exists():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    
    c.execute('''
        SELECT event_id, command, status, created_at, payload_json
        FROM telegram_events
        ORDER BY created_at DESC
    ''')
    
    events = c.fetchall()
    error_patterns = defaultdict(int)
    
    for event_id, command, status, created_at, payload_str in events:
        try:
            payload = json.loads(payload_str)
            response = payload.get("response", "").lower()
            
            # Clasificar errores
            if "saturado" in response or "sla" in response:
                error_patterns["Inferencia saturada"] += 1
            elif "timeout" in response:
                error_patterns["Timeout"] += 1
            elif "not available" in response or "unavailable" in response:
                error_patterns["Modelo no disponible"] += 1
            elif "busy" in response:
                error_patterns["Backend ocupado"] += 1
            elif "unauthorized" in status.lower():
                error_patterns["No autorizado"] += 1
            elif status == "delivered" and response.strip():
                error_patterns["Exitoso"] += 1
        except:
            pass
    
    print(f"  Total de eventos: {len(events)}")
    for pattern, count in sorted(error_patterns.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(events)
        print(f"  • {pattern:30} {count:2} ({pct:5.1f}%)")
    
    conn.close()
else:
    print(f"  ❌ Base de datos no encontrada: {DB_PATH}")

# 4. Recomendaciones
print("\n\n4️⃣  RECOMENDACIONES")
print("-" * 80)

down_backends = [k for k, v in backend_status.items() if not v.get("ok")]

if not down_backends:
    print("  ✅ Todos los backends están disponibles.")
    print("  ⚠️  El problema puede ser:")
    print("     • Modelos no están cargados en memoria")
    print("     • Timeout insuficiente")
    print("     • CPU/RAM saturados en el sistema")
    print("     • Semáforo de concurrencia activado (backend_busy)")
else:
    print(f"  ❌ {len(down_backends)} backend(s) caído(s): {', '.join(down_backends)}")
    for be in down_backends:
        status = backend_status[be]
        print(f"\n  🔴 {be}:")
        print(f"     URL: {backends_to_check[be]['url']}")
        print(f"     Error: {status['error']}")
        if status.get("type") == "http_error":
            print(f"     Acción: Revisar servicio, logs de contenedor")
        elif status.get("type") == "url_error":
            print(f"     Acción: Verificar conectividad de red, firewall, DNS")
        elif status.get("type") == "exception":
            print(f"     Acción: {status['error']}")

# 5. Prueba rápida de inferencia
print("\n\n5️⃣  PRUEBA DE INFERENCIA")
print("-" * 80)

if backend_status.get("edge", {}).get("ok"):
    print("  Intentando inferencia en Edge (LlamaCPP)...")
    try:
        # Usar formato compatible con API standard/llama.cpp
        payload = json.dumps({
            "model": os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b"),
            "messages": [{"role": "user", "content": "Responde en una frase: ¿Cuánto es 2+2?"}],
            "max_tokens": 16,
            "temperature": 0.2
        }).encode("utf-8")

        # Resolver endpoint correcto (/v1/chat/completions)
        edge_url = EDGE_BASE.rstrip("/")
        if not edge_url.endswith("/v1"):
            edge_url += "/v1"
        edge_url += "/chat/completions"

        req = request.Request(
            edge_url,
            data=payload,
            method="POST"
        )
        req.add_header("Content-Type", "application/json")

        start = time.time()
        with request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latency = (time.time() - start) * 1000

            # Parsear respuesta de inferencia compat
            choices = data.get("choices") or []
            result = ""
            if choices and isinstance(choices[0], dict):
                result = str((choices[0].get("message") or {}).get("content", "")).strip()

            print(f"  ✅ Respuesta recibida en {latency:.0f}ms")
            print(f"     '{result[:100]}'")
    except Exception as e:
        print(f"  ❌ Error en inferencia: {type(e).__name__}: {e}")

print("\n" + "="*80)
print("✅ Diagnóstico completado\n")
