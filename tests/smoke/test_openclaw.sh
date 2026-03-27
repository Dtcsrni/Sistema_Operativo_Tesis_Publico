#!/usr/bin/env bash
set -euo pipefail
if ! command -v openclaw >/dev/null 2>&1; then
  echo "SMOKE_OPENCLAW_SKIPPED:no_instalado"
  exit 0
fi
openclaw doctor >/dev/null
openclaw gateway status --json >/dev/null || openclaw daemon status --json >/dev/null
echo "SMOKE_OPENCLAW_OK"
