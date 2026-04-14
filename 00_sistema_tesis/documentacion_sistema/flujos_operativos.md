# Flujos operativos

## Flujo 1. Retomar el sistema

Objetivo: volver a entender el estado actual en pocos minutos.

Secuencia:

1. Leer `README_INICIO.md`.
2. Revisar `00_sistema_tesis/manual_operacion_humana.md`.
3. Ejecutar `python 07_scripts/tesis.py status`.
4. Ejecutar `python 07_scripts/tesis.py next`.
5. Si hace falta, ejecutar `python 07_scripts/tesis.py doctor`.

Salida esperada:

- entender que es el sistema;
- identificar bloque activo, siguiente entregable y riesgos;
- saber que modulo o archivo tocar despues.

## Flujo 2. Registrar un cambio o una decision

Objetivo: incorporar trabajo nuevo sin romper soberania ni trazabilidad.

Secuencia:

1. Editar la fuente canonica correcta.
2. Si el cambio afecta arquitectura, metodo, evidencia o gobernanza, registrar decision o bitacora.
3. Si corresponde a una instruccion humana critica, vincularla a `VAL-STEP`.
4. Si el `VAL-STEP` es nuevo y esta por encima del umbral de enforcement, registrar primero la evidencia fuente de conversacion.
5. Regenerar y auditar artefactos derivados.

Salida esperada:

- cambio explicado desde su fuente de verdad;
- soporte humano verificable;
- proyecciones sincronizadas.

## Flujo 3. Auditar el estado del sistema

Objetivo: comprobar integridad, consistencia y operabilidad.

Secuencia:

1. Ejecutar `python 07_scripts/tesis.py audit --check`.
2. Ejecutar `python 07_scripts/tesis.py source status --check`.
3. Ejecutar `python 07_scripts/build_all.py`.
4. Revisar wiki y dashboard generados si se requiere lectura humana rapida.

Salida esperada:

- estado de integridad del sistema;
- estado de evidencia fuente;
- estado de salida publica y artefactos derivados.

## Flujo 4. Publicar la superficie publica

Objetivo: exponer una vista tecnica evaluable sin abrir la base privada.

Secuencia:

1. Confirmar que la base privada ya paso auditorias.
2. Ejecutar `python 07_scripts/tesis.py publish --build`.
3. Revisar `06_dashboard/publico/index.md` y `manifest_publico.json`.
4. Validar que no haya rutas privadas, hashes o referencias internas prohibidas.

Salida esperada:

- bundle publico regenerado;
- narrativa tecnica clara para terceros;
- sanitizacion intacta.

## Flujo 5. Consultar el sistema desde la capa publica

Objetivo: permitir que terceros entiendan y evalúen sin editar ni acceder a lo privado.

Secuencia:

1. Abrir el indice publico.
2. Leer la pagina de sistema para entender proposito, modulos y limites.
3. Recorrer wiki y dashboard para revisar planeacion, gobernanza, estado y cobertura.
4. Usar la informacion para evaluar consistencia, madurez y direccion del proyecto.

Salida esperada:

- comprension tecnica suficiente para evaluacion externa;
- claridad sobre que informacion es publica y que informacion permanece interna.

## Flujo 6. Operar por dominios aislados

Objetivo: ejecutar tareas en Orange Pi sin mezclar permisos, red ni datos entre `sistema_tesis`, `openclaw` y `edge_iot`.

Secuencia:

1. Verificar identidad y servicio del dominio objetivo.
2. Confirmar rutas permitidas de lectura y escritura.
3. Confirmar si el dominio tiene red local, salida controlada o modo sin nube.
4. Si hay intercambio con otro dominio, usar solo `inbox`, `outbox`, `spool` o CLI explícita.
5. Ejecutar chequeos del dominio antes de operar componentes opcionales.

Salida esperada:

- servicio corriendo bajo la identidad correcta;
- sin acceso cruzado a workspaces ni secretos;
- intercambio trazable y reproducible.

## Flujo 7. Observar salud y métricas por dominio

Objetivo: revisar salud operativa sin mezclar logs ni métricas entre dominios.

Secuencia:

1. Verificar `prometheus.service`, `prometheus-node-exporter.service` y `tesis-observabilidad-collector.timer`.
2. Confirmar que cada dominio escribe en su ruta de logs propia.
3. Validar los archivos `.prom` en `/var/lib/node_exporter/textfile_collector`.
4. Ejecutar `bash tests/smoke/test_observability_stack.sh` cuando se requiera postcheck manual.
5. Revisar rotación y compresión en `/etc/logrotate.d/tesis-observabilidad`.

Salida esperada:

- observabilidad local funcional;
- métricas separadas por dominio;
- retención larga operable;
- sin exposición fuera de `localhost`.

## Flujo 8. Recuperar `edge_iot` tras degradación o cuarentena

Objetivo: inspeccionar y recuperar el dominio `edge_iot` sin romper el aislamiento.

Secuencia:

