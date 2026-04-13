#!/usr/bin/env bash
set -euo pipefail

: "${TESIS_EMMC_ROOT:=/mnt/emmc}"

target="${1:-}"
if [ -z "${target}" ]; then
  target="$(find "${TESIS_EMMC_ROOT}/backups" -maxdepth 3 -type f -name manifest.json 2>/dev/null | sort | tail -n 1)"
fi

if [ -z "${target}" ] || [ ! -e "${target}" ]; then
  echo "VERIFY_FAIL:no_backup_manifest"
  exit 1
fi

if [ -d "${target}" ]; then
  manifest_path="${target}/manifest.json"
else
  manifest_path="${target}"
fi

python3 - "$manifest_path" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
artifact = Path(manifest["artifact_path"])
checksum_path = Path(manifest["checksum_path"])
if not artifact.exists():
    raise SystemExit("VERIFY_FAIL:artifact_missing")
if not checksum_path.exists():
    raise SystemExit("VERIFY_FAIL:checksum_missing")
expected = checksum_path.read_text(encoding="utf-8").strip().split()[0]
sha = hashlib.sha256()
with artifact.open("rb") as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
        sha.update(chunk)
current = sha.hexdigest()
if current != expected:
    raise SystemExit("VERIFY_FAIL:checksum_mismatch")
print(f"VERIFY_OK:{manifest['domain']}:{artifact}")
PY
