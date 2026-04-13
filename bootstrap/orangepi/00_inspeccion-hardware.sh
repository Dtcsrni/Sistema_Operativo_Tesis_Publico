#!/usr/bin/env bash
set -euo pipefail
uname -a
lscpu
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT
ip link || true
rfkill list || true
