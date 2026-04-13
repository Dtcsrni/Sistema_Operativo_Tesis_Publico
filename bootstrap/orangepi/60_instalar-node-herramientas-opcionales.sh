#!/usr/bin/env bash
set -euo pipefail
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt-get install -y nodejs
if [[ "${INSTALL_OPENCLAW:-0}" == "1" ]]; then
  sudo npm install -g openclaw@latest
fi
