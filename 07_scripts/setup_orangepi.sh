#!/usr/bin/env bash

# Script de instalación y arranque para Orange Pi 5 Plus (Linux ARM64 - Ubuntu/Debian/Armbian)
# Prepara el entorno del Sistema Operativo de Tesis asegurando dependencias nativas instaladas a nivel sistema.

set -e # Detiene ejecución si ocurre un error

echo "[SETUP] Actualizando repositorios base de apt..."
sudo apt-get update -y

echo "[SETUP] Instalando entorno de Python3, pip, Git y dependencias esenciales de compilación..."
# python3-dev y build-essential son fundamentales en ARM para compilar librerías de datos o DVC (orjson/aiohttp) si no hay wheels ARM64 disponibles.
sudo apt-get install -y python3 python3-venv python3-pip git build-essential python3-dev

echo "[SETUP] Creando entorno virtual local (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "[SETUP] Entorno virtual .venv creado exitosamente."
else
    echo "[SETUP] El entorno virtual .venv ya existe, omitiendo creación."
fi

echo "[SETUP] Instalando dependencias del proyecto (pytest, pre-commit, dvc)..."
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements-dev.txt

echo "[SETUP] Instalando hooks de pre-commit para auto-validaciones locales..."
./.venv/bin/pre-commit install
./.venv/bin/pre-commit install --hook-type pre-push

echo "[SETUP] Inicializando DVC (Data Version Control) de manera local si no existe..."
if [ ! -d ".dvc" ]; then
    ./.venv/bin/dvc init
    echo "[SETUP] DVC inicializado correctamente."
else
    echo "[SETUP] DVC ya estaba inicializado, omitiendo."
fi

echo "[SETUP] Regenerando Dashboard de Tesis inicial..."
./.venv/bin/python 07_scripts/build_all.py

echo "---------------------------------------------------------"
echo "[¡ÉXITO!] El Sistema Operativo de Tesis está listo en tu Orange Pi."
echo ""
echo "Recuerda activar el entorno antes de trabajar:"
echo "    source .venv/bin/activate"
echo ""
echo "Y para compilar de nuevo todos tus archivos, corre:"
echo "    python 07_scripts/build_all.py"
echo "---------------------------------------------------------"
