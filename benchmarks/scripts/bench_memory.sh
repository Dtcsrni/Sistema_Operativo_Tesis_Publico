#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import time
buf = bytearray(256 * 1024 * 1024)
start = time.time()
for i in range(0, len(buf), 4096):
    buf[i] = 1
print({'elapsed_s': round(time.time() - start, 3), 'bytes': len(buf)})
PY
