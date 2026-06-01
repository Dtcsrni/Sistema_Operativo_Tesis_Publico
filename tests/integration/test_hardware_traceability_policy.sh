#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from pathlib import Path
text=Path('docs/05_reproducibilidad/bitacora-de-hardware-y-laboratorio.md').read_text(encoding='utf-8') if Path('docs/05_reproducibilidad/bitacora-de-hardware-y-laboratorio.md').exists() else ''
assert 'componente' in text.lower()
print('INTEGRATION_HARDWARE_TRACEABILITY_OK')
PY
