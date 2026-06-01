#!/usr/bin/env bash
set -euo pipefail
sudo systemctl disable --now bluetooth.service || true
sudo apt-get install -y ufw fail2ban
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw --force enable
