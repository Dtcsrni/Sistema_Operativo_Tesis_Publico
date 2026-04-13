#!/usr/bin/env bash
set -euo pipefail
ip link | grep -Ei 'wlan|wifi' >/dev/null
nmcli radio wifi >/dev/null || true
echo "SMOKE_WIFI_OK"
