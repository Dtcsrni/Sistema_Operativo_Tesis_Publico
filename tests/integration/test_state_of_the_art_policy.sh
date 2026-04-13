#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('manifests/state_of_the_art_workflow.yaml').read_text(encoding='utf-8'))
assert 'matriz_literatura' in obj['flujo']
print('INTEGRATION_STATE_OF_THE_ART_OK')
PY
