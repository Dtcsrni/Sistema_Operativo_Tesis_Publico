#!/bin/bash
# Wrapper para ejecutar pet_api_server con PYTHONPATH correcto

set -e

# Establecer PYTHONPATH
export PYTHONPATH="/app/runtime/openclaw:/app:${PYTHONPATH}"

# Ejecutar el servidor
cd /app
exec python 07_scripts/pet_api_server.py "$@"
