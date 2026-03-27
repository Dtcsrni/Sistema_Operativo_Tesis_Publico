#!/usr/bin/env bash
set -euo pipefail

if ! command -v openclaw >/dev/null 2>&1; then
  echo "OPENCLAW_HEALTHCHECK: no_instalado"
  exit 1
fi

openclaw doctor || true
openclaw gateway status --json || openclaw daemon status --json
