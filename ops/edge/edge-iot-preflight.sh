#!/usr/bin/env bash
set -euo pipefail

: "${EDGE_IOT_COMMAND:?EDGE_IOT_COMMAND es obligatorio}"
: "${EDGE_IOT_WORKDIR:?EDGE_IOT_WORKDIR es obligatorio}"
: "${EDGE_IOT_LOG_DIR:?EDGE_IOT_LOG_DIR es obligatorio}"
: "${EDGE_IOT_STATE_DIR:?EDGE_IOT_STATE_DIR es obligatorio}"
: "${EDGE_IOT_RUNTIME_DIR:?EDGE_IOT_RUNTIME_DIR es obligatorio}"
: "${EDGE_IOT_SPOOL_DIR:?EDGE_IOT_SPOOL_DIR es obligatorio}"
: "${EDGE_IOT_HEALTHCHECK_CMD:?EDGE_IOT_HEALTHCHECK_CMD es obligatorio}"

test -d "${EDGE_IOT_WORKDIR}"
test -d "${EDGE_IOT_LOG_DIR}"
test -d "${EDGE_IOT_STATE_DIR}"
test -d "${EDGE_IOT_RUNTIME_DIR}" || install -d -m 0750 "${EDGE_IOT_RUNTIME_DIR}"
test -d "${EDGE_IOT_SPOOL_DIR}" || install -d -m 0750 "${EDGE_IOT_SPOOL_DIR}"
test -x "${EDGE_IOT_HEALTHCHECK_CMD}"
test -x "/srv/tesis/repo/ops/edge/edge-iot-watchdog.sh"
test -x "/srv/tesis/repo/ops/edge/edge-iot-resilience.sh"

echo "EDGE_IOT_PREFLIGHT_OK"
