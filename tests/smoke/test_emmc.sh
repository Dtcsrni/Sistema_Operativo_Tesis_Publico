#!/usr/bin/env bash
set -euo pipefail
mount | grep '/mnt/emmc' >/dev/null
for dir in archive backups corpus datasets exports models snapshots; do
  test -d "/mnt/emmc/$dir"
done
echo "SMOKE_EMMC_OK"
