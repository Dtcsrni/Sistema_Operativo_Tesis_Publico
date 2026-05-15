#!/usr/bin/env python3
"""Verificación rápida del stack operativo (Edge + Serena)."""

import sys
import socket
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("\n" + "="*80)
print("🔍 VERIFICACIÓN ESTADO REAL - STACK DISTRIBUIDO + AUTONOMÍA")
print("="*80 + "\n")

# Leer configuración real
env_file = Path("config/env/openclaw.env")
env_vars = {}

if env_file.exists():
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                env_vars[key] = val.strip('"')

print("📋 CONFIGURACIÓN REAL")
print("-" * 80)
print(f"Edge (Ollama):              {env_vars.get('OPENCLAW_EDGE_OLLAMA_BASE_URL', 'NO CONFIGURADO')}")
print(f"Serena MCP:                 {env_vars.get('OPENCLAW_SERENA_URL', 'NO CONFIGURADO')}")
print(f"Repo Root:                  {env_vars.get('OPENCLAW_REPO_ROOT', 'NO CONFIGURADO')}")

print("\n\n🔌 CONECTIVIDAD")
print("-" * 80)

def test_connection(host: str, port: int, name: str) -> bool:
    """Prueba conexión a un servicio."""
    try:
        # Handle cases where host might be an URL
        if "://" in host:
            host = host.split("://")[1].split("/")[0]
        if ":" in host:
            host = host.split(":")[0]
            
        sock = socket.create_connection((host, port), timeout=2)
        sock.close()
        print(f"✅ {name:40} {host}:{port} → OK")
        return True
    except ConnectionRefusedError:
        print(f"❌ {name:40} {host}:{port} → Conexión rechazada (caído)")
        return False
    except Exception as e:
        print(f"⚠️  {name:40} {host}:{port} → {type(e).__name__}")
        return False

# Parsear URLs configuradas
def parse_url(url: str) -> tuple:
    """Extrae host y puerto de una URL."""
    if not url:
        return "localhost", 80
    
    # Remove protocol
    if "://" in url:
        proto, rest = url.split("://", 1)
        default_port = 443 if proto == "https" else 80
        url = rest
    else:
        default_port = 80
        
    # Remove path
    url = url.split("/")[0]
    
    if ":" in url:
        try:
            host, port_str = url.rsplit(":", 1)
            if port_str.isdigit():
                return host or "localhost", int(port_str)
            return url, default_port
        except ValueError:
            return url, default_port
            
    return url or "localhost", default_port

status = {}

# Edge
edge_url = env_vars.get('OPENCLAW_EDGE_OLLAMA_BASE_URL', 'http://192.168.1.124:11434')
edge_host, edge_port = parse_url(edge_url)
status["edge"] = test_connection(edge_host, edge_port, "Edge (Ollama en Orange Pi)")

# Desktop
desktop_url = env_vars.get("OPENCLAW_DESKTOP_RUNTIME_BASE_URL", env_vars.get("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434"))
desktop_host, desktop_port = parse_url(desktop_url)
status["desktop"] = test_connection(desktop_host, desktop_port, "Desktop compute")

# Serena
serena_url = env_vars.get('OPENCLAW_SERENA_URL', 'http://127.0.0.1:8765/mcp')
serena_host, serena_port = parse_url(serena_url)
status["serena"] = test_connection(serena_host, serena_port, "Serena MCP (HTTP)")

print("\n\n🗄️ PERSISTENCIA")
print("-" * 80)

def check_db_integrity(db_path: str, name: str) -> bool:
    import sqlite3
    try:
        if not Path(db_path).exists():
            print(f"⚠️  {name:40} {db_path} → NO EXISTE (Se creará)")
            return True
        conn = sqlite3.connect(db_path)
        res = conn.execute("PRAGMA integrity_check;").fetchone()
        conn.close()
        if res == ("ok",):
            print(f"✅ {name:40} {db_path} → INTEGRIDAD OK")
            return True
        else:
            print(f"❌ {name:40} {db_path} → CORRUPTO: {res}")
            return False
    except Exception as e:
        print(f"⚠️  {name:40} {db_path} → Error: {type(e).__name__}")
        return False

