#!/usr/bin/env bash
set -euo pipefail
RKLLM_ROOT="${OPENCLAW_RKLLM_ROOT:-/opt/tesis-os/vendor/rknn-llm}"
if [ ! -d "${RKLLM_ROOT}" ] && [ ! -e /dev/rknpu ] && [ ! -e /dev/rknn ]; then
  echo "SMOKE_RKNPU_SKIPPED:no_instalado"
  exit 0
fi
test -d "${RKLLM_ROOT}" || test -e /dev/rknpu || test -e /dev/rknn
echo "SMOKE_RKNPU_OK"
