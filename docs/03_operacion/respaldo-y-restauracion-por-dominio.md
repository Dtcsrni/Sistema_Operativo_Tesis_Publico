# Respaldo y Restauración por Dominio

## Objetivo
Respaldar y restaurar `sistema_tesis`, `openclaw` y `edge_iot` de forma independiente, sin mezclar rutas ni depender de un tar global del host.

## Artefactos
- Política: `/etc/tesis-os/policies/domain_backup_policy.yaml`
- Entorno administrativo: `/etc/tesis-os/backup.env`
- Orquestador: `ops/respaldo/ejecutar_respaldo.sh`
- Verificador: `ops/respaldo/verificar_respaldos.sh`
- Restore: `ops/recuperacion/restaurar_desde_emmc.sh`
- Reporte de restore: `ops/recuperacion/reporte_restauracion.sh`

## Ejecución mínima
- Correr respaldo: `bash /srv/tesis/repo/ops/respaldo/ejecutar_respaldo.sh`
- Verificar último respaldo: `bash /srv/tesis/repo/ops/respaldo/verificar_respaldos.sh`
- Restore a sandbox:
  - `bash /srv/tesis/repo/ops/recuperacion/restaurar_desde_emmc.sh --domain openclaw --manifest <manifest.json> --mode sandbox`
- Restore in-place controlado:
  - `bash /srv/tesis/repo/ops/recuperacion/restaurar_desde_emmc.sh --domain edge_iot --manifest <manifest.json> --mode in_place --target / --allow-in-place`

## Criterios
- Cada dominio genera su propio `tar.gz`, checksum y `manifest.json`.
- Además se crea un snapshot local en `/mnt/emmc/snapshots/<dominio>/`.
- El restore por defecto es `sandbox`.
- `in_place` exige banderas explícitas y validación previa del checksum.
- No hay cifrado en esta fase; la seguridad depende de ownership, permisos y aislamiento físico/lógico.

## Límite operativo
- No se respaldan modelos pesados de `Ollama` ni `RKNN-LLM` en esta fase.
- `administrativo` orquesta el proceso, pero no se trata como dominio restaurable completo.

_Última actualización: `2026-04-25`._
