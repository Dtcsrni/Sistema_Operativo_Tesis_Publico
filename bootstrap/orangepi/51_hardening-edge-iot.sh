#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATUS_DIR="/var/lib/edge-iot/bootstrap"
STATUS_FILE="${STATUS_DIR}/fase-hardening-edge.estado"
EDGE_POLICY="/etc/tesis-os/policies/edge_iot_hardening_policy.yaml"
EDGE_SSHD_DROPIN="/etc/ssh/sshd_config.d/tesis-edge-hardening.conf"
FAIL2BAN_JAIL="/etc/fail2ban/jail.d/tesis-edge.local"
TESIS_EDGE_SSH_USER="${TESIS_EDGE_SSH_USER:-tesisai}"
TESIS_EDGE_ADMIN_USERS="${TESIS_EDGE_ADMIN_USERS:-ErickV ${TESIS_EDGE_SSH_USER}}"

registrar_estado() {
  local estado="$1"
  local detalle="$2"
  sudo install -d -m 0755 "${STATUS_DIR}"
  printf 'estado=%s\ndetalle=%s\nfecha=%s\n' "${estado}" "${detalle}" "$(date --iso-8601=seconds)" | sudo tee "${STATUS_FILE}" >/dev/null
}

trap 'registrar_estado "fallo" "falló el hardening de edge_iot en la línea ${LINENO}"' ERR

sudo install -d -m 0755 /etc/tesis-os/policies
sudo install -m 0644 "${REPO_ROOT}/manifests/edge_iot_hardening_policy.yaml" "${EDGE_POLICY}"

sudo apt-get update
sudo apt-get install -y ufw fail2ban openssh-server

sudo install -d -o edgeiot -g edgeiot /var/lib/edge-iot /var/log/edge-iot /srv/tesis/workspace/edge /srv/tesis/intercambio/edge
sudo touch /var/log/edge-iot/edge-iot-worker.log /var/log/edge-iot/edge-iot-watchdog.log
sudo chown edgeiot:observabilidad /var/log/edge-iot/edge-iot-worker.log /var/log/edge-iot/edge-iot-watchdog.log
sudo chmod 0640 /var/log/edge-iot/edge-iot-worker.log /var/log/edge-iot/edge-iot-watchdog.log
sudo install -d -m 0700 /root/.ssh
sudo rm -f /root/.ssh/authorized_keys /root/.ssh/authorized_keys2

if id -u orangepi >/dev/null 2>&1; then
  sudo usermod -L -s /usr/sbin/nologin orangepi || true
  sudo chage -E 1 orangepi || true
fi

sudo install -d -m 0755 /etc/sudoers.d
for admin_user in ${TESIS_EDGE_ADMIN_USERS}; do
  if id -u "${admin_user}" >/dev/null 2>&1; then
    sudo usermod -aG adm,sudo,systemd-journal "${admin_user}" || true
    sudo tee "/etc/sudoers.d/90-${admin_user}-edge" >/dev/null <<EOF
${admin_user} ALL=(ALL) NOPASSWD: ALL
EOF
    sudo chmod 0440 "/etc/sudoers.d/90-${admin_user}-edge"
  fi
done

sudo systemctl disable --now bluetooth.service || true
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw --force enable

sudo tee "${EDGE_SSHD_DROPIN}" >/dev/null <<EOF
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
AllowUsers ${TESIS_EDGE_ADMIN_USERS}
EOF

sudo tee "${FAIL2BAN_JAIL}" >/dev/null <<'EOF'
[sshd]
enabled = true
backend = systemd
bantime = 1h
findtime = 10m
maxretry = 5
EOF

sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
sudo systemctl restart ssh || sudo systemctl restart sshd || true

registrar_estado "ok" "hardening edge_iot aplicado con ufw, fail2ban y ssh endurecido"
echo "BOOTSTRAP_HARDENING_EDGE_OK"
