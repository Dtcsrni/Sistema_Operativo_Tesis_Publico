#!/usr/bin/env bash
set -euo pipefail

: "${EDGE_IOT_STATE_DIR:?EDGE_IOT_STATE_DIR es obligatorio}"
EDGE_IOT_RUNTIME_DIR="${EDGE_IOT_RUNTIME_DIR:-${EDGE_IOT_STATE_DIR}/runtime}"
EDGE_IOT_RESILIENCE_FILE="${EDGE_IOT_RUNTIME_DIR}/resilience.env"
EDGE_IOT_REQUIRES_NETWORK="${EDGE_IOT_REQUIRES_NETWORK:-0}"
EDGE_IOT_FAILURE_WINDOW_SEC="${EDGE_IOT_FAILURE_WINDOW_SEC:-900}"
EDGE_IOT_MAX_CONSECUTIVE_FAILURES="${EDGE_IOT_MAX_CONSECUTIVE_FAILURES:-3}"
EDGE_IOT_SOFT_FAILURE_RESTART_THRESHOLD="${EDGE_IOT_SOFT_FAILURE_RESTART_THRESHOLD:-2}"
EDGE_IOT_BACKOFF_SEC="${EDGE_IOT_BACKOFF_SEC:-30}"
EDGE_IOT_QUARANTINE_SEC="${EDGE_IOT_QUARANTINE_SEC:-1800}"
EDGE_IOT_HEARTBEAT_STALE_SEC="${EDGE_IOT_HEARTBEAT_STALE_SEC:-180}"
EDGE_IOT_SPOOL_DIR="${EDGE_IOT_SPOOL_DIR:-/srv/tesis/intercambio/edge/spool}"

edge_iot_now() {
  date +%s
}

edge_iot_iso_now() {
  date --iso-8601=seconds
}

edge_iot_ensure_runtime() {
  install -d -m 0750 "${EDGE_IOT_STATE_DIR}" "${EDGE_IOT_RUNTIME_DIR}" "${EDGE_IOT_SPOOL_DIR}"
}

edge_iot_load_state() {
  edge_iot_ensure_runtime
  EDGE_IOT_RESILIENCE_STATE="healthy"
  EDGE_IOT_FAILURE_COUNT=0
  EDGE_IOT_LAST_RECOVERY_AT=""
  EDGE_IOT_DEGRADED_REASON=""
  EDGE_IOT_QUARANTINE_REASON=""
  EDGE_IOT_QUARANTINE_UNTIL=0
  EDGE_IOT_LAST_FAILURE_AT=0
  EDGE_IOT_LAST_HEALTHCHECK_AT=0
  EDGE_IOT_LAST_HEARTBEAT_AT=0
  if [ -f "${EDGE_IOT_RESILIENCE_FILE}" ]; then
    # shellcheck disable=SC1090
    source "${EDGE_IOT_RESILIENCE_FILE}"
  fi
}

edge_iot_save_state() {
  edge_iot_ensure_runtime
  cat > "${EDGE_IOT_RESILIENCE_FILE}" <<EOF
EDGE_IOT_RESILIENCE_STATE="${EDGE_IOT_RESILIENCE_STATE}"
EDGE_IOT_FAILURE_COUNT=${EDGE_IOT_FAILURE_COUNT}
EDGE_IOT_LAST_RECOVERY_AT="${EDGE_IOT_LAST_RECOVERY_AT}"
EDGE_IOT_DEGRADED_REASON="${EDGE_IOT_DEGRADED_REASON}"
EDGE_IOT_QUARANTINE_REASON="${EDGE_IOT_QUARANTINE_REASON}"
EDGE_IOT_QUARANTINE_UNTIL=${EDGE_IOT_QUARANTINE_UNTIL}
EDGE_IOT_LAST_FAILURE_AT=${EDGE_IOT_LAST_FAILURE_AT}
EDGE_IOT_LAST_HEALTHCHECK_AT=${EDGE_IOT_LAST_HEALTHCHECK_AT}
EDGE_IOT_LAST_HEARTBEAT_AT=${EDGE_IOT_LAST_HEARTBEAT_AT}
EOF
}

edge_iot_log_event() {
  local level="$1"
  local event="$2"
  local detail="${3:-}"
  printf '%s level=%s event=%s detail=%s\n' "$(edge_iot_iso_now)" "${level}" "${event}" "${detail}" >> "${EDGE_IOT_LOG_DIR}/edge-iot-resilience.log"
}

edge_iot_record_failure() {
  local reason="$1"
  local now
  now="$(edge_iot_now)"
  if [ $((now - EDGE_IOT_LAST_FAILURE_AT)) -gt "${EDGE_IOT_FAILURE_WINDOW_SEC}" ]; then
    EDGE_IOT_FAILURE_COUNT=0
  fi
  EDGE_IOT_FAILURE_COUNT=$((EDGE_IOT_FAILURE_COUNT + 1))
  EDGE_IOT_LAST_FAILURE_AT="${now}"
  EDGE_IOT_DEGRADED_REASON="${reason}"
}

edge_iot_reset_failures() {
  EDGE_IOT_FAILURE_COUNT=0
  EDGE_IOT_DEGRADED_REASON=""
  EDGE_IOT_QUARANTINE_REASON=""
}

edge_iot_set_state() {
  local state="$1"
  EDGE_IOT_RESILIENCE_STATE="${state}"
  edge_iot_save_state
}

edge_iot_enter_quarantine() {
  local reason="$1"
  local now
  now="$(edge_iot_now)"
  EDGE_IOT_RESILIENCE_STATE="quarantined"
  EDGE_IOT_QUARANTINE_REASON="${reason}"
  EDGE_IOT_QUARANTINE_UNTIL=$((now + EDGE_IOT_QUARANTINE_SEC))
  EDGE_IOT_LAST_RECOVERY_AT="$(edge_iot_iso_now)"
  edge_iot_save_state
  edge_iot_log_event "error" "quarantined" "${reason}"
}

edge_iot_quarantine_active() {
  local now
  now="$(edge_iot_now)"
  [ "${EDGE_IOT_QUARANTINE_UNTIL}" -gt "${now}" ]
}

edge_iot_emit_spool_note() {
  local label="$1"
  local detail="$2"
  local path="${EDGE_IOT_SPOOL_DIR}/$(date +%Y%m%d_%H%M%S)_${label}.txt"
  printf 'timestamp=%s\nlabel=%s\ndetail=%s\n' "$(edge_iot_iso_now)" "${label}" "${detail}" > "${path}"
}
