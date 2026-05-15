#!/usr/bin/env python3
import subprocess
import os
import sys
import argparse

def get_ram_usage():
    try:
        res = subprocess.check_output(["free", "-h"]).decode("utf-8")
        return res
    except:
        return "N/A"

def clean_node(force=False):
    print("=== Herramienta de Sanitización de Nodo (DEC-0038) ===")
    print(f"Estado inicial de memoria:\n{get_ram_usage()}")
    
    # Rutas de unidades de usuario
    user_unit_path = "/root/.config/systemd/user/"
    backup_path = "/root/.config/systemd/user_backup/"
    units = ["openclaw-llamacpp-server.service", "openclaw-desktop-tunnel.service", "openclaw-gateway.service"]
    
    if not force:
        confirm = input("\n¿Deseas proceder con el AISLAMIENTO FÍSICO de unidades? (s/n): ")
        if confirm.lower() != 's':
            print("Operación cancelada.")
            return

    print("\n[!] Iniciando aislamiento físico...")
    subprocess.run(["sudo", "mkdir", "-p", backup_path], check=False)
    
    for unit in units:
        src = os.path.join(user_unit_path, unit)
        dst = os.path.join(backup_path, unit)
        if os.path.exists(src):
            print(f"[*] Desplazando {unit} a reserva...")
            subprocess.run(["sudo", "mv", src, dst], check=False)

    print("[*] Recargando configuración de systemd...")
    subprocess.run(["sh", "-c", "export XDG_RUNTIME_DIR=/run/user/0 && systemctl --user daemon-reload"], check=False)
    
    # Detener servicios de sistema (Ollama/Docker)
    services = [
        ("Ollama (Sistema)", "sudo systemctl disable --now ollama"),
        ("Docker Service", "sudo systemctl disable --now docker.service"),
    ]
    for name, cmd in services:
        print(f"[*] Desactivando {name}...")
        subprocess.run(cmd.split(), check=False)

    # Limpieza final SIGKILL
    print("[*] Ejecutando limpieza SIGKILL final...")
    subprocess.run(["sh", "-c", "pkill -9 -f llama-server"], check=False)
    subprocess.run(["sh", "-c", "pkill -9 -f openclaw-gateway"], check=False)

    print("\n[OK] Entorno blindado físicamente.")
    print(f"Estado final de memoria:\n{get_ram_usage()}")

def restore_node():
    print("=== Restauración de Nodo (DEC-0038) ===")
    user_unit_path = "/root/.config/systemd/user/"
    backup_path = "/root/.config/systemd/user_backup/"
    units = ["openclaw-llamacpp-server.service", "openclaw-desktop-tunnel.service", "openclaw-gateway.service"]

    print("[*] Restaurando archivos de unidad...")
    for unit in units:
        src = os.path.join(backup_path, unit)
        dst = os.path.join(user_unit_path, unit)
        if os.path.exists(src):
            print(f"[*] Devolviendo {unit} a su ruta original...")
            subprocess.run(["sudo", "mv", src, dst], check=False)

    print("[*] Recargando systemd y re-activando servicios...")
    subprocess.run(["sh", "-c", "export XDG_RUNTIME_DIR=/run/user/0 && systemctl --user daemon-reload"], check=False)
    
    # Re-activar todo
    subprocess.run(["sudo", "systemctl", "enable", "--now", "ollama"], check=False)
    subprocess.run(["sudo", "systemctl", "enable", "--now", "docker.service"], check=False)
    
    # Iniciar servicios de usuario clave
    subprocess.run(["sh", "-c", "export XDG_RUNTIME_DIR=/run/user/0 && systemctl --user start openclaw-gateway.service"], check=False)
    subprocess.run(["sh", "-c", "export XDG_RUNTIME_DIR=/run/user/0 && systemctl --user start openclaw-llamacpp-server.service"], check=False)
    
    print("\n[OK] Servicios restaurados.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sanitizador de recursos para tareas críticas.")
    parser.add_argument("--force", action="store_true", help="Ejecutar sin pedir confirmación.")
    parser.add_argument("--restore", action="store_true", help="Restaurar los servicios previamente detenidos.")
    args = parser.parse_args()
    
    # Este script debe ejecutarse en WSL
    if os.name == 'nt':
        print("[!] Este script está diseñado para ejecutarse dentro de WSL.")
        sys.exit(1)
        
    if args.restore:
        restore_node()
    else:
        clean_node(force=args.force)
