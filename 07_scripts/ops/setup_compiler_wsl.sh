#!/usr/bin/env bash
# setup_compiler_wsl.sh — Prepara el entorno WSL Ubuntu para la compilación RKLLM.
# Uso: bash 07_scripts/setup_compiler_wsl.sh

set -euo pipefail

echo "=== SIOT: Preparando entorno de compilación RKLLM en WSL ==="

# 1. Instalar dependencias base
sudo apt-get update
sudo apt-get install -y git git-lfs python3-pip python3-venv libglib2.0-0 libsm6 libxext6 libxrender-dev

# 2. Instalar PyTorch (CPU) como prerrequisito para auto_gptq
echo "[INFO] Instalando PyTorch (CPU)..."
python3 -m pip install torch --index-url https://download.pytorch.org/whl/cpu --break-system-packages

# 3. Clonar SDK de Rockchip (Shallow clone para ahorrar tiempo)
if [ ! -d "/tmp/rknn-llm" ]; then
    echo "[INFO] Clonando RKNN-LLM SDK..."
    git clone --depth 1 -b release-v1.2.3 https://github.com/airockchip/rknn-llm.git /tmp/rknn-llm
fi

# 3. Instalar Toolkit en el entorno del sistema (o venv)
echo "[INFO] Instalando rkllm-toolkit..."
cd /tmp/rknn-llm/rkllm-toolkit/packages
# Nota: Ajustar según versión de Python. El SDK v1.2.3 incluye wheels para cp38-cp312.
PYTHON_VER=$(python3 -c "import sys; print(f'cp{sys.version_info.major}{sys.version_info.minor}')")
WHEEL=$(ls | grep "${PYTHON_VER}" | grep "x86_64" | head -n 1)

if [ -z "${WHEEL}" ]; then
    echo "[ERROR] No se encontró un wheel compatible para ${PYTHON_VER} x86_64."
    exit 1
fi

sudo pip3 install "${WHEEL}" --break-system-packages

echo "[OK] Entorno listo. Ahora puedes ejecutar la compilación:"
echo "python3 07_scripts/compile_rkllm.py --model meta-llama/Llama-3.2-3B-Instruct"
