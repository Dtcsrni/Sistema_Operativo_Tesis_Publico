#!/usr/bin/env bash
set -euo pipefail

: "${TESIS_EMMC_ROOT:=/mnt/emmc}"
: "${TESIS_BACKUP_POLICY:=/etc/tesis-os/policies/domain_backup_policy.yaml}"
: "${TESIS_BACKUP_TMPDIR:=/tmp/tesis-backup}"
: "${TESIS_BACKUP_SIGN_KEY:=}"

ts="$(date +%Y%m%d_%H%M%S)"
report_dir="${TESIS_EMMC_ROOT}/backups/reports"
mkdir -p "${report_dir}" "${TESIS_BACKUP_TMPDIR}"

mapfile -t DOMAINS < <(python3 - "$TESIS_BACKUP_POLICY" <<'PY' | tr -d '\r'
import json, sys
from pathlib import Path
policy = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if policy.get("encryption") != "required_age_or_gpg":
    raise SystemExit("BACKUP_FAIL:policy_encryption_must_be_required_age_or_gpg")
for name in policy["domains"]:
    print(name)
PY
)

if [ -z "${TESIS_BACKUP_SIGN_KEY}" ]; then
  echo "BACKUP_FAIL:missing_TESIS_BACKUP_SIGN_KEY"
  exit 1
fi

artifacts_json="["
first=1

for domain in "${DOMAINS[@]}"; do
  mapfile -t META < <(python3 - "$TESIS_BACKUP_POLICY" "$domain" <<'PY' | tr -d '\r'
import json, sys
from pathlib import Path
policy = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
domain = policy["domains"][sys.argv[2]]
print(domain["backup_dir"])
print(domain["snapshot_dir"])
print(json.dumps(domain["include_paths"]))
print(json.dumps(domain["exclude_globs"]))
print(json.dumps(domain["critical_paths"]))
PY
)

  backup_dir="${META[0]}"
  snapshot_dir="${META[1]}"
  include_json="${META[2]}"
  exclude_json="${META[3]}"
  critical_json="${META[4]}"

  artifact_dir="${backup_dir}/${ts}"
  snapshot_target="${snapshot_dir}/${ts}"
  mkdir -p "${artifact_dir}" "${snapshot_target}"

  include_file="${TESIS_BACKUP_TMPDIR}/${domain}_include_${ts}.txt"
  exclude_file="${TESIS_BACKUP_TMPDIR}/${domain}_exclude_${ts}.txt"

  python3 - "$include_json" "$exclude_json" "$include_file" "$exclude_file" <<'PY'
import json
import sys
import os
includes = [item.lstrip("/") for item in json.loads(sys.argv[1]) if os.path.exists(item)]
excludes = json.loads(sys.argv[2])
with open(sys.argv[3], 'w', encoding='utf-8', newline='\n') as f:
    f.write("\n".join(includes) + "\n")
with open(sys.argv[4], 'w', encoding='utf-8', newline='\n') as f:
    f.write("\n".join(excludes) + ("\n" if excludes else ""))
PY

  artifact_path="${artifact_dir}/${domain}_${ts}.tar.gz"
  checksum_path="${artifact_path}.sha256"
  signature_path="${artifact_path}.sha256.sig"
  manifest_path="${artifact_dir}/manifest.json"
  manifest_signature_path="${artifact_dir}/manifest.json.sig"

  tar --force-local --exclude-from="${exclude_file}" -czf "${artifact_path}" -C / -T "${include_file}"
  sha256sum "${artifact_path}" > "${checksum_path}"
  python3 - "${TESIS_BACKUP_SIGN_KEY}" "${artifact_path}" "${signature_path}" <<'PY'
import hashlib, hmac, sys
from pathlib import Path
sign_key = sys.argv[1].encode("utf-8")
artifact_path = Path(sys.argv[2])
sig_path = Path(sys.argv[3])
sig = hmac.new(sign_key, artifact_path.as_posix().encode("utf-8"), hashlib.sha256).hexdigest()
sig_path.write_text(sig + "\n", encoding="utf-8", newline="\n")
PY
  tar --exclude-from="${exclude_file}" -cf - -C / -T "${include_file}" | tar -xf - -C "${snapshot_target}"

  python3 - "$manifest_path" "$domain" "$artifact_path" "$checksum_path" "$signature_path" "$snapshot_target" "$critical_json" "$ts" <<'PY'
import json
import os
import socket
import sys
from pathlib import Path

payload = {
    "version": "1.0",
    "domain": sys.argv[2],
    "artifact_path": sys.argv[3],
    "checksum_path": sys.argv[4],
    "checksum_signature_path": sys.argv[5],
    "snapshot_path": sys.argv[6],
    "critical_paths": json.loads(sys.argv[7]),
    "timestamp": sys.argv[8],
    "host": socket.gethostname(),
    "billing_mode": "none",
    "signature_algorithm": "hmac-sha256",
}
with open(sys.argv[1], 'w', encoding='utf-8', newline='\n') as f:
    f.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(payload, ensure_ascii=False))
PY
  python3 - "${TESIS_BACKUP_SIGN_KEY}" "${manifest_path}" "${manifest_signature_path}" <<'PY'
import hashlib, hmac, sys
from pathlib import Path
sign_key = sys.argv[1].encode("utf-8")
manifest_path = Path(sys.argv[2])
sig_path = Path(sys.argv[3])
sig = hmac.new(sign_key, manifest_path.read_bytes(), hashlib.sha256).hexdigest()
sig_path.write_text(sig + "\n", encoding="utf-8", newline="\n")
PY
  artifact_payload="$(python3 - "$manifest_path" <<'PY' | tr -d '\r'
import json, sys
from pathlib import Path
print(json.dumps(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), ensure_ascii=False))
PY
)"
  if [ "${first}" -eq 0 ]; then
    artifacts_json="${artifacts_json},"
  fi
  artifacts_json="${artifacts_json}${artifact_payload}"
  first=0
done

artifacts_json="${artifacts_json}]"
report_path="${report_dir}/backup_report_${ts}.json"
python3 - "$report_path" "$artifacts_json" "$ts" <<'PY'
import json, sys
payload = {
    "version": "1.0",
    "timestamp": sys.argv[3],
    "artifacts": json.loads(sys.argv[2]),
}
with open(sys.argv[1], 'w', encoding='utf-8', newline='\n') as f:
    f.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
PY

echo "BACKUP_OK:${report_path}"
