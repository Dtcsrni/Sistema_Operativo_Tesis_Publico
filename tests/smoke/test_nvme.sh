#!/usr/bin/env bash
set -euo pipefail
mount | grep ' / ' | grep -i nvme >/dev/null
echo "SMOKE_NVME_OK"
