#!/usr/bin/env bash
# <!-- SISTEMA_TESIS:PROTEGIDO -->
# sync_toltecayotl_to_edge.sh — Sincroniza el acervo epistémico (TEB) con el nodo Edge.
# Versión: 1.0 | Fecha: 2026-05-01

set -euo pipefail

# --- Cargar Configuración (Toltecayotl) ---
CONFIG_DIR="config/env"
if [ -f "${CONFIG_DIR}/toltecayotl.env" ]; then
    echo "[INFO] Cargando configuración desde ${CONFIG_DIR}/toltecayotl.env"
    # shellcheck disable=SC1091
    source "${CONFIG_DIR}/toltecayotl.env"
fi

# --- Configuración (Valores por defecto si no están en .env) ---
EDGE_IP="${TESIS_EDGE_IP:-192.168.1.124}"
EDGE_USER="${TESIS_EDGE_USER:-tesisai}"
IDENTITY_FILE="${TESIS_SSH_KEY:-/mnt/c/Users/evega/.ssh/id_ed25519_orangepi_nopass}"

LOCAL_TEB_DIR="${TESIS_LOCAL_TEB_DIR:-00_sistema_tesis/05_registros_de_ingestion/teb/}"
REMOTE_KNOWLEDGE_DIR="${TESIS_REMOTE_KNOWLEDGE_DIR:-~/runtime/knowledge}"
REMOTE_TEB_DIR="${REMOTE_KNOWLEDGE_DIR}/teb/"

# Detección de entorno (WSL vs Native Linux)
if [ ! -f "${IDENTITY_FILE}" ]; then
    # Intentar ruta local si no es WSL
    IDENTITY_FILE="${HOME}/.ssh/id_ed25519_orangepi_nopass"
fi

# Manejo de permisos de llave SSH (WSL Fix)
if [[ "${IDENTITY_FILE}" == /mnt/* ]]; then
    echo "[INFO] Detectada llave en /mnt/. Corrigiendo permisos para SSH..."
    TMP_KEY="/tmp/id_sync_edge"
    cp "${IDENTITY_FILE}" "${TMP_KEY}"
    chmod 600 "${TMP_KEY}"
    IDENTITY_FILE="${TMP_KEY}"
fi

echo "--- Sincronización Toltecayotl (PC -> Edge) ---"

# 1. Verificar existencia de origen
if [ ! -d "${LOCAL_TEB_DIR}" ]; then
    echo "[ERROR] Directorio local TEB no encontrado: ${LOCAL_TEB_DIR}"
    exit 1
fi

# 2. Detección de Túnel Reverso (Puerto 2222)
if command -v netstat >/dev/null 2>&1; then
    if netstat -an | grep -q "2222"; then
        echo "[INFO] Túnel reverso detectado. Redirigiendo a localhost:2222"
        EDGE_IP="localhost"
        SSH_ARGS="-p 2222"
    else
        SSH_ARGS=""
    fi
else
    SSH_ARGS=""
fi

# 3. Asegurar directorios remotos
echo "[INFO] Asegurando directorios en el Edge..."
ssh ${SSH_ARGS} -i "${IDENTITY_FILE}" "${EDGE_USER}@${EDGE_IP}" "mkdir -p ${REMOTE_TEB_DIR}"

# 4. Sincronización de Bundles TEB (.jsonl firmados)
echo "[INFO] Transfiriendo cápsulas de conocimiento (.jsonl)..."
rsync -avz ${SSH_ARGS} -e "ssh -i ${IDENTITY_FILE}" --progress \
    "${LOCAL_TEB_DIR}" \
    "${EDGE_USER}@${EDGE_IP}:${REMOTE_TEB_DIR}"

# 5. Sincronización de Índices de Ingestión
echo "[INFO] Sincronizando índices maestros..."
rsync -avz ${SSH_ARGS} -e "ssh -i ${IDENTITY_FILE}" \
    "00_sistema_tesis/05_registros_de_ingestion/indice_maestro_ingestion_contexto_iot.csv" \
    "${EDGE_USER}@${EDGE_IP}:${REMOTE_KNOWLEDGE_DIR}/"

if [ $? -eq 0 ]; then
    echo "[SUCCESS] Acervo epistémico sincronizado correctamente."
    echo "[INFO] Nodo Edge actualizado con hashes: $(ls -1 ${LOCAL_TEB_DIR} | wc -l) paquetes."
else
    echo "[ERROR] Falló la sincronización. Verifique conectividad con ${EDGE_IP}."
    exit 1
fi
