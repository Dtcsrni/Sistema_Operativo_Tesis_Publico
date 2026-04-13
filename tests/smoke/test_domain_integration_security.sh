#!/usr/bin/env bash
set -euo pipefail

as_user() {
  local user="$1"
  shift
  if command -v sudo >/dev/null 2>&1; then
    sudo -u "$user" -- "$@"
  else
    runuser -u "$user" -- "$@"
  fi
}

expect_success() {
  if ! "$@"; then
    echo "INTEGRATION_FAIL:expected_success:$*"
    exit 1
  fi
}

expect_failure() {
  if "$@"; then
    echo "INTEGRATION_FAIL:expected_failure:$*"
    exit 1
  fi
}

test -f /etc/tesis-os/policies/domain_integration_security_policy.yaml

openclaw_outbox="/srv/tesis/intercambio/openclaw/outbox"
edge_spool="/srv/tesis/intercambio/edge/spool"
openclaw_sentinel="/var/lib/herramientas/openclaw/.integration_sentinel"
edge_sentinel="/var/lib/edge-iot/runtime/.integration_sentinel"

install -m 0640 /dev/null "${openclaw_sentinel}"
install -m 0640 /dev/null "${edge_sentinel}"
chown openclaw:openclaw "${openclaw_sentinel}"
chown edgeiot:edgeiot "${edge_sentinel}"

expect_success as_user openclaw bash -lc "printf 'draft' > '${openclaw_outbox}/t036_openclaw_draft.txt'"
expect_success as_user edgeiot bash -lc "printf 'spool' > '${edge_spool}/t036_edge_spool.txt'"
expect_success as_user tesis bash -lc "python3 /srv/tesis/repo/runtime/openclaw/bin/openclaw_local.py --help >/dev/null"

expect_failure as_user edgeiot bash -lc "cat '${openclaw_sentinel}' >/dev/null"
expect_failure as_user openclaw bash -lc "cat '${edge_sentinel}' >/dev/null"
expect_failure as_user openclaw bash -lc "touch /srv/tesis/workspace/edge/t036_cross_workspace_denied.txt"
expect_failure as_user edgeiot bash -lc "cat /etc/tesis-os/domains/academico.env >/dev/null"

if command -v curl >/dev/null 2>&1; then
  expect_failure as_user edgeiot bash -lc "curl --silent --show-error --fail --max-time 2 http://127.0.0.1:18789 >/dev/null"
fi

tmpdir="$(mktemp -d)"
tar -czf "${tmpdir}/sample.tar.gz" -C "${tmpdir}" .
sha256sum "${tmpdir}/sample.tar.gz" > "${tmpdir}/sample.tar.gz.sha256"
cat > "${tmpdir}/manifest.json" <<EOF
{
  "version": "1.0",
  "domain": "openclaw",
  "artifact_path": "${tmpdir}/sample.tar.gz",
  "checksum_path": "${tmpdir}/sample.tar.gz.sha256",
  "snapshot_path": "${tmpdir}",
  "critical_paths": [],
  "timestamp": "20260407_000000",
  "host": "test"
}
EOF
expect_failure bash /srv/tesis/repo/ops/recuperacion/restaurar_desde_emmc.sh --domain edge_iot --manifest "${tmpdir}/manifest.json" --mode sandbox --target "${tmpdir}/restore"

rm -f "${openclaw_outbox}/t036_openclaw_draft.txt" "${edge_spool}/t036_edge_spool.txt" "${openclaw_sentinel}" "${edge_sentinel}"
rm -rf "${tmpdir}"

echo "DOMAIN_INTEGRATION_SECURITY_OK"
