# Modelo de Amenazas de OpenClaw

## Objetivo
Definir los riesgos principales de `openclaw` como plano de control asistivo multicloud y los controles mínimos exigidos en `tesis-os`.

## Riesgos principales
- Fuga de secretos por impresión accidental en CLI, logs, dashboard o artefactos exportados.
- Mezcla de dominios al usar credenciales o sesiones de `personal`, `profesional`, `academico`, `edge` y `administrativo`.
- Publicación accidental de evidencia privada, hashes internos, rutas privadas o identificadores sensibles.
- Escalación a nube en dominios prohibidos o fuera de presupuesto.
- Sobregasto por bucles de ruteo, reintentos o fallback mal diseñado.
- Confusión entre sesión web asistida supervisada y telemetría exacta de API.

## Controles v1
- `EnvironmentFile` por dominio en `/etc/tesis-os/domains/`.
- `doctor`, `secretos estado` y `presupuesto estado` reportan presencia/ausencia y estado, nunca valores.
- `edge` y `administrativo` quedan en modo local por default.
- `personal` no comparte credenciales con `academico` ni `profesional`.
- Toda sesión web asistida se clasifica como `human_supervised_web_session`.
- Toda exportación pública exige redacción estricta de secretos, rutas privadas, hashes internos y referencias sensibles.
- El agotamiento presupuestal degrada a `local`, `offline` o `manual` antes de permitir nube.

## Riesgos residuales
- Error humano al cargar credenciales en un archivo de dominio incorrecto.
- Estimaciones incompletas de costo en flujos web asistidos.
- Dependencia de snapshots de presupuesto si el proveedor no ofrece telemetría exacta inmediata.

## Endurecimiento siguiente
- Rotación operativa de credenciales por dominio.
- Migración opcional a un resolver compatible con vault sin romper la CLI ni los wrappers.
- Reglas de publicación más finas por tipo de evidencia y tipo de artefacto.

_Última actualización: `2026-04-25`._
