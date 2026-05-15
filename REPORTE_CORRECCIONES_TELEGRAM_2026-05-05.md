#!/usr/bin/env python3
"""
Reporte y correcciones para errores de Telegram - Sistema Operativo de Tesis
Generado: 2026-05-05
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path("runtime/openclaw/state/openclaw.db")

print("\n" + "="*90)
print("📋 REPORTE DE ERRORES Y CORRECCIONES - Bot Telegram OpenClaw")
print("="*90 + "\n")

# Análisis de eventos
conn = sqlite3.connect(str(DB_PATH))
c = conn.cursor()

c.execute('''
    SELECT COUNT(*), 
           SUM(CASE WHEN status='delivered' THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='IGNORED_UNAUTHORIZED' THEN 1 ELSE 0 END)
    FROM telegram_events
''')

total, delivered, unauthorized = c.fetchone()

print("📊 RESUMEN DE EVENTOS")
print("-" * 90)
print(f"  Total eventos:          {total}")
print(f"  Entregados exitosos:    {delivered} ({100*delivered/total:.0f}%)")
print(f"  No autorizados:         {unauthorized}")
print(f"  Con errores:            {total - delivered - unauthorized} ({100*(total-delivered-unauthorized)/total:.0f}%)")

print("\n\n🔴 PROBLEMAS IDENTIFICADOS")
print("-" * 90)

issues = [
    {
        "id": "ISSUE-001",
        "severity": "CRÍTICO",
        "title": "Backend de Inferencia Desktop Caído (Puerto 21434)",
        "description": "OPENCLAW_DESKTOP_RUNTIME_BASE_URL=http://127.0.0.1:21434 no responde",
        "impact": "Bot no puede usar modelos de escritorio (mistral-nemo:12b)",
        "root_cause": "Servicio LlamaCPP no está corriendo en :21434",
        "affected_events": ["TGM-59fec76a562e", "TGM-bc6338d91cd3", "TGM-c71a142ac612"],
        "solution": """
1. Verificar si está instalado llama.cpp:
   - Si no: Descargar desde https://github.com/ggerganov/llama.cpp/releases
   
2. Iniciar servidor LlamaCPP:
   - Windows: llama-server.exe -m mistral-nemo-12b.gguf -ngl 35 --port 21434 --host 127.0.0.1
   - o usar: 07_scripts/run_llamacpp_server.sh
   
3. Verificar: curl http://127.0.0.1:21434/health
        """
    },
    {
        "id": "ISSUE-002",
        "severity": "CRÍTICO",
        "title": "Backend Edge (Orange Pi) No Responde en Puerto 11434",
        "description": "OPENCLAW_EDGE_OLLAMA_BASE_URL=http://192.168.1.124:11434 está caído",
        "impact": "Fallback a modelos de borde no funciona",
        "root_cause": "Servicio Ollama en Orange Pi no escucha en :11434",
        "affected_events": ["TGM-59fec76a562e", "TGM-bc6338d91cd3", "TGM-c71a142ac612"],
        "solution": """
1. SSH a Orange Pi:
   ssh tesisai@192.168.1.124 -i $ORANGEPI_KEY_PATH
   
2. Verificar estado de Ollama:
   systemctl status ollama
   
3. Si no está corriendo:
   systemctl start ollama
   
4. Verificar puerto:
   curl http://192.168.1.124:11434/api/tags
   
5. Si sigue sin funcionar:
   # Revisar logs
   journalctl -u ollama -n 50 --no-pager
   # O iniciar manualmente en foreground
   ollama serve --host 0.0.0.0:11434
        """
    },
    {
        "id": "ISSUE-003",
        "severity": "ALTO",
        "title": "Falta Fallback a Servicios Locales",
        "description": "Cuando todos los backends fallan, bot retorna 'saturado' genérico",
        "impact": "Usuario no recibe diagnóstico útil de qué backend falló",
        "root_cause": "Código de error agrupado sin detalles específicos por provider",
        "affected_events": ["TGM-59fec76a562e", "TGM-bc6338d91cd3", "TGM-c71a142ac612"],
        "solution": """
