#!/usr/bin/env bash
set -euo pipefail
: "${NVME_PARTITION:?Define NVME_PARTITION, por ejemplo /dev/nvme0n1p1}"
: "${TARGET_MOUNT:=/mnt/tesis-root}"
sudo mkdir -p "$TARGET_MOUNT"
sudo mount "$NVME_PARTITION" "$TARGET_MOUNT"
echo "Copia aqui el rootfs validado antes de cambiar bootargs o fstab."
