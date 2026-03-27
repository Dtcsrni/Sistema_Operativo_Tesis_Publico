# Topologia de Almacenamiento

Fuente maquina-legible: `manifests/storage_layout.yaml`.

## Politica objetivo
- NVMe: rootfs principal, runtime, workspace, logs y caches.
- eMMC: backups, corpus, datasets, exportaciones, snapshots.
- microSD: bootstrap, instalacion y rescate.

## Criterio tecnico
- Evitar escrituras intensivas en microSD.
- Mantener rollback manual documentado antes de migrar rootfs.
- Usar eMMC como almacenamiento templado/frio y no como rootfs principal.
