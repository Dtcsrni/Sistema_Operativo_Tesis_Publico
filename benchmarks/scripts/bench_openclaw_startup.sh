#!/usr/bin/env bash
set -euo pipefail
if ! command -v openclaw >/dev/null 2>&1; then
  echo "BENCH_OPENCLAW_SKIPPED"
  exit 0
fi
time openclaw gateway status --json || time openclaw daemon status --json
