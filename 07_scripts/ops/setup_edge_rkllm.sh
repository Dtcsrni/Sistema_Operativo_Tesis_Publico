#!/usr/bin/env bash
# setup_edge_rkllm.sh — Instala librkllmrt.so y dependencias RKLLM en el edge (Orange Pi 5 Plus)
# Ejecutar en el edge: bash setup_edge_rkllm.sh
# O via SSH desde PC: ssh orangepi-lan 'bash -s' < 07_scripts/setup_edge_rkllm.sh

set -euo pipefail

RKLLM_VERSION="${RKLLM_VERSION:-1.2.3}"
DRIVERS_DIR="${HOME}/runtime/drivers/rknn"
MODELS_DIR="${HOME}/runtime/models/edge"
RKLLM_DL_BASE="https://github.com/airockchip/rknn-llm/releases/download/v${RKLLM_VERSION}"

echo "[INFO] Setup RKLLM v${RKLLM_VERSION} en edge RK3588"
echo "[INFO] Architecture: $(uname -m)"

# 1. Verificar NPU
if ls /dev/dri/renderD* 2>/dev/null | grep -q renderD; then
    echo "[OK] NPU DRM render detectada: $(ls /dev/dri/renderD*)"
else
    echo "[WARN] No se detectó /dev/dri/renderD* — verifica drivers NPU"
fi

# 2. Crear directorios
mkdir -p "${DRIVERS_DIR}" "${MODELS_DIR}"
echo "[INFO] Directorios: ${DRIVERS_DIR}, ${MODELS_DIR}"

# 3. Intentar descarga de librkllmrt.so desde GitHub Releases
LIB_URL="${RKLLM_DL_BASE}/librkllmrt.so"
LIB_DEST="${DRIVERS_DIR}/librkllmrt.so"

if [ -f "${LIB_DEST}" ]; then
    echo "[SKIP] librkllmrt.so ya existe en ${LIB_DEST}"
else
    echo "[INFO] Descargando librkllmrt.so..."
    if wget -q --timeout=30 -O "${LIB_DEST}" "${LIB_URL}" 2>/dev/null || \
       curl -fsSL --max-time 30 -o "${LIB_DEST}" "${LIB_URL}" 2>/dev/null; then
        echo "[OK] librkllmrt.so descargada en ${LIB_DEST}"
    else
        echo "[WARN] Descarga automática falló. Coloca manualmente librkllmrt.so en ${LIB_DEST}"
        echo "       Descarga desde: https://github.com/airockchip/rknn-llm/releases"
    fi
fi

# 4. Registrar en LD_LIBRARY_PATH si no está
if ! grep -q "${DRIVERS_DIR}" ~/.bashrc 2>/dev/null; then
    echo "export LD_LIBRARY_PATH=${DRIVERS_DIR}:\$LD_LIBRARY_PATH" >> ~/.bashrc
    echo "[OK] LD_LIBRARY_PATH actualizado en ~/.bashrc"
fi

# 5. Verificar Python deps
echo "[INFO] Verificando dependencias Python..."
python3 -c "import ctypes; print('[OK] ctypes disponible')" 2>/dev/null || echo "[WARN] ctypes no disponible"

# 6. Estado final
echo ""
echo "=== ESTADO FINAL RKLLM SETUP ==="
echo "librkllmrt.so: $([ -f ${LIB_DEST} ] && echo 'PRESENTE' || echo 'AUSENTE')"
echo "Drivers dir:   ${DRIVERS_DIR}"
echo "Models dir:    ${MODELS_DIR}"
echo ""
echo "SIGUIENTE PASO — Convertir modelo a formato .rkllm:"
echo "  Instala RKLLM-Toolkit: pip install rkllm-toolkit"
echo "  Convierte: python3 -c \"from rkllm.api import RKLLM; m=RKLLM(); m.load_huggingface('Qwen/Qwen2.5-3B-Instruct'); m.build(do_quantization=True, optimization_level=1); m.export_rkllm('${MODELS_DIR}/qwen2.5_3b.rkllm')\""
echo ""
echo "O descarga un modelo pre-convertido desde HuggingFace:"
echo "  https://huggingface.co/c01zaut/qwen2.5-3b-instruct-rk3588-rkllm"
