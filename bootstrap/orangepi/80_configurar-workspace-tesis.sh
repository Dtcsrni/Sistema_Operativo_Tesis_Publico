#!/usr/bin/env bash
set -euo pipefail

if ! getent group tesis >/dev/null; then
  sudo groupadd --system tesis
fi
if ! id -u tesis >/dev/null 2>&1; then
  sudo useradd --system --gid tesis --home-dir /srv/tesis --create-home --shell /usr/sbin/nologin tesis
fi
if ! getent group openclaw >/dev/null; then
  sudo groupadd --system openclaw
fi
if ! id -u openclaw >/dev/null 2>&1; then
  sudo useradd --system --gid openclaw --groups tesis --home-dir /var/lib/herramientas/openclaw --no-create-home --shell /usr/sbin/nologin openclaw
fi
if ! getent group edgeiot >/dev/null; then
  sudo groupadd --system edgeiot
fi
if ! id -u edgeiot >/dev/null 2>&1; then
  sudo useradd --system --gid edgeiot --home-dir /var/lib/edge-iot --no-create-home --shell /usr/sbin/nologin edgeiot
fi
if ! getent group tesisadmin >/dev/null; then
  sudo groupadd --system tesisadmin
fi
if ! id -u tesisadmin >/dev/null 2>&1; then
  sudo useradd --system --gid tesisadmin --groups tesis --home-dir /var/lib/tesis-admin --no-create-home --shell /usr/sbin/nologin tesisadmin
fi
if ! getent group personal >/dev/null; then
  sudo groupadd --system personal
fi
if ! getent group observabilidad >/dev/null; then
  sudo groupadd --system observabilidad
fi
sudo usermod -a -G observabilidad tesisadmin

sudo mkdir -p \
  /opt/tesis-os \
  /opt/tesis-os/venvs \
  /srv/tesis/repo \
  /srv/tesis/workspace \
  /srv/tesis/workspace/openclaw \
  /srv/tesis/workspace/edge \
  /srv/tesis/outputs \
  /srv/tesis/intercambio/openclaw/inbox \
  /srv/tesis/intercambio/openclaw/outbox \
  /srv/tesis/intercambio/openclaw/spool \
  /srv/tesis/intercambio/edge/inbox \
  /srv/tesis/intercambio/edge/outbox \
  /srv/tesis/intercambio/edge/spool \
  /var/log/tesis-os \
  /var/lib/tesis-os \
  /var/lib/edge-iot \
  /var/lib/edge-iot/runtime \
  /var/log/edge-iot \
  /var/lib/tesis-admin \
  /var/log/tesis-admin \
  /var/lib/herramientas/openclaw \
  /var/cache/herramientas/openclaw \
  /var/log/openclaw \
  /var/lib/prometheus \
  /var/lib/node_exporter/textfile_collector \
  /var/lib/tesis-observabilidad
sudo chown -R tesis:tesis /srv/tesis/repo /srv/tesis/workspace /srv/tesis/outputs /opt/tesis-os /var/log/tesis-os /var/lib/tesis-os
sudo chown -R openclaw:observabilidad /var/lib/herramientas/openclaw /var/cache/herramientas/openclaw /var/log/openclaw /srv/tesis/workspace/openclaw /srv/tesis/intercambio/openclaw
sudo chown -R edgeiot:observabilidad /var/lib/edge-iot /var/log/edge-iot /srv/tesis/workspace/edge /srv/tesis/intercambio/edge
sudo chown -R tesisadmin:observabilidad /var/lib/tesis-admin /var/log/tesis-admin /var/lib/node_exporter/textfile_collector /var/lib/tesis-observabilidad
sudo touch \
  /var/log/tesis-os/tesis-healthcheck.log \
  /var/log/tesis-os/tesis-sync.log \
  /var/log/tesis-admin/tesis-backup.log \
  /var/log/tesis-admin/prometheus.log \
  /var/log/tesis-admin/node-exporter.log \
  /var/log/tesis-admin/observability-collector.log \
  /var/log/edge-iot/edge-iot-worker.log \
  /var/log/edge-iot/edge-iot-watchdog.log \
  /var/log/openclaw/openclaw-gateway.log
sudo chown tesis:tesis /var/log/tesis-os/tesis-healthcheck.log /var/log/tesis-os/tesis-sync.log
sudo chown tesisadmin:observabilidad /var/log/tesis-admin/tesis-backup.log /var/log/tesis-admin/prometheus.log /var/log/tesis-admin/node-exporter.log /var/log/tesis-admin/observability-collector.log
sudo chown edgeiot:observabilidad /var/log/edge-iot/edge-iot-worker.log /var/log/edge-iot/edge-iot-watchdog.log
sudo chown openclaw:observabilidad /var/log/openclaw/openclaw-gateway.log
sudo chmod 0640 /var/log/tesis-os/tesis-healthcheck.log /var/log/tesis-os/tesis-sync.log
sudo chmod 0640 /var/log/tesis-admin/tesis-backup.log /var/log/tesis-admin/prometheus.log /var/log/tesis-admin/node-exporter.log /var/log/tesis-admin/observability-collector.log
sudo chmod 0640 /var/log/edge-iot/edge-iot-worker.log /var/log/edge-iot/edge-iot-watchdog.log /var/log/openclaw/openclaw-gateway.log
sudo chmod 0750 /var/lib/herramientas/openclaw /var/cache/herramientas/openclaw /var/log/openclaw /srv/tesis/intercambio/openclaw /srv/tesis/intercambio/edge /srv/tesis/workspace/edge /var/log/edge-iot /var/log/tesis-admin
sudo chmod 0755 /var/lib/node_exporter/textfile_collector
sudo mkdir -p /mnt/emmc/backups/reports /mnt/emmc/snapshots/sistema_tesis /mnt/emmc/snapshots/openclaw /mnt/emmc/snapshots/edge_iot
sudo chown -R tesisadmin:tesisadmin /mnt/emmc/backups /mnt/emmc/snapshots
sudo chmod 0750 /srv/tesis/workspace/openclaw /srv/tesis/workspace/edge /srv/tesis/intercambio/openclaw /srv/tesis/intercambio/edge
sudo chmod 0750 /srv/tesis/intercambio/openclaw/inbox /srv/tesis/intercambio/openclaw/outbox /srv/tesis/intercambio/openclaw/spool
sudo chmod 0750 /srv/tesis/intercambio/edge/inbox /srv/tesis/intercambio/edge/outbox /srv/tesis/intercambio/edge/spool
