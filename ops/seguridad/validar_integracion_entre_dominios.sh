#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
REPORT_DIR="${DOMAIN_INTEGRATION_REPORT_DIR:-/var/log/tesis-admin}"
REPORT_PATH="${DOMAIN_INTEGRATION_REPORT_PATH:-${REPORT_DIR}/domain_integration_security_report_${TIMESTAMP}.log}"
SMOKE_SCRIPT="${REPO_ROOT}/tests/smoke/test_domain_integration_security.sh"

mkdir -p "${REPORT_DIR}"

{
  echo "reporte=seguridad_integracion_dominios"
  echo "fecha=${TIMESTAMP}"
  echo "repo_root=${REPO_ROOT}"
  echo "script=${SMOKE_SCRIPT}"
  echo "inicio"
  bash "${SMOKE_SCRIPT}"
  echo "resultado=ok"
} | tee "${REPORT_PATH}"

echo "DOMAIN_INTEGRATION_SECURITY_OK report=${REPORT_PATH}"
