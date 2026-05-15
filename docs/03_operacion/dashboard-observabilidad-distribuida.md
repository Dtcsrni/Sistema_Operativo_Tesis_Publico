# Dashboard de Observabilidad Distribuida

## Objetivo

Centralizar la observabilidad y el control gobernado del stack SIOT completo en un command center privado, operado desde contenedores Docker Compose.

El dashboard no sustituye al canon ni a los guardrails. Su funcion es hacer visible el estado operativo del stack, preparar solicitudes de control para OpenClaw y reducir la friccion de diagnostico entre PC, Edge, agentes, publicacion y trazabilidad.

## Principio de contenedores

El plano normal de ejecucion del proyecto es Docker Compose. Los servicios de dashboard, OpenClaw, Mission Control, persistencia, Toltecayotl, LLM local y observabilidad deben vivir en contenedores siempre que exista una imagen/servicio definido para ellos.

El repositorio soberano sigue siendo la fuente de verdad; los contenedores encapsulan ejecucion, observabilidad y control gobernado.

## Servicio central

Servicio Compose: `observabilidad-command-center`.

Puerto privado LAN: `8082`.

Token requerido: `SIOT_OBSERVABILITY_TOKEN`.

Rutas:

- `GET /api/observability`: snapshot privado autenticado.
- `GET /api/public-observability`: snapshot publico sanitizado.
- `POST /api/heartbeat`: marca monitoreo activo y permite suprimir notificaciones redundantes por Telegram.
- `POST /api/control/request`: crea una solicitud gobernada para OpenClaw en `runtime/observability/control_requests.jsonl`.

## Politica de control

La UI puede crear solicitudes de control, pero no ejecuta comandos arbitrarios ni expone un Docker socket crudo al navegador.

Toda mutacion queda en estado `pending_human_approval` y debe pasar por OpenClaw, guardrails y validacion humana cuando aplique.

## Fuentes de estado

- `docker-compose.yml`: stack vivo del PC Hub.
- `manifests/service_matrix.yaml`: matriz de servicios y criticidad.
- `manifests/operational_topology.yaml`: roles PC/Edge.
- `manifests/observability_policy.yaml`: Prometheus, logs y textfile collector.
- `00_sistema_tesis/config/openclaw_status.json`: estado runtime OpenClaw.
- `runtime/pc_control/benchmarks/index.json`: evidencia PC.
- `runtime/edge_iot/benchmarks/index.json`: evidencia Edge.
- `06_dashboard/publico/manifest_publico.json`: estado de publicacion sanitizada.

## Uso minimo

```bash
python3 07_scripts/ops/build_observability_snapshot.py
python3 07_scripts/ops/build_dashboard.py
SIOT_OBSERVABILITY_TOKEN=valor-local docker compose up -d observabilidad-command-center
```

Vista privada:

```bash
curl -H "Authorization: Bearer $SIOT_OBSERVABILITY_TOKEN" http://127.0.0.1:8082/api/observability
```

Solicitud gobernada:

```bash
curl -X POST \
  -H "Authorization: Bearer $SIOT_OBSERVABILITY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"intent":"diagnose_stack","target":"docker-compose","reason":"revision operativa"}' \
  http://127.0.0.1:8082/api/control/request
```

_Última actualización: `2026-05-15`._
