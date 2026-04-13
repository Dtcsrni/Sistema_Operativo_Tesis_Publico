#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

sudo apt-get update
sudo apt-get install -y prometheus prometheus-node-exporter logrotate

sudo install -d /etc/prometheus
sudo install -d /etc/logrotate.d
sudo install -d /etc/systemd/system/prometheus.service.d
sudo install -d /etc/systemd/system/prometheus-node-exporter.service.d
sudo install -d /var/lib/node_exporter/textfile_collector
sudo install -d /var/lib/tesis-observabilidad

sudo install -m 0644 "${REPO_ROOT}/config/prometheus/prometheus.yml" /etc/prometheus/prometheus.yml
sudo install -m 0644 "${REPO_ROOT}/config/logrotate/tesis-observabilidad" /etc/logrotate.d/tesis-observabilidad
sudo install -m 0644 "${REPO_ROOT}/config/systemd-overrides/prometheus.service.d/override.conf" /etc/systemd/system/prometheus.service.d/override.conf
sudo install -m 0644 "${REPO_ROOT}/config/systemd-overrides/prometheus-node-exporter.service.d/override.conf" /etc/systemd/system/prometheus-node-exporter.service.d/override.conf
if [ ! -f /etc/tesis-os/observabilidad.env ]; then
  sudo install -m 0640 "${REPO_ROOT}/config/env/observabilidad.env.example" /etc/tesis-os/observabilidad.env
fi

sudo chown -R tesisadmin:observabilidad /var/lib/node_exporter/textfile_collector /var/lib/tesis-observabilidad
sudo chmod 0755 /var/lib/node_exporter/textfile_collector
sudo chmod 0750 /var/lib/tesis-observabilidad

sudo systemctl daemon-reload
sudo systemctl enable --now prometheus.service prometheus-node-exporter.service tesis-observabilidad-collector.timer
