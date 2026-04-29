#!/usr/bin/env bash
set -euo pipefail

TESIS_EDGE_HOSTNAME="${TESIS_EDGE_HOSTNAME:-tesis-edge}"
TESIS_EDGE_USER="${TESIS_EDGE_USER:-tesisai}"
TESIS_EDGE_ADMIN_USERS="${TESIS_EDGE_ADMIN_USERS:-ErickV ${TESIS_EDGE_USER}}"
TESIS_EDGE_ADMIN_GROUPS="${TESIS_EDGE_ADMIN_GROUPS:-adm,sudo,systemd-journal}"

if command -v hostnamectl >/dev/null 2>&1; then
  sudo hostnamectl set-hostname "${TESIS_EDGE_HOSTNAME}"
fi

sudo sed -i '/^127\.0\.1\.1[[:space:]]/d' /etc/hosts
printf '127.0.1.1 %s\n' "${TESIS_EDGE_HOSTNAME}" | sudo tee -a /etc/hosts >/dev/null

if ! id -u "${TESIS_EDGE_USER}" >/dev/null 2>&1; then
  sudo adduser --disabled-password --gecos "" "${TESIS_EDGE_USER}"
fi

IFS=',' read -r -a TESIS_EDGE_ADMIN_GROUPS_LIST <<< "${TESIS_EDGE_ADMIN_GROUPS}"
IFS=' ' read -r -a TESIS_EDGE_ADMIN_USERS_LIST <<< "${TESIS_EDGE_ADMIN_USERS}"
if [ "${#TESIS_EDGE_ADMIN_GROUPS_LIST[@]}" -gt 0 ]; then
  TESIS_EDGE_ADMIN_GROUPS_CSV="$(printf '%s,' "${TESIS_EDGE_ADMIN_GROUPS_LIST[@]}" | sed 's/,$//')"
  for TESIS_EDGE_ADMIN_ACCOUNT in "${TESIS_EDGE_ADMIN_USERS_LIST[@]}"; do
    if id -u "${TESIS_EDGE_ADMIN_ACCOUNT}" >/dev/null 2>&1; then
      sudo usermod -aG "${TESIS_EDGE_ADMIN_GROUPS_CSV}" "${TESIS_EDGE_ADMIN_ACCOUNT}"
    fi
  done
fi

if id -u orangepi >/dev/null 2>&1; then
  sudo usermod -s /usr/sbin/nologin orangepi || true
  sudo passwd -l orangepi || true
fi

sudo apt-get update
sudo apt-get install -y git curl ca-certificates python3 python3-venv python3-pip jq rsync
