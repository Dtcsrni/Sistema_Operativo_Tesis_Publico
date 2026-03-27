#!/usr/bin/env bash
set -euo pipefail

python 07_scripts/tesis.py doctor --check
if command -v openclaw >/dev/null 2>&1; then
  bash runtime/openclaw/wrappers/healthcheck.sh || true
fi
