#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/edge-iot-resilience-lib.sh"
edge_iot_load_state

command="${1:-status}"

case "${command}" in
  status)
    edge_iot_save_state
    cat "${EDGE_IOT_RESILIENCE_FILE}"
    ;;
  clear-quarantine)
    EDGE_IOT_QUARANTINE_UNTIL=0
    EDGE_IOT_QUARANTINE_REASON=""
    EDGE_IOT_FAILURE_COUNT=0
    EDGE_IOT_RESILIENCE_STATE="healthy"
    edge_iot_save_state
    edge_iot_log_event "info" "manual_clear_quarantine" "manual_clear"
    echo "EDGE_IOT_QUARANTINE_CLEARED"
    ;;
  simulate-soft-failure)
    touch "${EDGE_IOT_RUNTIME_DIR}/force_soft_failure"
    edge_iot_log_event "warn" "simulate_soft_failure" "marker_created"
    echo "EDGE_IOT_SOFT_FAILURE_SIMULATED"
    ;;
  clear-soft-failure)
    rm -f "${EDGE_IOT_RUNTIME_DIR}/force_soft_failure"
    echo "EDGE_IOT_SOFT_FAILURE_CLEARED"
    ;;
  simulate-hard-failure)
    systemctl kill --signal=SIGTERM edge-iot-worker.service
    edge_iot_log_event "warn" "simulate_hard_failure" "systemctl_kill"
    echo "EDGE_IOT_HARD_FAILURE_SIMULATED"
    ;;
  *)
    echo "Uso: $0 {status|clear-quarantine|simulate-soft-failure|clear-soft-failure|simulate-hard-failure}" >&2
    exit 1
    ;;
esac
