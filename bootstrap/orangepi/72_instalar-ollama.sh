#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATUS_DIR="/var/lib/herramientas/openclaw/bootstrap"
STATUS_FILE="${STATUS_DIR}/fase-ollama.estado"
OLLAMA_MODELS_DIR="${OLLAMA_MODELS:-/mnt/emmc/models/ollama}"

registrar_estado() {
  local estado="$1"
  local detalle="$2"
  sudo install -d -m 0755 "${STATUS_DIR}"
  printf 'estado=%s\ndetalle=%s\nfecha=%s\n' "${estado}" "${detalle}" "$(date --iso-8601=seconds)" | sudo tee "${STATUS_FILE}" >/dev/null
}

trap 'registrar_estado "fallo" "falló la instalación de Ollama en la línea ${LINENO}"' ERR

if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi

if [ -d /mnt/emmc/models ]; then
  sudo install -d -m 0755 "${OLLAMA_MODELS_DIR}"
  sudo install -d -m 0755 /etc/systemd/system/ollama.service.d
  cat <<EOF | sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null
[Service]
Environment=OLLAMA_MODELS=${OLLAMA_MODELS_DIR}
EOF
fi

sudo systemctl daemon-reload || true
sudo systemctl enable ollama.service || true
sudo systemctl restart ollama.service || true

bash "${REPO_ROOT}/tests/smoke/test_ollama.sh" || true
registrar_estado "ok" "ollama instalado como runtime principal local"
echo "BOOTSTRAP_OLLAMA_OK"
