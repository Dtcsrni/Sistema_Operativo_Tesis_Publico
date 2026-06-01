#!/usr/bin/env bash
set -euo pipefail

if [ -r "/etc/tesis-os/openclaw.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . /etc/tesis-os/openclaw.env
  set +a
fi

if ! command -v openclaw >/dev/null 2>&1; then
  if [ ! -f "${OPENCLAW_REPO_ROOT:-/srv/tesis/repo}/runtime/openclaw/bin/openclaw_local.py" ]; then
    echo "SMOKE_OPENCLAW_SKIPPED:no_instalado"
    exit 0
  fi
fi
REPO_ROOT="${OPENCLAW_REPO_ROOT:-/srv/tesis/repo}"
PYTHON_BIN="${OPENCLAW_PYTHON_BIN:-python3}"
if [ -d "/var/lib/herramientas/openclaw" ]; then
  OPENCLAW_DATA_DIR="${OPENCLAW_DATA_DIR:-/var/lib/herramientas/openclaw}"
  OPENCLAW_CACHE_DIR="${OPENCLAW_CACHE_DIR:-/var/cache/herramientas/openclaw}"
  OPENCLAW_LOG_DIR="${OPENCLAW_LOG_DIR:-/var/log/openclaw}"
  OPENCLAW_DB_PATH="${OPENCLAW_DB_PATH:-/var/lib/herramientas/openclaw/openclaw.db}"
  export OPENCLAW_DATA_DIR OPENCLAW_CACHE_DIR OPENCLAW_LOG_DIR OPENCLAW_DB_PATH
fi
RUNNER=()
if command -v sudo >/dev/null 2>&1 && id openclaw >/dev/null 2>&1; then
  if sudo -n true >/dev/null 2>&1; then
    RUNNER=(
      sudo
      "--preserve-env=OPENCLAW_DATA_DIR,OPENCLAW_CACHE_DIR,OPENCLAW_LOG_DIR,OPENCLAW_DB_PATH,OPENCLAW_REPO_ROOT,OPENCLAW_PYTHON_BIN,OPENCLAW_RUNTIME,OPENCLAW_SERENA_ENABLED,OPENCLAW_SERENA_MODE,OPENCLAW_SERENA_TRANSPORT,OPENCLAW_SERENA_URL,OPENCLAW_SERENA_TIMEOUT_MS,OPENCLAW_NPU_AUTO_PROMOTE"
      -u
      openclaw
    )
  fi
fi

if [ ${#RUNNER[@]} -eq 0 ]; then
  # Fallback para entornos sin sudo no-interactivo: validar CLI en sandbox temporal.
  TMP_ROOT="${TMPDIR:-/tmp}/openclaw-smoke-${USER:-user}"
  mkdir -p "${TMP_ROOT}/data" "${TMP_ROOT}/cache" "${TMP_ROOT}/log"
  OPENCLAW_DATA_DIR="${TMP_ROOT}/data"
  OPENCLAW_CACHE_DIR="${TMP_ROOT}/cache"
  OPENCLAW_LOG_DIR="${TMP_ROOT}/log"
  OPENCLAW_DB_PATH="${TMP_ROOT}/data/openclaw.db"
  export OPENCLAW_DATA_DIR OPENCLAW_CACHE_DIR OPENCLAW_LOG_DIR OPENCLAW_DB_PATH
fi

if command -v openclaw >/dev/null 2>&1; then
  "${RUNNER[@]}" openclaw doctor >/dev/null
  "${RUNNER[@]}" openclaw proveedor estado >/dev/null
  "${RUNNER[@]}" openclaw pasarela preflight >/dev/null
  "${RUNNER[@]}" openclaw pasarela estado >/dev/null
else
  "${RUNNER[@]}" "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" doctor >/dev/null
  "${RUNNER[@]}" "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" proveedor estado >/dev/null
  "${RUNNER[@]}" "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" pasarela preflight >/dev/null
  "${RUNNER[@]}" "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" pasarela estado >/dev/null
fi
echo "SMOKE_OPENCLAW_OK"
