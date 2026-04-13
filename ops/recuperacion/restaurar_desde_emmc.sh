#!/usr/bin/env bash
set -euo pipefail

: "${TESIS_BACKUP_POLICY:=/etc/tesis-os/policies/domain_backup_policy.yaml}"
: "${TESIS_RESTORE_SANDBOX_ROOT:=/tmp/tesis-restore}"

usage() {
  echo "Uso: $0 --domain <dominio> --manifest <manifest.json> [--mode sandbox|in_place] [--target <ruta>] [--allow-in-place]"
  exit 1
}

domain=""
manifest_path=""
mode="sandbox"
target=""
allow_in_place=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) domain="$2"; shift 2 ;;
    --manifest) manifest_path="$2"; shift 2 ;;
    --mode) mode="$2"; shift 2 ;;
    --target) target="$2"; shift 2 ;;
    --allow-in-place) allow_in_place=1; shift ;;
    *) usage ;;
  esac
done

[ -n "${domain}" ] || usage
[ -n "${manifest_path}" ] || usage
[ -f "${manifest_path}" ] || { echo "RESTORE_FAIL:manifest_missing"; exit 1; }

bash /srv/tesis/repo/ops/respaldo/verificar_respaldos.sh "${manifest_path}" >/dev/null

artifact_path="$(python3 - "$manifest_path" "$domain" "$TESIS_BACKUP_POLICY" <<'PY'
import json, sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if manifest["domain"] != sys.argv[2]:
    raise SystemExit("RESTORE_FAIL:domain_manifest_mismatch")
policy = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
if sys.argv[2] not in policy["domains"]:
    raise SystemExit("RESTORE_FAIL:domain_not_allowed")
print(manifest["artifact_path"])
PY
)"

report_root="$(dirname "${manifest_path}")"

if [ "${mode}" = "sandbox" ]; then
  if [ -z "${target}" ]; then
    timestamp="$(date +%Y%m%d_%H%M%S)"
    target="${TESIS_RESTORE_SANDBOX_ROOT}/${domain}/${timestamp}"
  fi
  mkdir -p "${target}"
elif [ "${mode}" = "in_place" ]; then
  if [ "${allow_in_place}" -ne 1 ]; then
    echo "RESTORE_FAIL:in_place_requires_allow_flag"
    exit 1
  fi
  [ -n "${target}" ] || usage
  if [ "${target}" != "/" ]; then
    echo "RESTORE_FAIL:in_place_requires_root_target"
    exit 1
  fi
else
  echo "RESTORE_FAIL:invalid_mode"
  exit 1
fi

tar -xzf "${artifact_path}" -C "${target}"

validation_report="$(python3 - "$manifest_path" "$target" "$mode" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
target = Path(sys.argv[2])
mode = sys.argv[3]
missing = []
for item in manifest["critical_paths"]:
    expected = target / item if mode == "sandbox" else Path("/") / item
    if not expected.exists():
        missing.append(str(expected))
payload = {
    "domain": manifest["domain"],
    "mode": mode,
    "target": str(target),
    "artifact_path": manifest["artifact_path"],
    "missing_critical_paths": missing,
    "status": "ok" if not missing else "fail",
}
print(json.dumps(payload, ensure_ascii=False))
PY
)"

report_path="${report_root}/restore_${domain}_${mode}.json"
printf '%s\n' "${validation_report}" > "${report_path}"
status="$(python3 - "$report_path" <<'PY'
import json, sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["status"])
PY
)"

if [ "${status}" != "ok" ]; then
  echo "RESTORE_FAIL:${report_path}"
  exit 1
fi

echo "RESTORE_OK:${report_path}"
