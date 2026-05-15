#!/usr/bin/env bash
set -euo pipefail

test -f /etc/prometheus/prometheus.yml
test -f /etc/logrotate.d/tesis-observabilidad
test -f /etc/tesis-os/observabilidad.env
test -d /var/lib/node_exporter/textfile_collector
systemctl cat prometheus.service | grep -q '127.0.0.1:9090'
systemctl cat prometheus-node-exporter.service | grep -q '127.0.0.1:9100'
systemctl cat prometheus-node-exporter.service | grep -q 'collector.textfile.directory=/var/lib/node_exporter/textfile_collector'
systemctl cat tesis-observabilidad-collector.service | grep -q 'User=tesisadmin'
systemctl cat tesis-observabilidad-collector.timer | grep -q 'OnUnitActiveSec=2min'
echo 'OBSERVABILIDAD_STACK_OK'
