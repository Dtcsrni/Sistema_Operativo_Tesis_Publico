---
title: "T-034 Resiliencia edge_iot"
date: 2026-05-22
category: enhancement
status: closed
owner: "Tesista Principal / HOA"
decisions: ["DEC-0046"]
step_id: "validación humana interna no pública"
trace_status: "validado"
---

# T-034 Resiliencia edge_iot

## Objetivo

Implementar rutinas de watchdog y mecanismos de auto-recuperacion ante fallos (auto-recovery)
para los servicios del dominio `edge_iot`. Esto permitira que el nodo Edge sobreviva
a errores transitorios de contenedores, interrupciones de NPU o caidas de conexion,
reiniciando los servicios degradados y aplicando cuarentena ante bucles de fallo.

## Alcance

- **Incluye:**
  - Adaptacion del script `ops/edge/edge-iot-watchdog.sh` para operar sobre `siot-edge.service` (stack Docker)
    en lugar del obsoleto `edge-iot-worker.service`.
  - Actualizacion de `config/systemd/edge-iot-watchdog.service` para correr bajo el usuario `edge_ops` y 
    verificar los contenedores gestionados por Docker Compose.
  - Comprobacion de salud (healthcheck) de contenedores Docker (especialmente del gateway y el sincronizador).
  - Limpieza de `config/systemd/edge-iot-worker.service`.
- **Excluye:**
  - Reemplazo del OTel Collector (ya hace telemetria en T-033). El watchdog asiste en la capa de SO (Systemd) 
    para tomar acciones curativas.

## Rutas Afectadas

- `ops/edge/edge-iot-watchdog.sh` [MODIFY]
- `config/systemd/edge-iot-watchdog.service` [MODIFY]
- `config/systemd/edge-iot-worker.service` [DELETE]
- `config/systemd/edge-iot-watchdog.timer` [MODIFY] (ajustar dependencias)

## Gates Publicos

- El watchdog no debe reiniciar el stack indefinidamente (respetar la politica de cuarentena).
- Los scripts no deben escribir fuera de las rutas de `edge_iot`.

## Pruebas y Aceptacion

- Verificacion manual deteniendo el contenedor de gateway y asegurando que el watchdog lo detecte y 
  reinicie el servicio `siot-edge`.

## Rollback

Restaurar la rama desde el ultimo commit. Deshabilitar `edge-iot-watchdog.timer`.

## Cierre de Trazabilidad

Validado formalmente en validación humana interna no pública. Se han realizado los siguientes cambios:
- Se eliminó el archivo obsoleto `config/systemd/edge-iot-worker.service`.
- Se actualizó el script `ops/edge/edge-iot-watchdog.sh` para monitorizar el estado y reiniciar `siot-edge.service`.
- Se actualizó la unidad `config/systemd/edge-iot-watchdog.service` para correr como el usuario `edge_ops` y ajustó sus rutas y dependencias.
- Se agregaron las variables de configuración del Watchdog al archivo `config/env/domains/edge.env.example`, definiendo explícitamente el uso de `docker inspect` en `EDGE_IOT_HEALTHCHECK_CMD`.



## FRE



## ESE

_Última actualización: `2026-06-01`._
