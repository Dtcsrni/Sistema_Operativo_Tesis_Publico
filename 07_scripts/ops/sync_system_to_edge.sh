#!/usr/bin/env bash
# <!-- SISTEMA_TESIS:PROTEGIDO -->
# sync_system_to_edge.sh — Sincronización integral (Código + Gobernanza + Conocimiento)
# Versión: 1.0 | Fecha: 2026-05-04

set -euo pipefail

# --- Cargar Configuración ---
CONFIG_DIR="config/env"
if [ -f "${CONFIG_DIR}/toltecayotl.env" ]; then
    source "${CONFIG_DIR}/toltecayotl.env"
fi

EDGE_IP="${TESIS_EDGE_IP:-192.168.1.124}"
EDGE_USER="${TESIS_EDGE_USER:-tesisai}"
IDENTITY_FILE="${TESIS_SSH_KEY:-/mnt/c/Users/evega/.ssh/id_ed25519_orangepi_nopass}"
REMOTE_BASE_DIR="/home/tesisai/Sistema_Operativo_Tesis_Posgrado"

# Manejo de permisos de llave SSH (WSL Fix)
if [[ "${IDENTITY_FILE}" == /mnt/* ]]; then
    TMP_KEY="/tmp/id_sync_system"
    cp "${IDENTITY_FILE}" "${TMP_KEY}"
    chmod 600 "${TMP_KEY}"
    IDENTITY_FILE="${TMP_KEY}"
fi

echo "--- Sincronización Integral (PC -> Edge) ---"

# 1. Asegurar directorio base remoto
ssh -i "${IDENTITY_FILE}" "${EDGE_USER}@${EDGE_IP}" "mkdir -p ${REMOTE_BASE_DIR}"

# 2. Sincronización con Exclusiones
echo "[INFO] Sincronizando código y gobernanza..."
rsync -avz -e "ssh -i ${IDENTITY_FILE}" --progress \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude 'runtime/temp_ingest' \
    --exclude '*.bak' \
    --exclude '*.db-shm' \
    --exclude '*.db-wal' \
    ./ \
    "${EDGE_USER}@${EDGE_IP}:${REMOTE_BASE_DIR}/"

if [ $? -eq 0 ]; then
    echo "[SUCCESS] Sistema sincronizado correctamente en el nodo Edge."
    echo "[INFO] Ubicación remota: ${REMOTE_BASE_DIR}"
else
    echo "[ERROR] Falló la sincronización integral."
    exit 1
fi
