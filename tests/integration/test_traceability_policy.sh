#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('manifests/audit_policy.yaml').read_text(encoding='utf-8'))
assert obj['politica']['sin_auto_validacion'] is True
print('INTEGRATION_TRACEABILITY_POLICY_OK')
PY
