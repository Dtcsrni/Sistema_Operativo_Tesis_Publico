#!/usr/bin/env bash
set -euo pipefail
time python 07_scripts/tesis.py doctor --check
time python 07_scripts/tesis.py publish --check
