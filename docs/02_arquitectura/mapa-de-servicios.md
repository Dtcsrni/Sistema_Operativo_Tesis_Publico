# Mapa de Servicios

Fuente maquina-legible: `manifests/service_matrix.yaml`.

## Servicios previstos
- `tesis-healthcheck.service` + timer bajo dominio `sistema_tesis`.
- `tesis-backup.service` + timer bajo dominio `administrativo`.
- `tesis-sync.service` + timer bajo dominio `sistema_tesis`.
- `openclaw-gateway.service` como servicio opcional bajo dominio `openclaw`.
- `ollama.service` como runtime principal local opcional bajo dominio `openclaw`.
- Carril NPU experimental instalado por bootstrap, sin convertirse en servicio base obligatorio.
- `edge-iot-worker.service` como servicio genérico del dominio `edge_iot`.
- `edge-iot-watchdog.service` + timer como watchdog híbrido para recuperación y cuarentena del dominio `edge_iot`.
- `prometheus.service` para scraping local y retención larga bajo dominio `administrativo`.
- `prometheus-node-exporter.service` como exporter local del host y textfile collector.
- `tesis-observabilidad-collector.service` + timer para generar métricas por dominio sin mezcla de runtime.
- `tesis-backup.service` como orquestador administrativo de backups por dominio, snapshots locales y validación de restore.

## Nota
OpenClaw no es prerequisito del sistema base ni del pipeline edge.

## Ownership por dominio
- `sistema_tesis`: usuario `tesis`, acceso mínimo a repo, outputs y logs del sistema.
- `openclaw`: usuario `openclaw`, escritura solo en su namespace, en sus logs y en el intercambio controlado.
- `administrativo`: usuarios `tesisadmin` y `prometheus`, lectura controlada de estados, observabilidad local y escritura solo a backups, snapshots, logs administrativos y textfile collector.
- `edge_iot`: usuario `edgeiot`, sin acceso directo a canon, publicación ni SQLite de `openclaw`, con runtime de resiliencia en `/var/lib/edge-iot/runtime`.
- La fuente máquina-legible incorpora `usuario`, `grupo`, `read_only_paths`, `read_write_paths`, `network_profile` y `hardening`.

_Última actualización: `2026-04-13`._
