# Flujo Escritorio -> Orange Pi

## Objetivo
Definir el flujo tecnico normal entre el workspace principal de escritorio y el nodo edge en Orange Pi sin ambiguedad operativa.

## Principio
- El cambio nace, se edita y se valida primero en el nodo `desktop_workspace`.
- La Orange Pi recibe el repositorio por Git en `/srv/tesis/repo` como clon operativo.
- La Orange Pi ejecuta validacion edge, runtime y observabilidad local.
- El retorno hacia `desktop_workspace` ocurre por logs, metricas y evidencia edge, no por mover la autoria principal al nodo edge.

## Secuencia normal
1. En escritorio, editar fuentes canonicas y ejecutar `python3 07_scripts/build_all.py`.
2. En escritorio, sincronizar el cambio del repo soberano con `python3 07_scripts/tesis.py sync --message "..." --step-id validación humana interna no pública`.
3. En Orange Pi, actualizar el clon operativo con `bash /srv/tesis/repo/ops/actualizacion/sync_repo_desde_desktop.sh repo+postcheck`.
4. En Orange Pi, revisar estado edge:
   - `systemctl status edge-iot-worker.service`
   - `bash /srv/tesis/repo/ops/edge/edge-iot-healthcheck.sh`
   - `bash /srv/tesis/repo/ops/edge/edge-iot-resilience.sh status`
5. Recuperar hacia escritorio la evidencia relevante desde:
   - `/srv/tesis/intercambio/edge/outbox`
   - `/srv/tesis/intercambio/edge/spool`
   - `/var/log/edge-iot`
6. Registrar en decision, bitacora o backlog cualquier hallazgo que cambie arquitectura, operacion o criterio de despliegue.

## Canales permitidos
- Git hacia `/srv/tesis/repo` con `pull --ff-only`.
- Contratos de datos y artefactos generados que el edge deba consumir explicitamente.
- Evidencia operativa de retorno por logs, outbox y spool del dominio `edge_iot`.

## Perfiles de sincronizacion
- `repo-only`: actualiza `/srv/tesis/repo` con `fetch + checkout + pull --ff-only` sin tocar runtime.
- `repo+postcheck`: perfil recomendado por defecto; actualiza repo, ejecuta `python3 07_scripts/tesis.py audit --check` y `bash bootstrap/orangepi/90_postcheck.sh`.
- `repo+restart-edge`: usa el mismo recorrido del perfil anterior y ademas reinicia `edge-iot-worker.service`.

## Cuando usar cada perfil
- Usar `repo-only` cuando solo se necesita dejar el clon operativo alineado para inspeccion, diff o preparacion local.
- Usar `repo+postcheck` para el flujo normal despues de promover cambios desde el escritorio.
- Usar `repo+restart-edge` cuando el cambio afecta el runtime `edge_iot`, wrappers, unidades systemd o comportamiento del servicio.

## Prohibiciones operativas
- No editar en Orange Pi la arquitectura principal como flujo normal.
- No usar un workspace montado por red como sustituto del repo soberano del escritorio.
- No corregir a mano artefactos generados en Orange Pi para despues tratarlos como fuente canonica.
- No hacer `git pull` con merge implicito en el clon operativo edge.

## Rutas clave
- Repo edge: `/srv/tesis/repo`
- Workspace runtime edge: `/srv/tesis/workspace/edge`
- Intercambio edge: `/srv/tesis/intercambio/edge`
- Logs edge: `/var/log/edge-iot`

## Criterio de uso
- Si el trabajo es de tesis, documentacion, analisis o decisiones: escritorio.
- Si el trabajo es de servicio, healthcheck, resiliencia, logs o pruebas locales del stack IoT: Orange Pi.
- Si el cambio no toca runtime edge: `repo-only` o `repo+postcheck` segun el nivel de verificacion requerido.
- Si el cambio toca runtime edge: `repo+restart-edge` con recuperacion posterior de logs y evidencia.

_Última actualización: `2026-04-13`._
