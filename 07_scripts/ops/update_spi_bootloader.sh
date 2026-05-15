#!/usr/bin/env bash
# <!-- SISTEMA_TESIS:PROTEGIDO -->
# update_spi_bootloader.sh - Actualización atómica de U-Boot en SPI Flash para Orange Pi 5 Plus
# Versión: 1.0 | Fecha: 2026-05-01

set -euo pipefail

# --- Configuración ---
MTD_DEVICE="/dev/mtd0"
SPI_BACKUP_DIR="/var/lib/herramientas/openclaw/backups/spi"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "--- Actualización de SPI Bootloader (Protocolo Seguro) ---"

# 1. Verificación de privilegios
if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] Este script debe ejecutarse como root."
   exit 1
fi

# 2. Verificar existencia del dispositivo MTD
if [ ! -e "${MTD_DEVICE}" ]; then
    echo "[ERROR] Dispositivo SPI Flash (${MTD_DEVICE}) no encontrado."
    echo "Asegúrese de que el módulo 'mtd' esté cargado y el hardware sea compatible."
    exit 1
fi

# 3. Respaldo Atómico del estado actual
mkdir -p "${SPI_BACKUP_DIR}"
BACKUP_FILE="${SPI_BACKUP_DIR}/spi_dump_${TIMESTAMP}.img"
echo "[INFO] Realizando dump de seguridad del SPI actual..."
dd if="${MTD_DEVICE}" of="${BACKUP_FILE}" bs=1M status=progress
echo "[OK] Respaldo guardado en ${BACKUP_FILE}"

# 4. Preparación de Nueva Imagen (Simulado / Requiere URL)
# En un entorno real, aquí se descargaría la imagen y se verificaría su SHA256.
if [ $# -eq 0 ]; then
    echo "[INFO] No se proporcionó imagen de bootloader. El script finaliza tras el respaldo."
    echo "Uso: $0 <ruta_a_bootloader.img> <sha256_sum>"
    exit 0
fi

NEW_IMAGE="$1"
EXPECTED_SHA="$2"

# 5. Verificación de Integridad antes de flashear
echo "[INFO] Verificando integridad de la nueva imagen..."
ACTUAL_SHA=$(sha256sum "${NEW_IMAGE}" | awk '{print $1}')

if [ "${ACTUAL_SHA}" != "${EXPECTED_SHA}" ]; then
    echo "[ERROR] Hash de imagen no coincide. ABORTANDO FLASHEO POR SEGURIDAD."
    echo "Esperado: ${EXPECTED_SHA}"
    echo "Actual:   ${ACTUAL_SHA}"
    exit 1
fi
echo "[OK] Hash verificado correctamente."

# 6. Flasheo Atómico (Uso de flashcp si está disponible, sino dd)
echo "[CAUTION] Iniciando flasheo de SPI Flash. NO INTERRUMPA LA ENERGÍA."
if command -v flashcp >/dev/null 2>&1; then
    flashcp -v "${NEW_IMAGE}" "${MTD_DEVICE}"
else
    echo "[WARNING] flashcp no encontrado. Usando dd (menos seguro)..."
    dd if="${NEW_IMAGE}" of="${MTD_DEVICE}" bs=1M conv=fsync status=progress
fi

echo "[SUCCESS] Actualización de bootloader completada."
echo "Se recomienda realizar un ciclo de apagado completo (Cold Boot)."
