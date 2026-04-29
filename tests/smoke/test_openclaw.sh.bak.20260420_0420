#!/usr/bin/env bash
set -euo pipefail
if ! command -v openclaw >/dev/null 2>&1; then
  if [ ! -f "${OPENCLAW_REPO_ROOT:-/srv/tesis/repo}/runtime/openclaw/bin/openclaw_local.py" ]; then
    echo "SMOKE_OPENCLAW_SKIPPED:no_instalado"
    exit 0
  fi
fi
REPO_ROOT="${OPENCLAW_REPO_ROOT:-/srv/tesis/repo}"
PYTHON_BIN="${OPENCLAW_PYTHON_BIN:-python3}"
if command -v openclaw >/dev/null 2>&1; then
  openclaw doctor >/dev/null
  openclaw proveedor estado >/dev/null
  openclaw pasarela preflight >/dev/null
  openclaw pasarela estado >/dev/null
else
  "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" doctor >/dev/null
  "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" proveedor estado >/dev/null
  "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" pasarela preflight >/dev/null
  "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" pasarela estado >/dev/null
fi
echo "SMOKE_OPENCLAW_OK"
