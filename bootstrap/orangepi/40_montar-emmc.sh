#!/usr/bin/env bash
set -euo pipefail
: "${EMMC_PARTITION:?Define EMMC_PARTITION}"
: "${EMMC_MOUNT:=/mnt/emmc}"
sudo mkdir -p "$EMMC_MOUNT"
sudo mount "$EMMC_PARTITION" "$EMMC_MOUNT"
for dir in archive backups corpus datasets exports models snapshots; do
  sudo mkdir -p "$EMMC_MOUNT/$dir"
done
