#!/usr/bin/env bash
# Script idempotente para endurecimiento de nodos Edge (Orange Pi)
# Referencia: T-031 Hardening edge_iot
# Ejecucion esperada: sudo bash harden_edge.sh

set -euo pipefail

log() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] INFO: $1"
}

warn() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] WARN: $1" >&2
}

error() {
    echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')] ERROR: $1" >&2
    exit 1
}

if [[ $EUID -ne 0 ]]; then
   error "Este script debe ser ejecutado como root (sudo)."
fi

log "Iniciando proceso de hardening del nodo Edge..."

# 1. Actualizar repositorios e instalar paquetes base
log "Instalando paquetes de seguridad requeridos..."
apt-get update -qq
apt-get install -y -qq ufw fail2ban unattended-upgrades

# 2. Configuracion de UFW
log "Configurando UFW..."
# Asegurarse de no desconectar la sesion actual si estamos via SSH
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
# Puertos requeridos por Edge IoT segun arquitectura (por ejemplo, puertos LLM o Docker si aplican)
# Asumiendo puerto 11434 para Ollama/llama.cpp si se expone, pero como es local o via tunneling,
# por defecto solo exponemos SSH al exterior.
ufw --force enable

# 3. Configuracion de SSHD
log "Asegurando SSHD..."
SSHD_CONFIG="/etc/ssh/sshd_config"
# Hacer backup si no existe
if [[ ! -f "${SSHD_CONFIG}.bak.orig" ]]; then
    cp "$SSHD_CONFIG" "${SSHD_CONFIG}.bak.orig"
fi

# Deshabilitar root login
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' "$SSHD_CONFIG"
# Forzar public key authentication (deshabilitar password)
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONFIG"
# Deshabilitar contrasenas vacias
sed -i 's/^#*PermitEmptyPasswords.*/PermitEmptyPasswords no/' "$SSHD_CONFIG"

systemctl restart sshd

# 4. Configuracion de Fail2Ban
log "Configurando Fail2Ban..."
cat << EOF > /etc/fail2ban/jail.local
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban --now
systemctl restart fail2ban

# 5. Usuario Restringido edge_ops
log "Verificando usuario edge_ops..."
if ! id "edge_ops" &>/dev/null; then
    useradd -m -s /bin/bash edge_ops
    usermod -aG sudo edge_ops
    usermod -aG docker edge_ops 2>/dev/null || warn "Grupo docker no existe aun, omitiendo."
    log "Usuario edge_ops creado. NOTA: Asegurese de anadir llaves publicas a /home/edge_ops/.ssh/authorized_keys."
else
    log "Usuario edge_ops ya existe."
fi

# 6. Actualizaciones automaticas (Security only)
log "Configurando unattended-upgrades..."
dpkg-reconfigure -f noninteractive unattended-upgrades

log "Hardening del nodo Edge completado exitosamente."