Implementar mejora en telegram_bot.py:
- Registrar error específico de cada backend
- Diferencia entre "timeout", "conexión rechazada", "modelo_no_disponible"
- Mejorar mensaje de error para el usuario
        """
    }
]

for i, issue in enumerate(issues, 1):
    print(f"\n{i}. {issue['id']} [{issue['severity']}]")
    print(f"   Título: {issue['title']}")
    print(f"   Descripción: {issue['description']}")
    print(f"   Impacto: {issue['impact']}")
    print(f"   Causa Raíz: {issue['root_cause']}")
    print(f"   Afecta a {len(issue['affected_events'])} evento(s)")
    print(f"\n   SOLUCIÓN:")
    for line in issue['solution'].strip().split('\n'):
        print(f"   {line}")

print("\n\n✅ CORRECCIONES IMPLEMENTADAS")
print("-" * 90)

corrections = [
    {
        "id": "FIX-001",
        "file": "07_scripts/diagnose_backends.py",
        "status": "✅ CREADO",
        "description": "Script de diagnóstico para identificar backends caídos"
    },
    {
        "id": "FIX-002",
        "file": "check_telegram_issues.py",
        "status": "✅ CREADO",
        "description": "Analizador de errores en historial de Telegram"
    },
    {
        "id": "FIX-003",
        "file": "Este reporte",
        "status": "✅ GENERADO",
        "description": "Documentación de problemas y soluciones"
    }
]

for fix in corrections:
    print(f"\n✓ {fix['id']}: {fix['status']}")
    print(f"  Archivo: {fix['file']}")
    print(f"  Descripción: {fix['description']}")

print("\n\n📋 PLAN DE ACCIÓN RECOMENDADO")
print("-" * 90)

plan = """
INMEDIATO (Próximos 5 minutos):
  1. Ejecutar: python diagnose_backends.py
  2. Identificar qué backend está caído
  3. Iniciar servicio correspondiente:
     - Si falta Desktop: iniciar llama.cpp
     - Si falta Edge: SSH a Orange Pi y reiniciar Ollama

CORTO PLAZO (Próxima sesión):
  4. Implementar mejora de errores en telegram_bot.py
     - Registrar error específico de cada backend
     - Enviar diagnóstico al usuario (no solo "saturado")
  
  5. Crear scripts de autoarranque:
     - 07_scripts/start_backends.sh
     - Verificación automática de salud cada 5 minutos

MEDIANO PLAZO:
  6. Implementar reintentos con backoff exponencial
  7. Cache de disponibilidad de backends
  8. Alertas proactivas en Telegram si backend cae
"""

for line in plan.strip().split('\n'):
    print(f"  {line}")

print("\n\n🔗 REFERENCIAS")
print("-" * 90)
print(f"  • BD de eventos: {DB_PATH}")
print(f"  • Env config: config/env/openclaw.env")
print(f"  • Bot source: runtime/openclaw/openclaw_local/telegram_bot.py")
print(f"  • Backends config: Línea ~1466 en telegram_bot.py")

print("\n\n📌 EVENTOS CON ERROR DE SATURACIÓN")
print("-" * 90)

c.execute('''
    SELECT event_id, command, created_at, payload_json
    FROM telegram_events
    WHERE payload_json LIKE '%saturado%'
    ORDER BY created_at DESC
''')

saturated = c.fetchall()
for event_id, cmd, created_at, payload_str in saturated:
    payload = json.loads(payload_str)
    print(f"\n[{event_id}] {created_at}")
    print(f"  Comando: {cmd}")
    print(f"  User: {payload.get('text', '')[:60]}")
    print(f"  Response: {payload.get('response', '')[:80]}...")

conn.close()

print("\n" + "="*90)
print("✅ Reporte completado")
print("="*90 + "\n")

_Última actualización: `2026-05-15`._
