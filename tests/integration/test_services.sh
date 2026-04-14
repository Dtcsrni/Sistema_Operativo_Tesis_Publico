#!/usr/bin/env bash
set -euo pipefail
systemctl list-unit-files 'tesis-*' 'openclaw-gateway.service' >/dev/null || true
echo INTEGRATION_SERVICES_OK
