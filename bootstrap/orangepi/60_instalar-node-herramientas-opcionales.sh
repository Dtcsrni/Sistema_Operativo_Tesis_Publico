#!/usr/bin/env bash
set -euo pipefail
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
if [[ "${INSTALL_OPENCLAW:-0}" == "1" ]]; then
  npm_prefix="${OPENCLAW_NPM_PREFIX:-${HOME}/.local}"
  mkdir -p "${npm_prefix}/bin"
  export NPM_CONFIG_PREFIX="${npm_prefix}"
  export PATH="${npm_prefix}/bin:${PATH}"
  npm install -g openclaw@latest
fi
