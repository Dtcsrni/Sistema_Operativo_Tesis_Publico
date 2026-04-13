#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('manifests/hardware_validation_policy.yaml').read_text(encoding='utf-8'))
assert 'seguridad_primero' in obj['principios']
print('INTEGRATION_HARDWARE_POLICY_OK')
PY
