#!/usr/bin/env bash
set -euo pipefail

: "${EDGE_IOT_COMMAND:?EDGE_IOT_COMMAND es obligatorio}"
: "${EDGE_IOT_WORKDIR:?EDGE_IOT_WORKDIR es obligatorio}"
: "${EDGE_IOT_LOG_DIR:?EDGE_IOT_LOG_DIR es obligatorio}"
: "${EDGE_IOT_STATE_DIR:?EDGE_IOT_STATE_DIR es obligatorio}"
: "${EDGE_IOT_RUNTIME_DIR:?EDGE_IOT_RUNTIME_DIR es obligatorio}"
: "${EDGE_IOT_SPOOL_DIR:?EDGE_IOT_SPOOL_DIR es obligatorio}"
: "${EDGE_IOT_HEARTBEAT_INTERVAL_SEC:=30}"

install -d -m 0750 "${EDGE_IOT_LOG_DIR}" "${EDGE_IOT_STATE_DIR}" "${EDGE_IOT_RUNTIME_DIR}" "${EDGE_IOT_SPOOL_DIR}"
printf '%s\n' "$(date --iso-8601=seconds)" > "${EDGE_IOT_STATE_DIR}/last_start.txt"
date +%s > "${EDGE_IOT_RUNTIME_DIR}/heartbeat.timestamp"

cd "${EDGE_IOT_WORKDIR}"
(
  while true; do
    date +%s > "${EDGE_IOT_RUNTIME_DIR}/heartbeat.timestamp"
    sleep "${EDGE_IOT_HEARTBEAT_INTERVAL_SEC}"
  done
) &
heartbeat_pid=$!
trap 'kill "${heartbeat_pid}" >/dev/null 2>&1 || true' EXIT INT TERM

/usr/bin/env bash -lc "${EDGE_IOT_COMMAND}" >> "${EDGE_IOT_LOG_DIR}/edge-iot-worker.log" 2>&1 &
worker_pid=$!
wait "${worker_pid}"
