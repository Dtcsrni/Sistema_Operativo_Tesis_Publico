#!/usr/bin/env bash
# sync_pet_to_edge.sh — Sincroniza la biblioteca PET validada con la Orange Pi 5 Plus.

# Configuración (Usuario Agente IA Dedicado)
EDGE_IP="192.168.1.124"
EDGE_USER="tesisai"
IDENTITY_FILE="/mnt/c/Users/evega/.ssh/id_ed25519_orangepi_nopass"
LOCAL_PET_DIR="00_sistema_tesis/05_registros_de_ingestion/paquetes_pet/"
REMOTE_PET_DIR="~/runtime/knowledge/paquetes_pet/"

# Manejo de permisos de llave SSH (WSL Fix)
if [[ "${IDENTITY_FILE}" == /mnt/* ]]; then
    echo "[INFO] Detectada llave en /mnt/. Corrigiendo permisos para SSH..."
    TMP_KEY="/tmp/id_sync_pet"
    cp "${IDENTITY_FILE}" "${TMP_KEY}"
    chmod 600 "${TMP_KEY}"
    IDENTITY_FILE="${TMP_KEY}"
fi

echo "[*] Iniciando sincronización de paquetes PET hacia el Edge (${EDGE_IP})..."

# Asegurar que el directorio remoto existe
ssh -i ${IDENTITY_FILE} ${EDGE_USER}@${EDGE_IP} "mkdir -p ${REMOTE_PET_DIR}"

# Sincronizar vía rsync
rsync -avz -e "ssh -i ${IDENTITY_FILE}" --progress "${LOCAL_PET_DIR}" "${EDGE_USER}@${EDGE_IP}:${REMOTE_PET_DIR}"

if [ $? -eq 0 ]; then
    echo "[OK] Sincronización completada exitosamente."
    echo "[*] La Orange Pi ahora cuenta con la biblioteca de conocimiento validada."
else
    echo "[ERROR] Falló la sincronización. Verifica la conexión con el nodo Edge."
fi
