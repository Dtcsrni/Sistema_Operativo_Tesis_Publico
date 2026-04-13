#!/usr/bin/env bash
set -euo pipefail

: "${EDGE_IOT_WORKDIR:?EDGE_IOT_WORKDIR es obligatorio}"
: "${EDGE_IOT_LOG_DIR:?EDGE_IOT_LOG_DIR es obligatorio}"
: "${EDGE_IOT_STATE_DIR:?EDGE_IOT_STATE_DIR es obligatorio}"
: "${EDGE_IOT_RUNTIME_DIR:?EDGE_IOT_RUNTIME_DIR es obligatorio}"
: "${EDGE_IOT_EXTERNAL_CHECK_CMD:=true}"
: "${EDGE_IOT_HEARTBEAT_STALE_SEC:=180}"

test -d "${EDGE_IOT_WORKDIR}"
test -d "${EDGE_IOT_LOG_DIR}"
test -d "${EDGE_IOT_STATE_DIR}"
test -d "${EDGE_IOT_RUNTIME_DIR}"
test -f "${EDGE_IOT_STATE_DIR}/last_start.txt" || true

if ! systemctl is-active --quiet edge-iot-worker.service; then
  echo "EDGE_IOT_HEALTH_FAIL service_inactive"
  exit 1
fi

if [ -f "${EDGE_IOT_RUNTIME_DIR}/force_soft_failure" ]; then
  echo "EDGE_IOT_HEALTH_FAIL force_soft_failure"
  exit 1
fi

if [ -f "${EDGE_IOT_RUNTIME_DIR}/heartbeat.timestamp" ]; then
  now="$(date +%s)"
  heartbeat="$(cat "${EDGE_IOT_RUNTIME_DIR}/heartbeat.timestamp" 2>/dev/null || echo 0)"
  if [ $((now - heartbeat)) -gt "${EDGE_IOT_HEARTBEAT_STALE_SEC}" ]; then
    echo "EDGE_IOT_HEALTH_FAIL stale_heartbeat"
    exit 1
  fi
fi

if ! bash -lc "${EDGE_IOT_EXTERNAL_CHECK_CMD}" >/dev/null 2>&1; then
  echo "EDGE_IOT_HEALTH_FAIL external_dependency"
  exit 1
fi

echo "EDGE_IOT_HEALTH_OK healthy"
exit 0
