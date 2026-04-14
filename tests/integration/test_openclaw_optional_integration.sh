#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('manifests/openclaw_evaluation_policy.yaml').read_text(encoding='utf-8'))
assert obj['posicion']=='capa_asistiva_opcional'
assert obj['fallo_de_openclaw_no_detiene_sistema'] is True
print('INTEGRATION_OPENCLAW_OPTIONAL_OK')
PY
