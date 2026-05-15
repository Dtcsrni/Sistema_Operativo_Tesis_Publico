#!/usr/bin/env bash
set -euo pipefail
: "${NVME_DEVICE:?Define NVME_DEVICE, por ejemplo /dev/nvme0n1}"
sudo parted -s "$NVME_DEVICE" mklabel gpt
sudo parted -s "$NVME_DEVICE" mkpart primary ext4 1MiB 100%
sudo mkfs.ext4 -F "${NVME_DEVICE}p1"
