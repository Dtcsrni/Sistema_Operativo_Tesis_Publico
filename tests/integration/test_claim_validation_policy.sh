#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('manifests/claim_validation_policy.yaml').read_text(encoding='utf-8'))
assert 'hecho_verificado' in obj['clasificaciones']
print('INTEGRATION_CLAIM_VALIDATION_POLICY_OK')
PY
