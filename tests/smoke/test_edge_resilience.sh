#!/usr/bin/env bash
set -euo pipefail

test -f /etc/systemd/system/edge-iot-watchdog.service
test -f /etc/systemd/system/edge-iot-watchdog.timer
test -x /srv/tesis/repo/ops/edge/edge-iot-watchdog.sh
test -x /srv/tesis/repo/ops/edge/edge-iot-resilience.sh
test -f /etc/tesis-os/policies/edge_iot_resilience_policy.yaml
systemctl cat edge-iot-watchdog.service | grep -q "User=edgeiot"
systemctl cat edge-iot-watchdog.timer | grep -q "OnUnitActiveSec=2min"
echo "EDGE_RESILIENCE_OK"
