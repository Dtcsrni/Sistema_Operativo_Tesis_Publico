# Espacio de Trabajo Local de OpenClaw

## Objetivo
Ofrecer una superficie híbrida CLI + web para operar `openclaw` en Orange Pi sin convertirlo en prerrequisito del sistema.

## Flujo mínimo
1. Ejecutar `python runtime/openclaw/bin/openclaw_local.py doctor`.
2. Registrar una tarea con `tarea nueva` o evaluarla con `tarea enrutar`.
3. Correr `ejecutar --simulacion` para generar evidencia y, si corresponde, solicitud de aprobación.
4. Revisar aprobaciones pendientes.
5. Levantar la pasarela local con `pasarela servir` cuando existan dependencias web instaladas.
6. Verificar readiness local con `proveedor estado`, `proveedor medir`, `secretos estado`, `presupuesto estado`, `pasarela preflight` y `pasarela estado`.

## Serena MCP en OpenClaw
- `OpenClaw` consume `serena-local` como capacidad auxiliar de contexto y gobernanza; no participa en el `provider_registry` ni reemplaza el ruteo de modelos.
- Cuando una tarea tiene `target_paths`, contexto documental, riesgo alto o modo académico, el CLI intenta usar Serena automáticamente.
- La salida JSON de `tarea nueva`, `tarea enrutar`, `ejecutar` y `academico ...` incluye un bloque `serena` con disponibilidad, herramientas invocadas, referencias recuperadas y resultado de preflight.
- Si Serena no está disponible, `OpenClaw` degrada solo en flujos de lectura o `--simulacion`; cuando Serena es obligatoria o la operación pretende mutar artefactos, el comando falla con estado explícito.
- Si `governance.preflight` devuelve `blocked`, el bloqueo se conserva en la salida y se anota también en el resumen de aprobación humana.
- Este adapter no vuelve accesible a Serena para cualquier chat externo por defecto; el host o runtime que quiera invocarlo debe registrar el MCP o consumir un bridge explicito.

## Configuración del adapter Serena
- `OPENCLAW_SERENA_ENABLED=1|0`: activa o desactiva la heurística automática.
- `OPENCLAW_SERENA_MODE=auto|required|off`: política por defecto del adapter interno.
- `OPENCLAW_SERENA_TRANSPORT=http|stdio`: transporte preferido del cliente interno.
- `OPENCLAW_SERENA_URL=http://127.0.0.1:8765/mcp`: endpoint HTTP cuando se usa `http`.
- `OPENCLAW_SERENA_SCRIPT=/ruta/a/07_scripts/serena_mcp.py`: script local cuando se usa `stdio`.
- `OPENCLAW_SERENA_PYTHON=/ruta/a/python`: intérprete para lanzar `serena_mcp.py`.
- `OPENCLAW_SERENA_TIMEOUT_MS=4000`: timeout por llamada.
- Por comando, `--modo-serena auto|required|off` permite exigir Serena, apagarla o dejar la heurística por defecto.
- Para diagnostico rapido del host local fuera de OpenClaw, usar `python 07_scripts/check_serena_access.py`.

## Flujos académicos v1
- `python runtime/openclaw/bin/openclaw_local.py academico estado-del-arte --id-tarea ... --archivo-entrada-json <archivo.json>`
- `python runtime/openclaw/bin/openclaw_local.py academico metodologia --id-tarea ... --archivo-entrada-json <archivo.json>`
- `python runtime/openclaw/bin/openclaw_local.py academico redaccion --id-tarea ... --archivo-entrada-json <archivo.json> --escribir-artefactos`
- `python runtime/openclaw/bin/openclaw_local.py academico exportar-propuesta --id-tarea ...`

## Observabilidad local
- Log de servicio: `/var/log/openclaw/openclaw-gateway.log`
- Métricas de dominio: `/var/lib/node_exporter/textfile_collector/openclaw.prom`
- Scraping local vía `node_exporter` en `127.0.0.1:9100`
- `Prometheus` vive en `127.0.0.1:9090` y retiene 90 días en esta fase.

## Despliegue local en Orange Pi
- El entorno efectivo se instala en `/etc/tesis-os/openclaw.env`.
- Los secretos por dominio viven en `/etc/tesis-os/domains/`.
- El estado local vive en `/var/lib/herramientas/openclaw`.
- El cache local vive en `/var/cache/herramientas/openclaw`.
- Los logs operativos viven en `/var/log/openclaw`.
- El intercambio con otros dominios vive solo en `/srv/tesis/intercambio/openclaw`.
- El runtime principal es `Ollama`; la vía `RKLLM`/`RKNN-LLM` se instala como carril experimental secundario.
- `pasarela preflight` debe pasar antes de habilitar `openclaw-gateway.service`.

## Aislamiento T-030
- `openclaw-gateway.service` corre bajo `openclaw:openclaw`.
- `openclaw` no comparte SQLite, cache ni logs con `sistema_tesis` ni `edge_iot`.
- `openclaw` no expone API interdominio; solo escucha en `localhost`.
- Toda entrega a `sistema_tesis` sale por drafts, spool local o CLI explícita.

## Secretos y presupuesto
- `python runtime/openclaw/bin/openclaw_local.py secretos estado` reporta dominios, proveedores permitidos y faltantes sin exponer valores.
- `python runtime/openclaw/bin/openclaw_local.py presupuesto estado` consolida snapshot global y gasto local de `openclaw`.
- `python runtime/openclaw/bin/openclaw_local.py presupuesto simular --dominio academico --proveedor gemini_api` permite validar degradación antes de ejecutar una tarea.
- Las sesiones `gemini_web_assisted` y `chatgpt_plus_web_assisted` se clasifican como supervisadas por humano y usan costo estimado/manual.

## Gate humano
- Toda mutación de estado, publicación o cambio de arquitectura exige aprobación humana.
- La salida de `openclaw` se considera propuesta operativa hasta revisión humana.
- La evidencia fuente y el `Step ID` se preservan fuera de la cola automática.

_Última actualización: `2026-04-14`._
