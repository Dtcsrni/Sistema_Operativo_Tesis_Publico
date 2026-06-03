---
title: "T-032 Servicios edge_iot"
date: 2026-05-21
category: enhancement
status: closed
owner: "Tesista Principal / HOA"
decisions: []
step_id: "validación humana interna no pública"
trace_status: "validado"
---

# T-032 Servicios edge_iot

## Objetivo

Configurar unidades de servicio en Systemd para orquestar la capa `edge_iot` garantizando encendido automÃ¡tico, monitorizaciÃ³n de salud (healthchecks), polÃ­ticas de reinicio y dependencias seguras con Docker y la red.

## Alcance

- **Incluye:**
  - CreaciÃ³n de la unidad `config/systemd/siot-edge.service`.
  - PolÃ­ticas de `Restart=always` y tiempos de gracia coherentes con el hardware Orange Pi (NPU, RAM).
  - Script autÃ³nomo de instalaciÃ³n `07_scripts/ops/install_edge_service.sh` que haga los enlaces simbÃ³licos en `/etc/systemd/system/` y habilite el servicio.
- **Excluye:**
  - Modificar las imÃ¡genes Docker en sÃ­; Ã©stas se asumen pre-construidas.
  - IntervenciÃ³n en el PC orquestador central.

## Rutas Afectadas

- `config/systemd/siot-edge.service` [NEW]
- `07_scripts/ops/install_edge_service.sh` [NEW]
- `07_scripts/ops/optimize_edge.sh` [NEW]

## Gates Publicos

- No debe sobreescribirse ni alterar servicios de `openclaw`.
- El script de instalaciÃ³n debe ser idempotente.
- El sistema de build `build_all.py` y verificaciones de SDD deben pasar sin errores.

## Pruebas y Aceptacion

- Despliegue manual en Orange Pi mediante `sudo bash 07_scripts/ops/install_edge_service.sh`.
- ComprobaciÃ³n vÃ­a `systemctl status siot-edge` y `journalctl -fu siot-edge` para observar el levantamiento exitoso de Docker Compose.

## Rollback

- Detener y deshabilitar `siot-edge.service` y remover el enlace simbÃ³lico de `/etc/systemd/system/`.

## Cierre de Trazabilidad

Validado formalmente en validación humana interna no pública. Se han creado los archivos:
- `config/systemd/siot-edge.service`: unidad Systemd que orquesta el stack Docker edge_iot.
- `07_scripts/ops/install_edge_service.sh`: script idempotente de instalacion en Orange Pi.
- `07_scripts/ops/optimize_edge.sh`: script de optimizacion de rendimiento (CPU, ZRAM, I/O, Docker).


## FRE



## ESE

_Última actualización: `2026-06-03`._
