#!/usr/bin/env bash
set -euo pipefail

: "${TESIS_EMMC_ROOT:=/mnt/emmc}"

report_root="${1:-${TESIS_EMMC_ROOT}/backups}"

python3 - "$report_root" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
reports = sorted(root.rglob("restore_*.json"))
payload = {"reports": []}
for path in reports:
    payload["reports"].append(json.loads(path.read_text(encoding="utf-8")))
print(json.dumps(payload, indent=2, ensure_ascii=False))
PY
