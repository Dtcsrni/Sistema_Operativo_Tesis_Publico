#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('manifests/research_exploration_policy.yaml').read_text(encoding='utf-8'))
assert 'investigacion' in obj['niveles']
print('INTEGRATION_EXPLORATION_POLICY_OK')
PY
