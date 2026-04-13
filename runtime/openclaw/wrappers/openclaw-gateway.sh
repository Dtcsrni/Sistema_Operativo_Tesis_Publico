#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${OPENCLAW_REPO_ROOT:-/srv/tesis/repo}"
PYTHON_BIN="${OPENCLAW_PYTHON_BIN:-python3}"
HOST="${OPENCLAW_HOST:-127.0.0.1}"
PORT="${OPENCLAW_PORT:-18789}"

if command -v openclaw >/dev/null 2>&1; then
  exec openclaw pasarela servir --host "${HOST}" --puerto "${PORT}"
fi

exec "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" pasarela servir --host "${HOST}" --puerto "${PORT}"
