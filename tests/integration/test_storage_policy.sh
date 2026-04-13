#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
p=Path('manifests/storage_layout.yaml')
obj=json.loads(p.read_text(encoding='utf-8'))
assert obj['medios']['nvme']['rol']=='rootfs_principal'
assert '/mnt/emmc/backups' in obj['medios']['emmc']['montajes']
print('INTEGRATION_STORAGE_POLICY_OK')
PY
