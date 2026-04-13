# Observabilidad por Dominio

## Baseline
- Logs por dominio en filesystem y soporte adicional en `journald`.
- Métricas del host mediante `node_exporter`.
- Métricas de dominio mediante `textfile collector` local.
- Scraping local por `Prometheus`.

## Separación
- `sistema_tesis` escribe solo en `/var/log/tesis-os`.
- `openclaw` escribe solo en `/var/log/openclaw`.
- `edge_iot` escribe solo en `/var/log/edge-iot`.
- `administrativo` concentra backup y observabilidad en `/var/log/tesis-admin`.
- Ningún dominio expone métricas fuera de `localhost`.

## Retención
- `logrotate` diario
- 90 rotaciones
- compresión diferida
- corte por tamaño de 50 MB

## Scrape local
- `Prometheus`: `127.0.0.1:9090`
- `node_exporter`: `127.0.0.1:9100`
- Archivos `.prom` por dominio en `/var/lib/node_exporter/textfile_collector`

_Última actualización: `2026-04-13`._
