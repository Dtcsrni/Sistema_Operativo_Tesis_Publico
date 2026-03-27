#!/usr/bin/env bash
set -euo pipefail
sudo install -d /etc/tesis-os
sudo install -m 0644 config/systemd/*.service /etc/systemd/system/
sudo install -m 0644 config/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tesis-healthcheck.timer tesis-backup.timer tesis-sync.timer
