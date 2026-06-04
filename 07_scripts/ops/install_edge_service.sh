#!/usr/bin/env bash
# ============================================================
# install_edge_service.sh
# Instalacion idempotente del servicio siot-edge en Orange Pi.
# Referencia: T-032 Servicios edge_iot (VAL-STEP-779)
# Uso: sudo bash 07_scripts/ops/install_edge_service.sh
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVICE_NAME="siot-edge.service"
SERVICE_SRC="${REPO_ROOT}/config/systemd/${SERVICE_NAME}"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}"
EDGE_ENV="${REPO_ROOT}/config/env/domains/edge.env"
REPO_SYMLINK="/srv/tesis/repo"
EDGE_USER="edge_ops"

log()  { echo "[$(date +'%H:%M:%S')] INFO:  $*"; }
warn() { echo "[$(date +'%H:%M:%S')] WARN:  $*" >&2; }
ok()   { echo "[$(date +'%H:%M:%S')] OK:    $*"; }
fail() { echo "[$(date +'%H:%M:%S')] ERROR: $*" >&2; exit 1; }

# Verificar root
[[ $EUID -eq 0 ]] || fail "Ejecutar como root: sudo bash $0"

log "=== Instalando siot-edge.service en $(hostname) ==="

# 1. Pre-check: dependencias
log "Verificando dependencias..."
command -v docker         >/dev/null 2>&1 || fail "Docker no encontrado. Instalar primero."
command -v docker compose >/dev/null 2>&1 \
  || docker compose version >/dev/null 2>&1 \
  || fail "docker compose plugin no encontrado."
id "${EDGE_USER}" >/dev/null 2>&1 || fail "Usuario ${EDGE_USER} no existe. Ejecutar primero harden_edge.sh."
[[ -f "${SERVICE_SRC}" ]] || fail "Archivo de servicio no encontrado: ${SERVICE_SRC}"
[[ -f "${EDGE_ENV}"    ]] || warn "Archivo de entorno no encontrado: ${EDGE_ENV} (crease antes de arrancar)"

# 2. Enlace simbolico del repo en /srv/tesis/repo (ruta canonica del servicio)
if [[ ! -L "${REPO_SYMLINK}" ]]; then
    log "Creando enlace simbolico ${REPO_SYMLINK} -> ${REPO_ROOT}..."
    mkdir -p /srv/tesis
    ln -sfn "${REPO_ROOT}" "${REPO_SYMLINK}"
    ok "Enlace creado: ${REPO_SYMLINK}"
else
    ok "Enlace simbolico ya existe: ${REPO_SYMLINK} -> $(readlink -f ${REPO_SYMLINK})"
fi

# 3. Asegurar que edge_ops tenga el repo en lectura (no escritura al canon)
chown -h root:docker "${REPO_SYMLINK}" 2>/dev/null || true

# 4. Instalar la unidad de servicio
if [[ -f "${SERVICE_DST}" ]]; then
    log "Unidad existente detectada, actualizando..."
    cp "${SERVICE_DST}" "${SERVICE_DST}.bak.$(date +%Y%m%d_%H%M%S)"
fi
install -m 0644 "${SERVICE_SRC}" "${SERVICE_DST}"
ok "Servicio instalado: ${SERVICE_DST}"

# 5. Recargar Systemd y habilitar el servicio
log "Recargando Systemd daemon..."
systemctl daemon-reload

log "Habilitando siot-edge para arranque automatico..."
systemctl enable "${SERVICE_NAME}"
ok "Servicio habilitado en arranque del sistema."

# 6. Arrancar si no esta ya corriendo
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    log "Servicio ya activo, recargando configuracion..."
    systemctl reload-or-restart "${SERVICE_NAME}"
else
    log "Arrancando ${SERVICE_NAME}..."
    systemctl start "${SERVICE_NAME}" || {
        warn "Error al arrancar. Mostrando logs:"
        journalctl -u "${SERVICE_NAME}" -n 30 --no-pager
        fail "El servicio no arranco correctamente."
    }
fi

# 7. Verificacion post-instalacion
sleep 3
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    ok "=== ${SERVICE_NAME} corriendo correctamente ==="
    systemctl status "${SERVICE_NAME}" --no-pager -l
else
    warn "El servicio no esta activo despues de 3 segundos."
    journalctl -u "${SERVICE_NAME}" -n 20 --no-pager
    fail "Verificacion fallida."
fi
