#!/usr/bin/env bash
set -euo pipefail

test -f /etc/tesis-os/policies/domain_runtime_isolation.yaml
test -f /etc/tesis-os/policies/domain_network_policy.yaml
test -f /etc/tesis-os/policies/interdomain_exchange_contract.yaml
getent passwd openclaw >/dev/null
getent passwd edgeiot >/dev/null
getent passwd tesisadmin >/dev/null
test -d /srv/tesis/intercambio/openclaw/spool
test -d /srv/tesis/intercambio/edge/spool
systemctl cat openclaw-gateway.service | grep -q "User=openclaw"
echo "DOMAIN_ISOLATION_OK"
