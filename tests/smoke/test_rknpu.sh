#!/usr/bin/env bash
set -euo pipefail
RKLLM_ROOT="${OPENCLAW_RKLLM_ROOT:-/opt/tesis-os/vendor/rknn-llm}"
has_rknpu_device() {
  if [ -e /dev/rknpu ] || [ -e /dev/rknn ]; then
    return 0
  fi
  for render in /sys/class/drm/renderD*/device/uevent; do
    [ -e "${render}" ] || continue
    grep -q '^DRIVER=RKNPU$' "${render}" && return 0
  done
  return 1
}

if [ ! -d "${RKLLM_ROOT}" ] && ! has_rknpu_device; then
  echo "SMOKE_RKNPU_SKIPPED:no_instalado"
  exit 0
fi
test -d "${RKLLM_ROOT}" || has_rknpu_device
echo "SMOKE_RKNPU_OK"
