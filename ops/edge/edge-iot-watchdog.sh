#!/usr/bin/env bash
set -euo pipefail

: "${EDGE_IOT_HEALTHCHECK_CMD:?EDGE_IOT_HEALTHCHECK_CMD es obligatorio}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/edge-iot-resilience-lib.sh"

edge_iot_load_state
EDGE_IOT_LAST_HEALTHCHECK_AT="$(edge_iot_now)"

if edge_iot_quarantine_active; then
  edge_iot_set_state "quarantined"
  edge_iot_log_event "warn" "watchdog_quarantine_active" "${EDGE_IOT_QUARANTINE_REASON}"
  echo "EDGE_IOT_WATCHDOG_QUARANTINED"
  exit 0
fi

if [ "${EDGE_IOT_QUARANTINE_UNTIL}" -gt 0 ] && ! edge_iot_quarantine_active; then
  EDGE_IOT_QUARANTINE_UNTIL=0
  EDGE_IOT_QUARANTINE_REASON=""
  EDGE_IOT_FAILURE_COUNT=0
  edge_iot_log_event "info" "watchdog_quarantine_expired" "quarantine_expired"
fi

service_active=0
if systemctl is-active --quiet edge-iot-worker.service; then
  service_active=1
fi

health_ok=0
if bash -lc "${EDGE_IOT_HEALTHCHECK_CMD}" >/dev/null 2>&1; then
  health_ok=1
fi

if [ "${service_active}" -eq 1 ] && [ "${health_ok}" -eq 1 ]; then
  edge_iot_reset_failures
  EDGE_IOT_LAST_RECOVERY_AT="${EDGE_IOT_LAST_RECOVERY_AT:-$(edge_iot_iso_now)}"
  edge_iot_set_state "healthy"
  edge_iot_log_event "info" "watchdog_healthy" "service_and_healthcheck_ok"
  echo "EDGE_IOT_WATCHDOG_HEALTHY"
  exit 0
fi

if [ "${service_active}" -eq 0 ]; then
  edge_iot_record_failure "hard_failure_service_inactive"
  if [ "${EDGE_IOT_FAILURE_COUNT}" -gt "${EDGE_IOT_MAX_CONSECUTIVE_FAILURES}" ]; then
    edge_iot_enter_quarantine "hard_failure_limit_exceeded"
    systemctl stop edge-iot-worker.service || true
    echo "EDGE_IOT_WATCHDOG_QUARANTINED"
    exit 0
  fi
  EDGE_IOT_LAST_RECOVERY_AT="$(edge_iot_iso_now)"
  edge_iot_set_state "recovering"
  edge_iot_log_event "warn" "watchdog_restart_hard_failure" "count=${EDGE_IOT_FAILURE_COUNT}"
  sleep "${EDGE_IOT_BACKOFF_SEC}"
  systemctl restart edge-iot-worker.service
  echo "EDGE_IOT_WATCHDOG_RECOVERING_HARD"
  exit 0
fi

edge_iot_record_failure "soft_failure_healthcheck"
edge_iot_set_state "degraded_offline"
edge_iot_emit_spool_note "degraded_offline" "${EDGE_IOT_DEGRADED_REASON}"
edge_iot_log_event "warn" "watchdog_degraded_offline" "count=${EDGE_IOT_FAILURE_COUNT}"

if [ "${EDGE_IOT_FAILURE_COUNT}" -ge "${EDGE_IOT_SOFT_FAILURE_RESTART_THRESHOLD}" ]; then
  if [ "${EDGE_IOT_FAILURE_COUNT}" -gt "${EDGE_IOT_MAX_CONSECUTIVE_FAILURES}" ]; then
    edge_iot_enter_quarantine "soft_failure_limit_exceeded"
    systemctl stop edge-iot-worker.service || true
    echo "EDGE_IOT_WATCHDOG_QUARANTINED"
    exit 0
  fi
  EDGE_IOT_LAST_RECOVERY_AT="$(edge_iot_iso_now)"
  edge_iot_set_state "recovering"
  sleep "${EDGE_IOT_BACKOFF_SEC}"
  systemctl restart edge-iot-worker.service
  edge_iot_log_event "warn" "watchdog_restart_soft_failure" "count=${EDGE_IOT_FAILURE_COUNT}"
  echo "EDGE_IOT_WATCHDOG_RECOVERING_SOFT"
  exit 0
fi

edge_iot_save_state
echo "EDGE_IOT_WATCHDOG_DEGRADED"
