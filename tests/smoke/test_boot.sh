#!/usr/bin/env bash
set -euo pipefail
systemctl is-system-running >/dev/null
uname -m | grep -E 'aarch64|arm64' >/dev/null || true
echo "SMOKE_BOOT_OK"
