#!/usr/bin/env bash
set -euo pipefail

test -f /etc/tesis-os/edge-iot.env
test -f /etc/systemd/system/edge-iot-worker.service
test -x /srv/tesis/repo/ops/edge/edge-iot-run.sh
test -x /srv/tesis/repo/ops/edge/edge-iot-preflight.sh
test -x /srv/tesis/repo/ops/edge/edge-iot-healthcheck.sh
systemctl cat edge-iot-worker.service | grep -q "User=edgeiot"
systemctl cat edge-iot-worker.service | grep -q "Restart=always"
echo "EDGE_SERVICE_OK"
