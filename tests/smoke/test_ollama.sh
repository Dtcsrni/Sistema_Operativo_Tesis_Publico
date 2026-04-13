#!/usr/bin/env bash
set -euo pipefail
if ! command -v ollama >/dev/null 2>&1; then
  echo "SMOKE_OLLAMA_SKIPPED:no_instalado"
  exit 0
fi
ollama --version >/dev/null
echo "SMOKE_OLLAMA_OK"