db_mission = "04_implementacion/control_mission/mission-control.db"
status["db_mission"] = check_db_integrity(db_mission, "Mission Control DB")

print("\n\n🤖 SISTEMA DE AUTONOMÍA")
print("-" * 80)

# Verificar que los archivos de autonomía existen
autonomy_files = [
    ("07_scripts/start_backends_auto.py", "Script de auto-arranque"),
    ("07_scripts/diagnose_backends.py", "Script de diagnóstico"),
]

autonomy_ready = True
for file_path, description in autonomy_files:
    if Path(file_path).exists():
        print(f"✅ {description:30} {file_path}")
    else:
        print(f"❌ {description:30} NO ENCONTRADO")
        autonomy_ready = False

# Verificar que bot tiene integración
bot_path = Path("runtime/openclaw/openclaw_local/telegram_bot.py")
if bot_path.exists():
    content = bot_path.read_text(encoding="utf-8")
    if "_check_and_start_backends_if_needed" in content:
        print(f"✅ {'Función de autonomía':30} telegram_bot.py")
    else:
        print(f"❌ {'Función de autonomía':30} NO INTEGRADA")
        autonomy_ready = False
    
    if 'elif command in {"salud"' in content:
        print(f"✅ {'Comando /salud':30} telegram_bot.py")
    else:
        print(f"❌ {'Comando /salud':30} NO IMPLEMENTADO")
else:
    print(f"❌ {'telegram_bot.py':30} NO ENCONTRADO")
    autonomy_ready = False

print("\n\n📊 RESUMEN")
print("-" * 80)

print(f"\n🌐 Stack Distribuido:")
if status["edge"]:
    print(f"   ✅ Edge (Ollama):      {edge_host}:{edge_port} → LEVANTADO")
else:
    print(f"   ❌ Edge (Ollama):      {edge_host}:{edge_port} → CAÍDO")

print(f"\n🔧 Sistema de Autonomía:")
if autonomy_ready and (status["edge"] or status["desktop"]):
    print(f"   ✅ OPERATIVO - Can handle fallback")
elif autonomy_ready:
    print(f"   ✅ LISTO - Pero sin backends activos")
    print(f"      (Auto-arrancaría cuando usuario envíe mensaje)")
else:
    print(f"   ❌ NO LISTO - Faltan componentes")

print(f"\n🎯 Serena MCP:")
if status["serena"]:
    print(f"   ✅ ACTIVO: {serena_host}:{serena_port}")
else:
    print(f"   ❌ INACTIVO: {serena_host}:{serena_port}")

print(f"\n🗄️ Persistencia:")
if status["db_mission"]:
    print(f"   ✅ DB Misiones: INTEGRIDAD OK")
else:
    print(f"   ❌ DB Misiones: CORRUPCIÓN DETECTADA (Requiere mantenimiento)")

print("\n\n💡 ESTADO GENERAL")
print("-" * 80)

backends_ok = status["edge"]
autonomy_ok = autonomy_ready

if backends_ok and autonomy_ok:
    print("✅ TOTALMENTE OPERATIVO")
    print("   • Stack distribuido levantado")
    print("   • Sistema de autonomía integrado")
    print("   • Bot puede responder sin intervención manual")
elif autonomy_ok and not backends_ok:
    print("✅ EN STANDBY - LISTA PARA AUTO-ARRANQUE")
    print("   • Sistema de autonomía está integrado")
    print("   • Backends están caídos")
    print("   • Cuando usuario envíe mensaje:")
    print("     1. Bot detectará backends caídos")
    print("     2. Bot intentará levantarlos automáticamente")
    print("     3. Bot responderá la pregunta")
    print("   ")
    print("   ACTION: Enviar mensaje en Telegram para validar")
elif not autonomy_ok and backends_ok:
    print("⚠️  PARCIALMENTE OPERATIVO")
    print("   • Backends están levantados")
    print("   • Sistema de autonomía NO ESTÁ INTEGRADO")
    print("   • Bot responde pero sin respaldo automático si algo falla")
else:
    print("❌ NO OPERATIVO")
    print("   • Backends están caídos")
    print("   • Sistema de autonomía NO ESTÁ INTEGRADO")
    print("   • Bot no puede responder")

print("\n" + "="*80 + "\n")
