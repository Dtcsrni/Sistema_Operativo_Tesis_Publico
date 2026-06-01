#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

set +e
bash "${REPO_ROOT}/tests/smoke/test_openclaw.sh"
OPENCLAW_RC=$?
bash "${REPO_ROOT}/tests/smoke/test_ollama.sh"
OLLAMA_RC=$?
bash "${REPO_ROOT}/tests/smoke/test_rknpu.sh"
RKNPU_RC=$?
set -e

printf 'POSTCHECK_OPENCLAW openclaw=%s ollama=%s rknpu=%s\n' "${OPENCLAW_RC}" "${OLLAMA_RC}" "${RKNPU_RC}"
exit 0
