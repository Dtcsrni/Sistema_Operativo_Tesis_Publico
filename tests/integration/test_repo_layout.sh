#!/usr/bin/env bash
set -euo pipefail
test -d docs && test -d manifests && test -d bootstrap && test -d runtime && test -d data_contracts
echo INTEGRATION_REPO_LAYOUT_OK
