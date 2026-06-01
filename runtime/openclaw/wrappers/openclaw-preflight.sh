#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${OPENCLAW_REPO_ROOT:-/srv/tesis/repo}"
PYTHON_BIN="${OPENCLAW_PYTHON_BIN:-python3}"

exec "${PYTHON_BIN}" "${REPO_ROOT}/runtime/openclaw/bin/openclaw_local.py" pasarela preflight
