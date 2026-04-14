#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('manifests/bibliography_policy.yaml').read_text(encoding='utf-8'))
assert 'verificacion_doi' in obj['flujo']
print('INTEGRATION_BIBLIOGRAPHY_POLICY_OK')
PY
