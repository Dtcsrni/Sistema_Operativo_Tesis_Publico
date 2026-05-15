---
title: "ISSUE-0047: Dashboard de Observabilidad Distribuida SIOT"
date: 2026-05-06
category: operation
status: in_progress
reporter: "Codex"
---

# ISSUE-0047: Dashboard de Observabilidad Distribuida SIOT

## Objetivo

Implementar un command center privado para centralizar observabilidad y control gobernado del stack SIOT completo, con ejecucion normal en Docker Compose.

## Alcance

- Dashboard NOC industrial para tesista operador.
- Stack completo: PC Hub, Edge, OpenClaw/agentes, observabilidad, benchmarks, publicacion y trazabilidad.
- Servicio `observabilidad-command-center` en `docker-compose.yml`.
- Snapshot privado y snapshot publico sanitizado.
- Cola de solicitudes de control para OpenClaw, sin ejecucion arbitraria desde navegador.

## Criterios de aceptacion tecnica

- [ ] `python3 07_scripts/ops/build_observability_snapshot.py` genera snapshot privado y publico.
- [ ] `python3 07_scripts/ops/build_dashboard.py` incorpora la seccion `Observabilidad Distribuida SIOT`.
- [ ] `docker compose config` valida `observabilidad-command-center`.
- [ ] La API privada exige `SIOT_OBSERVABILITY_TOKEN`.
- [ ] La vista publica no contiene tokens, endpoints privados ni rutas sensibles.
- [ ] Las solicitudes de control quedan en `runtime/observability/control_requests.jsonl` como `pending_human_approval`.

## Estado tecnico de la implementacion

- `build_observability_snapshot.py` y `build_dashboard.py` ya generan las vistas y el dashboard con la seccion de observabilidad distribuida.
- `docker compose config` quedaba bloqueado por secretos requeridos en `config/env/openclaw.env`; la configuracion local ahora usa valores de reemplazo controlados para permitir validacion estructural sin exponer secretos.
- La validacion humana de cierre sigue pendiente y requiere Step ID antes de marcar el issue como cerrado.

## Nota de gobernanza

Este issue no valida por si mismo la operacion. Cualquier cierre formal requiere Step ID humano y trazabilidad canonica.

_Última actualización: `2026-05-15`._
