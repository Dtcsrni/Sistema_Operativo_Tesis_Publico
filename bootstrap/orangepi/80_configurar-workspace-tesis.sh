#!/usr/bin/env bash
set -euo pipefail
sudo mkdir -p /opt/tesis-os /srv/tesis/repo /srv/tesis/workspace /srv/tesis/outputs /var/log/tesis-os /var/lib/tesis-os
sudo chown -R "$USER":"$USER" /srv/tesis /opt/tesis-os /var/log/tesis-os /var/lib/tesis-os
