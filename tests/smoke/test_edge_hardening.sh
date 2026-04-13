#!/usr/bin/env bash
set -euo pipefail

test -f /etc/tesis-os/policies/edge_iot_hardening_policy.yaml
getent passwd edgeiot >/dev/null
test -d /var/lib/edge-iot
test -d /var/log/edge-iot
ufw status | grep -q "Status: active"
ufw status | grep -q "22"
systemctl is-enabled fail2ban >/dev/null
test -f /etc/ssh/sshd_config.d/tesis-edge-hardening.conf
grep -q "^PermitRootLogin no" /etc/ssh/sshd_config.d/tesis-edge-hardening.conf
grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config.d/tesis-edge-hardening.conf
echo "EDGE_HARDENING_OK"
