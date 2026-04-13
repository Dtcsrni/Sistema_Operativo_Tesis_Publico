#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/srv/tesis/repo}"
SYNC_REMOTE="${SYNC_REMOTE:-origin}"
SYNC_BRANCH="${SYNC_BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
EDGE_SERVICE_NAME="${EDGE_SERVICE_NAME:-edge-iot-worker.service}"
SYNC_PROFILE="${SYNC_PROFILE:-${1:-repo+postcheck}}"

usage() {
  cat <<'EOF'
Uso:
  sync_repo_desde_desktop.sh [repo-only|repo+postcheck|repo+restart-edge]

Perfiles:
  repo-only          Actualiza el clon operativo con fetch/checkout/pull --ff-only.
  repo+postcheck     Actualiza repo, corre audit --check y 90_postcheck.sh.
  repo+restart-edge  Hace repo+postcheck y reinicia edge-iot-worker.service.
EOF
}

sync_repo() {
  git -C "${REPO_ROOT}" fetch "${SYNC_REMOTE}" "${SYNC_BRANCH}" --prune
  git -C "${REPO_ROOT}" checkout "${SYNC_BRANCH}"
  git -C "${REPO_ROOT}" pull --ff-only "${SYNC_REMOTE}" "${SYNC_BRANCH}"
}

run_postcheck() {
  "${PYTHON_BIN}" "${REPO_ROOT}/07_scripts/tesis.py" audit --check
  bash "${REPO_ROOT}/bootstrap/orangepi/90_postcheck.sh"
}

case "${SYNC_PROFILE}" in
  repo-only)
    sync_repo
    ;;
  repo+postcheck)
    sync_repo
    run_postcheck
    ;;
  repo+restart-edge)
    sync_repo
    run_postcheck
    systemctl restart "${EDGE_SERVICE_NAME}"
    systemctl is-active --quiet "${EDGE_SERVICE_NAME}"
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    echo "Perfil de sincronizacion no soportado: ${SYNC_PROFILE}" >&2
    usage >&2
    exit 64
    ;;
esac

echo "EDGE_REPO_SYNC_OK:${SYNC_BRANCH}:${SYNC_PROFILE}"
