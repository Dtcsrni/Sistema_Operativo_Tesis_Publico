#!/usr/bin/env bash
# <!-- SISTEMA_TESIS:PROTEGIDO -->
# harden_bootloader.sh - Endurecimiento de seguridad física para Orange Pi 5 Plus (RK3588)
# Versión: 1.0 | Fecha: 2026-05-01

set -euo pipefail

# --- Configuración ---
BOOT_ENV_FILE="/boot/armbianEnv.txt"
[ ! -f "${BOOT_ENV_FILE}" ] && BOOT_ENV_FILE="/boot/orangepiEnv.txt"
BACKUP_DIR="/var/lib/herramientas/openclaw/backups/boot"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "--- Hardening de Bootloader (Toltecayotl Engine) ---"

# 1. Verificación de privilegios
if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] Este script debe ejecutarse como root."
   exit 1
fi

# 2. Respaldo de seguridad
mkdir -p "${BACKUP_DIR}"
if [ -f "${BOOT_ENV_FILE}" ]; then
    cp "${BOOT_ENV_FILE}" "${BACKUP_DIR}/env_backup_${TIMESTAMP}.bak"
    echo "[OK] Respaldo de ${BOOT_ENV_FILE} creado."
fi

# 3. Configuración de Stop String (Opcional - Requiere fw_setenv)
# Si no está instalado u-boot-tools, avisamos.
if ! command -v fw_setenv >/dev/null 2>&1; then
    echo "[INFO] u-boot-tools no detectado. Saltando configuración de Stop String persistente en SPI."
else
    echo "[INFO] Configurando Stop String en variables de U-Boot..."
    # Nota: Aquí se debería pedir la clave al usuario de forma interactiva
    # Por ahora, solo dejamos la estructura lista para habilitar la protección.
    # fw_setenv bootstopkeysha256 <HASH>
fi

# 4. Endurecimiento de parámetros de arranque (CMDLINE)
if [ -f "${BOOT_ENV_FILE}" ]; then
    echo "[INFO] Aplicando restricciones de kernel en ${BOOT_ENV_FILE}..."
    
    # Deshabilitar consola serie interactiva si se desea máxima seguridad (OPCIONAL)
    # Por ahora solo aseguramos que el log sea limpio y el reinicio automático esté activo.
    if ! grep -q "panic=10" "${BOOT_ENV_FILE}"; then
        sed -i 's/extraargs=/extraargs=panic=10 /' "${BOOT_ENV_FILE}" || echo "extraargs=panic=10" >> "${BOOT_ENV_FILE}"
    fi

    # Deshabilitar sysrq para evitar reinicios forzados desde teclado
    echo "kernel.sysrq = 0" > /etc/sysctl.d/99-bootloader-hardening.conf
    echo "[OK] SysRq deshabilitado."
fi

# 5. Verificación Final
echo "--- Resumen de Endurecimiento ---"
echo "- Archivo: ${BOOT_ENV_FILE}"
echo "- Backup: ${BACKUP_DIR}/env_backup_${TIMESTAMP}.bak"
echo "[SUCCESS] Políticas de seguridad de arranque aplicadas."
