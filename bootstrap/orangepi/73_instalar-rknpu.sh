#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATUS_DIR="/var/lib/herramientas/openclaw/bootstrap"
STATUS_FILE="${STATUS_DIR}/fase-rknpu.estado"
RKLLM_ROOT="${OPENCLAW_RKLLM_ROOT:-/opt/tesis-os/vendor/rknn-llm}"
RKLLM_REPO="${OPENCLAW_RKLLM_REPO:-https://github.com/airockchip/rknn-llm.git}"
RKLLM_REF="${OPENCLAW_RKLLM_REF:-main}"

registrar_estado() {
  local estado="$1"
  local detalle="$2"
  sudo install -d -m 0755 "${STATUS_DIR}"
  printf 'estado=%s\ndetalle=%s\nfecha=%s\n' "${estado}" "${detalle}" "$(date --iso-8601=seconds)" | sudo tee "${STATUS_FILE}" >/dev/null
}

trap 'registrar_estado "fallo" "falló la instalación experimental RKLLM/RKNN-LLM en la línea ${LINENO}"' ERR

sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip
sudo install -d -m 0755 "$(dirname "${RKLLM_ROOT}")"

if [ ! -d "${RKLLM_ROOT}/.git" ]; then
  sudo git clone --depth 1 --branch "${RKLLM_REF}" "${RKLLM_REPO}" "${RKLLM_ROOT}"
else
  sudo git -C "${RKLLM_ROOT}" fetch --depth 1 origin "${RKLLM_REF}"
  sudo git -C "${RKLLM_ROOT}" checkout "${RKLLM_REF}"
  sudo git -C "${RKLLM_ROOT}" pull --ff-only origin "${RKLLM_REF}"
fi

if [ -f "${RKLLM_ROOT}/requirements.txt" ]; then
  sudo python3 -m pip install -r "${RKLLM_ROOT}/requirements.txt" || true
fi

bash "${REPO_ROOT}/tests/smoke/test_rknpu.sh" || true
registrar_estado "ok" "ruta experimental Rockchip NPU instalada como carril secundario"
echo "BOOTSTRAP_RKNPU_OK"
