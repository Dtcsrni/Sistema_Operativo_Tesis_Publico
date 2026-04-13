#!/usr/bin/env bash
set -euo pipefail

test -f /etc/tesis-os/policies/domain_backup_policy.yaml
test -f /etc/tesis-os/backup.env
test -x /srv/tesis/repo/ops/respaldo/ejecutar_respaldo.sh
test -x /srv/tesis/repo/ops/respaldo/verificar_respaldos.sh
test -x /srv/tesis/repo/ops/recuperacion/restaurar_desde_emmc.sh
test -x /srv/tesis/repo/ops/recuperacion/reporte_restauracion.sh
systemctl cat tesis-backup.service | grep -q "EnvironmentFile=/etc/tesis-os/backup.env"
systemctl cat tesis-backup.service | grep -q "/mnt/emmc/snapshots"
echo "DOMAIN_BACKUP_OK"
