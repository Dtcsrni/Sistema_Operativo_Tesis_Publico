# Especificacion Operativa de Mission Control

## Estado actual

Mission Control vive en `04_implementacion/control_mission/` y se expone en el stack principal como `centro-control-misiones` en el puerto `4000`. El dashboard consume el gateway de OpenClaw por `OPENCLAW_GATEWAY_URL` y la persistencia principal sigue siendo SQLite local en `04_implementacion/control_mission/mission-control.db`.

## Casos de uso

- Supervisar tareas, aprobaciones y actividad del agente en tiempo casi real.
- Revisar y resolver aprobaciones humanas antes de ejecuciones sensibles.
- Consultar trazabilidad de sesiones, decisiones de ruteo y progreso de tareas.
- Operar como panel de control local-first para OpenClaw sin depender de SaaS externo para el flujo base.

## Especificacion minima

- La configuracion sensible no debe quedar inline en `docker-compose.yml`; debe entrar por `env_file` o variables de entorno del host.
- El gateway de OpenClaw debe ser alcanzable desde el contenedor de Mission Control sin reescribir la red ni duplicar el secreto en el compose.
- La base de datos de Mission Control debe tener un unico origen de verdad por despliegue.
- El panel debe responder con estado de salud claro y fallar de forma explicita si no puede ver OpenClaw o su propia base de datos.
- El modelo de despliegue debe conservar separacion entre runtime de OpenClaw, panel web y persistencia.

## Recomendaciones de mejor practica

- Mantener el token del gateway solo en `config/env/openclaw.env` y en el entorno de despliegue real.
- Preferir rutas declarativas en el compose y evitar defaults secretos embebidos.
- Documentar cualquier cambio de contrato entre OpenClaw y Mission Control junto con su prueba de humo.
- Si se agrega telemetria nueva, primero formalizar el contrato y luego conectar la UI.

_Última actualización: `2026-05-15`._
