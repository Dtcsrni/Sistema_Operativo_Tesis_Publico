#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Uso: $0 <backup.tar.gz> <destino>"
  exit 1
fi

tar -xzf "$1" -C "$2"
echo "RESTORE_OK:$2"
