# Política de Red por Dominio

## Reglas globales
- `allow_interdomain_http = false`
- `allow_cross_workspace_reads = false`
- `allow_cross_domain_sqlite = false`

## Perfiles
- `salida_minima`: sistema base con la salida estrictamente necesaria para sincronización ya existente.
- `egress_controlado_localhost_in`: `openclaw` con escucha solo en `localhost` y salida controlada a proveedores.
- `edge_restringido`: `edge_iot` con puertos explícitos y sin acceso a canon ni publicación.
- `edge_restringido` no permite healthchecks HTTP; la salud se valida por script local.
- `sin_nube`: dominio administrativo para backup y collector local sin salida a nube.
- `offline_logico`: dominio personal.
- `solo_localhost_observabilidad`: `Prometheus` y `node_exporter` limitados a `127.0.0.1`, solo para scraping local.

## Criterio operativo
- abrir puertos solo cuando exista servicio y contrato explícito;
- negar mezcla de dominios por red;
- preferir intercambio por archivos/CLI antes que sockets o APIs;
- exponer métricas solo en `localhost` y nunca como canal interdominio general.

_Última actualización: `2026-04-14`._
