#!/usr/bin/env bash
set -euo pipefail

: "${TESIS_EMMC_ROOT:=/mnt/emmc}"
: "${TESIS_BACKUP_SIGN_KEY:=}"

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

if [ -z "${TESIS_BACKUP_SIGN_KEY}" ]; then
  echo "VERIFY_FAIL:missing_TESIS_BACKUP_SIGN_KEY"
  exit 1
fi

python3 - "$manifest_path" "$TESIS_BACKUP_SIGN_KEY" <<'PY'
import hashlib
import hmac
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
sign_key = sys.argv[2].encode("utf-8")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
artifact = Path(manifest["artifact_path"])
checksum_path = Path(manifest["checksum_path"])
checksum_signature_path = Path(manifest.get("checksum_signature_path", ""))
manifest_signature_path = manifest_path.parent / "manifest.json.sig"
if not artifact.exists():
    raise SystemExit("VERIFY_FAIL:artifact_missing")
if not checksum_path.exists():
    raise SystemExit("VERIFY_FAIL:checksum_missing")
if not checksum_signature_path.exists():
    raise SystemExit("VERIFY_FAIL:checksum_signature_missing")
if not manifest_signature_path.exists():
    raise SystemExit("VERIFY_FAIL:manifest_signature_missing")
expected = checksum_path.read_text(encoding="utf-8").strip().split()[0]
sha = hashlib.sha256()
with artifact.open("rb") as fh:
    for chunk in iter(lambda: fh.read(1024 * 1024), b""):
        sha.update(chunk)
current = sha.hexdigest()
if current != expected:
    raise SystemExit("VERIFY_FAIL:checksum_mismatch")
expected_checksum_sig = checksum_signature_path.read_text(encoding="utf-8").strip()
current_checksum_sig = hmac.new(sign_key, str(artifact).encode("utf-8"), hashlib.sha256).hexdigest()
if expected_checksum_sig != current_checksum_sig:
    raise SystemExit("VERIFY_FAIL:checksum_signature_mismatch")
expected_manifest_sig = manifest_signature_path.read_text(encoding="utf-8").strip()
current_manifest_sig = hmac.new(sign_key, manifest_path.read_bytes(), hashlib.sha256).hexdigest()
if expected_manifest_sig != current_manifest_sig:
    raise SystemExit("VERIFY_FAIL:manifest_signature_mismatch")
print(f"VERIFY_OK:{manifest['domain']}:{artifact}")
print(f"VERIFY_SIGNATURE_OK:{manifest_path}")
PY
