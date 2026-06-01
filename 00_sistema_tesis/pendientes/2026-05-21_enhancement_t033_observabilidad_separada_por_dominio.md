---
title: "T-033 Observabilidad separada por dominio"
date: 2026-05-21
category: enhancement
status: closed
owner: "Tesista Principal / HOA"
decisions: ["DEC-0046", "DEC-0030", "DEC-0037", "DEC-0025"]
step_id: "validación humana interna no pública"
trace_status: "validado"
---

# T-033 Observabilidad separada por dominio

## Objetivo

Implementar una capa de observabilidad distribuida con aislamiento estricto por dominio
(`edge_iot`, `openclaw`, `sistema_tesis`) utilizando estandares abiertos CNCF
(Prometheus + OpenTelemetry), garantizando que las bitacoras tecnicas de un dominio
nunca se mezclen con las de otro, y que el stack sea desplegable tanto local como en nube.

Alineado con **DEC-0046**: arquitectura abierta, agnostica y comercialmente viable.

## Alcance

- **Incluye:**
  - Ampliar `config/prometheus/prometheus.yml` con scrape targets separados por dominio
    (`edge_iot`, `openclaw`, `host`), con labels de aislamiento obligatorios.
  - Crear `config/prometheus/rules/` con alertas basicas por dominio (node down, high memory).
  - Configurar `runtime/edge_iot/logs/` y `runtime/openclaw/logs/` como rutas independientes,
    sin cruce entre dominios.
  - Agregar un `node_exporter` en el perfil Docker del Edge para exponer metricas del hardware
    Orange Pi (CPU, RAM, temperatura NPU).
  - Script de verificacion `07_scripts/audit/verify_observability_isolation.py`.
- **Excluye:**
  - Implementar un stack de trazas distribuidas completo (Jaeger/Tempo) en esta iteracion.
    Se dejara el puerto OpenTelemetry listo pero el collector se priorizara en T-034.
  - Dashboards Grafana (se integran en T-034 como dependencia de este).

## Rutas Afectadas

- `config/prometheus/prometheus.yml` [MODIFY]
- `config/prometheus/rules/edge_iot.yml` [NEW]
- `config/prometheus/rules/openclaw.yml` [NEW]
- `docker-compose.edge.yml` [MODIFY] — agregar node_exporter al perfil edge
- `07_scripts/audit/verify_observability_isolation.py` [NEW]

## Gates Publicos

- Las metricas del dominio `edge_iot` deben incluir el label `dominio=edge_iot` en todos
  los scrape targets.
- Las metricas del dominio `openclaw` deben incluir el label `dominio=openclaw`.
- Ningun log de un dominio debe escribirse en la ruta de otro dominio.
- `build_all.py` pasa sin regresiones.

## Pruebas y Aceptacion

- Ejecucion de `python 07_scripts/audit/verify_observability_isolation.py`.
- Consulta Prometheus: `{dominio="edge_iot"}` retorna solo metricas del Edge.
- Consulta Prometheus: `{dominio="openclaw"}` retorna solo metricas del hub.

## Rollback

Revertir `prometheus.yml` desde su `.bak`, eliminar los archivos `rules/` nuevos y
remover el servicio `node_exporter` del `docker-compose.edge.yml`.

## Viabilidad Comercial (DEC-0046)

- **Producto:** Stack de observabilidad IoT distribuido listo para venta como modulo independiente.
- **Segmento:** Municipios y plantas industriales que ya usan Prometheus/Grafana.
- **Diferenciador:** Aislamiento por dominio out-of-the-box; cero configuracion adicional.

## Cierre de Trazabilidad

Validado formalmente en validación humana interna no pública. Arquitectura híbrida OTel+MQTT+Prometheus implementada.
Archivos entregados: `config/otel/collector-edge.yml`, `config/otel/collector-hub.yml`,
`config/prometheus/prometheus.yml`, `config/prometheus/rules/{edge_iot,openclaw,sistema_tesis}.yml`,
`docker-compose.edge.yml` (servicios metrics), `07_scripts/audit/verify_observability_isolation.py`.
Verificación: 5/5 OK, 0 advertencias.



## FRE



## ESE

_Última actualización: `2026-06-01`._
