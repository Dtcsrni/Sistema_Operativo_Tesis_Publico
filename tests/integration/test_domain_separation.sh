#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('manifests/domain_boundaries.yaml').read_text(encoding='utf-8'))
assert len(obj['dominios']) == 5
print('INTEGRATION_DOMAIN_SEPARATION_OK')
PY