1. Verificar `systemctl status edge-iot-worker.service` y `systemctl status edge-iot-watchdog.timer`.
2. Revisar `bash /srv/tesis/repo/ops/edge/edge-iot-resilience.sh status`.
3. Leer `edge-iot-worker.log`, `edge-iot-watchdog.log` y `edge-iot-resilience.log`.
4. Si el dominio está en `degraded_offline`, revisar causa externa y esperar o forzar reintento según criterio humano.
5. Si el dominio está en `quarantined`, corregir la causa y ejecutar limpieza explícita de cuarentena.

Salida esperada:

- causa de degradación identificada;
- reintento o desbloqueo humano trazable;
- sin bucles infinitos de reinicio.

## Flujo 9. Respaldar y restaurar por dominio

Objetivo: proteger y validar recuperación de `sistema_tesis`, `openclaw` y `edge_iot` sin mezclar sus rutas.

Secuencia:

1. Ejecutar `bash /srv/tesis/repo/ops/respaldo/ejecutar_respaldo.sh`.
2. Verificar checksum y manifiestos con `bash /srv/tesis/repo/ops/respaldo/verificar_respaldos.sh`.
3. Restaurar cada dominio a sandbox con `ops/recuperacion/restaurar_desde_emmc.sh --mode sandbox`.
4. Revisar el reporte consolidado de restauración.
5. Usar `in_place` solo con bandera explícita y durante ventana controlada.

Salida esperada:

- artefactos independientes por dominio;
- snapshots locales por dominio;
- restore validado sin tocar el runtime activo;
- procedimiento in-place trazable y controlado.

## Flujo 10. Auditar integración segura entre dominios

Objetivo: demostrar que los canales declarados funcionan y que los accesos internos no autorizados fallan.

Secuencia:

1. Ejecutar `bash tests/smoke/test_domain_integration_security.sh`.
2. Ejecutar `bash ops/seguridad/validar_integracion_entre_dominios.sh` para consolidar evidencia administrativa.
3. Confirmar que `archivo_draft`, `spool_local` y `cli_explicita` pasan.
4. Confirmar que fallan accesos a rutas, secretos y SQLite de otros dominios.
5. Confirmar que cualquier intento de HTTP interdominio falla.
6. Revisar `/var/log/tesis-admin/domain_integration_security_report_<timestamp>.log` como evidencia operativa.

Salida esperada:

- canales permitidos funcionando;
- accesos cruzados bloqueados;
- evidencia reproducible de enforcement real.

## Flujo 11. Trabajar con Codex asistido por Serena MCP

Objetivo: operar tareas de tesis con contexto compacto y acciones auditables desde VS Code sin sustituir la validacion humana ni la via CLI.

Secuencia:

1. Abrir el repositorio en la raiz correcta del workspace.
2. Recargar VS Code y confirmar que `serena-local` aparezca como servidor MCP activo.
3. Usar `context.fetch_compact` para recuperar solo el contexto minimo necesario.
4. Usar `governance.preflight` antes de preparar o aplicar cambios sobre canon o rutas protegidas.
5. Usar `canon.prepare_change` para revisar diff, riesgo y requisitos antes de tocar la fuente canonica.
6. Usar `canon.apply_controlled_change` solo con `VAL-STEP` valido y evidencia fuente corroborada cuando la politica lo exija.
7. Ejecutar `python 07_scripts/build_all.py` despues de cambios relevantes.

Salida esperada:

- contexto reducido sin perder referencias de origen;
- cambios guiados por gobernanza y no por memoria implicita del agente;
- traza MCP visible en `historial interno no público/serena_mcp_operations.jsonl`.

Referencia operativa: `00_sistema_tesis/documentacion_sistema/operacion_serena_mcp_codex.md`

## Flujo 12. Registrar Serena para un runtime externo

Objetivo: exponer Serena como MCP HTTP autenticado para un host separado de VS Code sin duplicar reglas de negocio.

Secuencia:

1. Definir `SERENA_BRIDGE_BEARER_TOKEN` en el entorno del host.
2. Arrancar `python runtime/serena_bridge/bin/serena_bridge.py`.
3. Verificar con `python 07_scripts/check_serena_access.py` que el bridge sea alcanzable.
4. Registrar la URL del bridge en el host externo con auth `Bearer` y headers de identidad.
5. Ejecutar `initialize`, `tools/list`, `context.fetch_compact` y `governance.preflight`.
6. Confirmar que la traza MCP incluya identidad del host y `host_kind=external_runtime`.

Salida esperada:

- runtime externo consumiendo el mismo contrato `serena-local`;
- auth minima activa;
- misma gobernanza que el MCP local;
- traza diferenciada del host llamador.

## Regla transversal

Todo flujo del sistema debe cumplir tres condiciones:

- tener una fuente canonica identificable;
- tener una salida humana legible;
- poder distinguir entre superficie canónica no pública y superficie publica.

_Última actualización: `2026-04-14`._
