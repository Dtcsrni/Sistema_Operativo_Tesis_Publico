#!/usr/bin/env python3
"""
setup_telegram.py -- Configura y valida el canal de comunicación de OpenClaw.
Parte del Sistema Operativo de Tesis de Posgrado.
"""

import os
import sys
from pathlib import Path
from urllib import request, error
import json

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def validate_token(token):
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        with request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("ok"):
                return True, data["result"]["username"]
    except Exception:
        return False, None
    return False, None

def update_env(token, chat_id):
    env_path = Path("config/env/openclaw.env")
    if not env_path.exists():
        print(f"[ERROR] No se encontró {env_path}")
        return False
    
    lines = env_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    
    token_set = False
    chat_id_set = False
    
    for line in lines:
        if line.startswith("OPENCLAW_TELEGRAM_TOKEN=") or line.startswith("OPENCLAW_TELEGRAM_BOT_TOKEN="):
            new_lines.append(f"OPENCLAW_TELEGRAM_BOT_TOKEN={token}")
            token_set = True
        elif line.startswith("OPENCLAW_TELEGRAM_CHAT_ID="):
            new_lines.append(f"OPENCLAW_TELEGRAM_CHAT_ID={chat_id}")
            chat_id_set = True
        else:
            new_lines.append(line)
            
    if not token_set:
        new_lines.append(f"OPENCLAW_TELEGRAM_BOT_TOKEN={token}")
    if not chat_id_set:
        new_lines.append(f"OPENCLAW_TELEGRAM_CHAT_ID={chat_id}")
        
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return True

def main():
    clear_screen()
    print("====================================================")
    print("   OPENCLAW TELEGRAM SETUP - SISTEMA DE TESIS")
    print("====================================================\n")
    
    print("Este script configurará tu Asistente Científico.")
    print("Necesitas el Token de @BotFather.")
    
    token = input("\n[1/2] Introduce tu Telegram Bot Token: ").strip()
    
    print("\nValidando token con Telegram API...")
    ok, username = validate_token(token)
    
    if not ok:
        print("[FAIL] El token parece inválido o no hay conexión a internet.")
        sys.exit(1)
        
    print(f"[OK] Bot detectado: @{username}")
    
    print("\n[2/2] Ahora necesito tu Chat ID.")
    print("Si no lo sabes, envía un mensaje al bot y luego presiona Enter.")
    input("Presiona Enter cuando hayas enviado un mensaje al bot...")
    
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    chat_id = None
    try:
        with request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get("ok") and data["result"]:
                # Tomar el último chat_id que envió un mensaje
                last_update = data["result"][-1]
                chat_id = last_update.get("message", {}).get("chat", {}).get("id")
    except Exception as e:
        print(f"[WARN] Error al obtener actualizaciones: {e}")

    if not chat_id:
        chat_id = input("No pude detectarlo automáticamente. Introdúcelo manualmente: ").strip()
    else:
        print(f"[OK] Chat ID detectado: {chat_id}")
        confirm = input(f"¿Es {chat_id} tu ID correcto? (s/n): ").lower()
        if confirm != 's':
            chat_id = input("Introduce el Chat ID correcto: ").strip()

    if update_env(token, chat_id):
        print("\n[SUCCESS] Configuración guardada en config/env/openclaw.env")
        print("Ahora puedes reiniciar el servicio de OpenClaw.")
    else:
        print("\n[FAIL] No se pudo actualizar el archivo .env")

if __name__ == "__main__":
    main()
