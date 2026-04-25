# Topologia de Almacenamiento

Fuente maquina-legible: `manifests/storage_layout.yaml`.

## Politica objetivo
- NVMe: rootfs principal, runtime, workspace, logs, caches y observabilidad local.
- eMMC: backups, corpus, datasets, exportaciones, snapshots.
- microSD: bootstrap, instalacion y rescate.
- `/srv/tesis/repo` en Orange Pi se interpreta como clon operativo para despliegue, supervision y ejecucion local; no como sede primaria de autoria del repositorio soberano.
- `openclaw` mantiene namespace separado en `/var/lib/herramientas/openclaw`, `/var/cache/herramientas/openclaw` y `/var/log/openclaw`.
- `edge_iot` mantiene namespace separado en `/var/lib/edge-iot` y `/var/log/edge-iot`.
- `administrativo` mantiene namespace separado en `/var/lib/tesis-admin` y `/var/log/tesis-admin`.
- La observabilidad local usa `/var/lib/prometheus`, `/var/lib/node_exporter/textfile_collector` y `/var/lib/tesis-observabilidad`.
- El intercambio interdominio se limita a `/srv/tesis/intercambio/...`.
- Los modelos locales de `Ollama` deben preferir `/mnt/emmc/models/ollama` cuando el montaje exista.

## Criterio tecnico
- Evitar escrituras intensivas en microSD.
- Mantener rollback manual documentado antes de migrar rootfs.
- Usar eMMC como almacenamiento templado/frio y no como rootfs principal.
- Preservar el modelo `desktop-first`: la Orange Pi almacena lo necesario para ejecutar y supervisar el edge, mientras la autoria y construccion principal viven en el escritorio.
- No compartir bases de datos, caches o logs entre dominios.
- La observabilidad se recolecta localmente y no depende de nube.

_Última actualización: `2026-04-25`._
