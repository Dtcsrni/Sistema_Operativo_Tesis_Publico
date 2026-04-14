# Observabilidad Local por Dominio

## Componentes
- `prometheus.service` escucha en `127.0.0.1:9090`.
- `prometheus-node-exporter.service` escucha en `127.0.0.1:9100`.
- `tesis-observabilidad-collector.timer` genera métricas por dominio cada 2 minutos.
- `logrotate` aplica retención larga y compresión a logs de `sistema_tesis`, `openclaw`, `edge_iot` y `administrativo`.

## Rutas
- Logs del sistema: `/var/log/tesis-os`
- Logs de OpenClaw: `/var/log/openclaw`
- Logs de edge: `/var/log/edge-iot`
- Logs administrativos y observabilidad: `/var/log/tesis-admin`
- Textfile collector: `/var/lib/node_exporter/textfile_collector`
- Almacenamiento de Prometheus: `/var/lib/prometheus`

## Validación mínima
- `systemctl status prometheus.service`
- `systemctl status prometheus-node-exporter.service`
- `systemctl status tesis-observabilidad-collector.timer`
- `bash /srv/tesis/repo/tests/smoke/test_observability_stack.sh`

## Métricas por dominio
Cada dominio publica al menos:
- estado del servicio;
- estado del último healthcheck;
- latencia del healthcheck;
- tamaño acumulado de logs;
- errores recientes en logs;
- timestamp de última actividad útil.

`edge_iot` además publica:
- estado de resiliencia;
- fallas consecutivas;
- timestamp de última recuperación;
- bandera y vencimiento de cuarentena.

## Límite operativo
La observabilidad es local al host y no sustituye la trazabilidad documental del sistema.

_Última actualización: `2026-04-14`._
