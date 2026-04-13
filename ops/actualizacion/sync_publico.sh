#!/usr/bin/env bash
set -euo pipefail

python 07_scripts/tesis.py publish --build
if [[ -n "${PUBLIC_SYNC_TARGET:-}" ]]; then
  python 07_scripts/sync_public_repo.py --mode mirror --target-dir "$PUBLIC_SYNC_TARGET" --branch main
fi
