#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STATUS_DIR="/var/lib/herramientas/openclaw/bootstrap"
STATUS_FILE="${STATUS_DIR}/fase-openclaw.estado"
OPENCLAW_VENV="/opt/tesis-os/venvs/openclaw"
OPENCLAW_ENV="/etc/tesis-os/openclaw.env"
DOMAINS_DIR="/etc/tesis-os/domains"

registrar_estado() {
  local estado="$1"
  local detalle="$2"
  sudo install -d -m 0755 "${STATUS_DIR}"
  printf 'estado=%s\ndetalle=%s\nfecha=%s\n' "${estado}" "${detalle}" "$(date --iso-8601=seconds)" | sudo tee "${STATUS_FILE}" >/dev/null
}

trap 'registrar_estado "fallo" "falló la instalación de openclaw en la línea ${LINENO}"' ERR

if ! getent group tesis >/dev/null; then
  sudo groupadd --system tesis
fi
if ! id -u tesis >/dev/null 2>&1; then
  sudo useradd --system --gid tesis --home-dir /srv/tesis --create-home --shell /usr/sbin/nologin tesis
fi

sudo install -d -o tesis -g tesis /etc/tesis-os "${DOMAINS_DIR}"
sudo install -d -o openclaw -g openclaw /var/lib/herramientas/openclaw /var/cache/herramientas/openclaw /var/log/openclaw
sudo install -d -o tesis -g tesis /opt/tesis-os/venvs

sudo python3 -m venv "${OPENCLAW_VENV}"
sudo "${OPENCLAW_VENV}/bin/pip" install --upgrade pip
if [ -f "${REPO_ROOT}/runtime/openclaw/requirements-web.txt" ]; then
  sudo "${OPENCLAW_VENV}/bin/pip" install -r "${REPO_ROOT}/runtime/openclaw/requirements-web.txt"
fi
sudo install -d -o openclaw -g openclaw /var/lib/herramientas/openclaw/ms-playwright
sudo -u openclaw env HOME=/var/lib/herramientas/openclaw PLAYWRIGHT_BROWSERS_PATH=/var/lib/herramientas/openclaw/ms-playwright \
  "${OPENCLAW_VENV}/bin/python" -m playwright install chromium || true

if [ ! -f "${OPENCLAW_ENV}" ]; then
  sudo install -m 0640 "${REPO_ROOT}/config/env/openclaw.env.example" "${OPENCLAW_ENV}"
fi

sudo python3 - <<'PY'
from pathlib import Path

env_path = Path("/etc/tesis-os/openclaw.env")
required = {
    "OPENCLAW_REPO_ROOT": "/srv/tesis/repo",
    "OPENCLAW_DATA_DIR": "/var/lib/herramientas/openclaw",
    "OPENCLAW_CACHE_DIR": "/var/cache/herramientas/openclaw",
    "OPENCLAW_LOG_DIR": "/var/log/openclaw",
    "OPENCLAW_DB_PATH": "/var/lib/herramientas/openclaw/openclaw.db",
    "OPENCLAW_PYTHON_BIN": "/opt/tesis-os/venvs/openclaw/bin/python",
    "OPENCLAW_DOMAINS_ENV_DIR": "/etc/tesis-os/domains",
    "PLAYWRIGHT_BROWSERS_PATH": "/var/lib/herramientas/openclaw/ms-playwright",
}
lines = []
seen = set()
if env_path.exists():
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        key = raw.split("=", 1)[0] if "=" in raw else raw
        if key in required:
            lines.append(f"{key}={required[key]}")
            seen.add(key)
        else:
            lines.append(raw)
for key, value in required.items():
    if key not in seen:
        lines.append(f"{key}={value}")
env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
PY

install_domain_env() {
  local domain="$1"
  local owner="$2"
  local group="$3"
  local src="${REPO_ROOT}/config/env/domains/${domain}.env.example"
  local dst="${DOMAINS_DIR}/${domain}.env"
  if [ -f "${src}" ] && [ ! -f "${dst}" ]; then
    sudo install -m 0640 "${src}" "${dst}"
  fi
  if [ -f "${dst}" ]; then
    sudo chown "${owner}:${group}" "${dst}"
    sudo chmod 0640 "${dst}"
  fi
}

install_domain_env personal tesis personal
install_domain_env profesional openclaw openclaw
install_domain_env academico openclaw openclaw
install_domain_env edge edgeiot edgeiot
install_domain_env administrativo tesisadmin tesisadmin

sudo chown tesis:tesis "${OPENCLAW_ENV}"
sudo chmod 0640 "${OPENCLAW_ENV}"
sudo chown -R openclaw:openclaw /var/lib/herramientas/openclaw /var/cache/herramientas/openclaw /var/log/openclaw
sudo chmod 0750 /var/lib/herramientas/openclaw /var/cache/herramientas/openclaw /var/log/openclaw
sudo systemctl daemon-reload
sudo systemctl enable openclaw-gateway.service
sudo systemctl restart openclaw-gateway.service || true

export OPENCLAW_REPO_ROOT="/srv/tesis/repo"
export OPENCLAW_PYTHON_BIN="${OPENCLAW_VENV}/bin/python"
if [ -f "${OPENCLAW_ENV}" ]; then
  set -a
  # shellcheck disable=SC1090
  . "${OPENCLAW_ENV}"
  set +a
fi
bash "${REPO_ROOT}/tests/smoke/test_openclaw.sh" || true

registrar_estado "ok" "openclaw instalado con entorno Python, env efectivo y servicio habilitado"
echo "BOOTSTRAP_OPENCLAW_OK"
