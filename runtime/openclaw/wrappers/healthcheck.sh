#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${OPENCLAW_REPO_ROOT:-/srv/tesis/repo}"
PYTHON_BIN="${OPENCLAW_PYTHON_BIN:-python3}"

if command -v openclaw >/dev/null 2>&1; then
  openclaw doctor || true
  openclaw proveedor estado || true
  openclaw pasarela preflight
  openclaw pasarela estado
  exit 0
fi

if [ -f "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" ]; then
  "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" doctor || true
  "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" proveedor estado || true
  "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" pasarela preflight
  "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" pasarela estado
  exit 0
fi

echo "OPENCLAW_HEALTHCHECK: no_instalado"
exit 1
