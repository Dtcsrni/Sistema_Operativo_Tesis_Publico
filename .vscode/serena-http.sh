#!/usr/bin/env sh
set -eu

WORKSPACE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SUPERVISOR_SCRIPT="$WORKSPACE_DIR/07_scripts/serena_http_supervisor.py"

if [ ! -f "$SUPERVISOR_SCRIPT" ]; then
  echo "[serena-http] Script no encontrado: $SUPERVISOR_SCRIPT" >&2
  exit 1
fi

export SISTEMA_TESIS_ROOT="$WORKSPACE_DIR"
export PYTHONUNBUFFERED=1
export PYTHONUTF8=1
export SERENA_MCP_DEBUG_LOG="${SERENA_MCP_DEBUG_LOG:-$WORKSPACE_DIR/00_sistema_tesis/bitacora/audit_history/serena_mcp_debug.log}"

if [ -x "$WORKSPACE_DIR/.venv/bin/python" ]; then
  exec "$WORKSPACE_DIR/.venv/bin/python" -u "$SUPERVISOR_SCRIPT"
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 -u "$SUPERVISOR_SCRIPT"
fi

if command -v python >/dev/null 2>&1; then
  exec python -u "$SUPERVISOR_SCRIPT"
fi

echo "[serena-http] Python no encontrado. Se intentó: .venv/bin/python, python3, python" >&2
exit 1
