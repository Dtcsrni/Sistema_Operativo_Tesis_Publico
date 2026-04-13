# Mapa de Interconexiones

## Bloques
- `desktop_workspace` en Windows 11 con VS Code para autoria, analisis y administracion del repo soberano.
- Orange Pi 5 Plus como nodo base y clon operativo del sistema de tesis en `/srv/tesis/repo`.
- Nodo edge y perifericos como dominio separado.
- Herramientas asistivas como OpenClaw en capa opcional desacoplada.

## Canales de datos
- `desktop_workspace -> /srv/tesis/repo`: sincronizacion Git del repo canonico con `pull --ff-only`.
- `desktop_workspace -> edge_iot`: contratos y artefactos explicitamente necesarios para despliegue o validacion.
- `orange_pi_edge -> desktop_workspace`: logs, metricas, `outbox` y `spool` del dominio `edge_iot`.
- Entre dominios locales de Orange Pi, el intercambio sigue limitado a `/srv/tesis/intercambio/...`.

## Perfiles operativos edge
- `repo-only`: alineacion del clon operativo sin tocar servicios.
- `repo+postcheck`: alineacion del clon mas validacion edge local.
- `repo+restart-edge`: alineacion del clon, validacion edge y reinicio controlado de `edge-iot-worker.service`.

## Regla
Toda conexion electrica y de datos debe validarse contra datasheet y checklist pre-energizacion.

_Última actualización: `2026-04-13`._
