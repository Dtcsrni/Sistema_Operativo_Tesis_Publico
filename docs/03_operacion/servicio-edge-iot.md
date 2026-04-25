# Servicio `edge_iot`

## Objetivo
Operar un servicio genérico del dominio `edge_iot` sin acoplarlo todavía a una app específica.

## Archivos operativos
- Unidad: `config/systemd/edge-iot-worker.service`
- Watchdog: `config/systemd/edge-iot-watchdog.service` + `config/systemd/edge-iot-watchdog.timer`
- Entorno: `/etc/tesis-os/edge-iot.env`
- Wrapper de ejecución: `ops/edge/edge-iot-run.sh`
- Preflight: `ops/edge/edge-iot-preflight.sh`
- Healthcheck: `ops/edge/edge-iot-healthcheck.sh`
- Control de resiliencia: `ops/edge/edge-iot-resilience.sh`
- Lógica watchdog: `ops/edge/edge-iot-watchdog.sh`

## Operación mínima
- Arranque: `systemctl start edge-iot-worker.service`
- Estado: `systemctl status edge-iot-worker.service`
- Watchdog: `systemctl status edge-iot-watchdog.timer`
- Healthcheck: `bash /srv/tesis/repo/ops/edge/edge-iot-healthcheck.sh`
- Estado de resiliencia: `bash /srv/tesis/repo/ops/edge/edge-iot-resilience.sh status`
- Limpiar cuarentena: `bash /srv/tesis/repo/ops/edge/edge-iot-resilience.sh clear-quarantine`
- Simular fallo blando: `bash /srv/tesis/repo/ops/edge/edge-iot-resilience.sh simulate-soft-failure`
- Simular fallo duro: `bash /srv/tesis/repo/ops/edge/edge-iot-resilience.sh simulate-hard-failure`
- Log de servicio: `/var/log/edge-iot/edge-iot-worker.log`
- Log de resiliencia: `/var/log/edge-iot/edge-iot-resilience.log`
- Log de watchdog: `/var/log/edge-iot/edge-iot-watchdog.log`
- Métricas de dominio: `/var/lib/node_exporter/textfile_collector/edge-iot.prom`

## Rutas permitidas
- Estado: `/var/lib/edge-iot`
- Runtime de resiliencia: `/var/lib/edge-iot/runtime`
- Logs: `/var/log/edge-iot`
- Workspace: `/srv/tesis/workspace/edge`
- Intercambio: `/srv/tesis/intercambio/edge`

## Límites
- No puede escribir en canon ni publicación.
- No depende de `openclaw`, `ollama` ni timers del sistema base.
- El healthcheck es por script local; no hay endpoint HTTP.
- Sus métricas se recolectan localmente por textfile collector; no expone canal interdominio propio.
- Ante intermitencia externa, degrada a `degraded_offline`, encola evidencia en `spool` y solo reinicia cuando cruza el umbral configurado.
- Si excede el máximo de fallas consecutivas, entra en `quarantined` y deja evidencia operativa para revisión humana.

_Última actualización: `2026-04-25`._
