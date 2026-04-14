# Operación Serena MCP con Codex en VS Code

## Proposito

Definir como operar Serena MCP desde VS Code con Codex sin perder soberania humana, trazabilidad ni claridad sobre la raiz real del workspace.

## Arquitectura operativa

- **Host:** VS Code con Codex.
- **Transporte recomendado en Windows local:** MCP por Streamable HTTP sobre `http://127.0.0.1:8765/mcp`.
- **Transporte alterno:** `stdio`, conservado para pruebas y otros hosts.
- **Raiz efectiva:** `${workspaceFolder}`.
- **Adaptador MCP:** `07_scripts/serena_mcp.py`.
- **Gobernanza y permisos:** `07_scripts/serena_policy.py`.
- **Ejecucion de operaciones:** `07_scripts/serena_core.py`.
- **Configuracion del servidor:** `00_sistema_tesis/config/serena_mcp.json`.
- **Integracion del workspace:** `.vscode/mcp.json`.
- **Wrappers locales Windows:** `.vscode/serena-http.cmd` y `.vscode/serena-local-py.cmd`.

Serena MCP no reemplaza `tesis.py` ni `ab_pilot.py`. Su funcion es exponer herramientas compactas y auditables para que Codex opere con menos contexto repetido y con enforcement explicito.
Adicionalmente, `OpenClaw` lo consume ahora como adapter interno de contexto/gobernanza, sin incorporarlo al ruteo de proveedores de inferencia.

## Contrato común para hosts/agentes

- `serena-local` se mantiene como nombre lógico común para hosts MCP compatibles.
- `serena-local-py` se admite como alias operativo local del host Codex para fallback y diagnóstico por `stdio`.
- La plantilla mínima de conexión compartida vive en `docs/03_operacion/serena-mcp-host-template.json`.
- El contrato reutilizable para agentes externos e internos está documentado en `00_sistema_tesis/documentacion_sistema/contrato_serena_mcp_agentes.md`.
- En esta fase, Copilot y Antigravity se consideran consumidores potenciales del mismo contrato MCP, sin assets específicos por host.

## Perfiles MCP del workspace

- `serena-local`: perfil recomendado y activo del workspace para el endpoint HTTP local `http://127.0.0.1:8765/mcp`. La tarea `Serena MCP HTTP` queda configurada con autoarranque al abrir la carpeta para que Serena permanezca disponible durante el trabajo agéntico normal.
- `serena-local-py`: wrapper y ruta de diagnóstico por `stdio`, conservado en el repo pero deshabilitado temporalmente en `.vscode/mcp.json` por incompatibilidad práctica con `LocalProcess` de VS Code `1.115.0`.
- El contrato lógico del servidor sigue siendo `serena-local`; `serena-local-py` no redefine herramientas, gobernanza ni `serverInfo.name`.

## Bridge para runtimes externos

- El repo incorpora un bridge HTTP autenticado en `runtime/serena_bridge/bin/serena_bridge.py`.
- El bridge reutiliza `SerenaMCPServer` y no redefine el contrato ni las reglas de gobernanza.
- Endpoint por defecto: `http://127.0.0.1:8766/mcp/serena`.
- Token requerido por defecto: variable `SERENA_BRIDGE_BEARER_TOKEN`.
- Los hosts externos deben enviar headers de identidad para que la traza distinga `host_kind=external_runtime`.
- VS Code no necesita este bridge para operar localmente; su uso principal es exponer Serena a runtimes separados del host.

## Limite entre host y runtime

- VS Code puede cargar los perfiles MCP publicados en `.vscode/mcp.json`.
- En el estado actual del workspace (`2026-04-12`), VS Code expone solo `serena-local` por HTTP con autoarranque del task local.
- Esta conversacion no hereda automaticamente los servidores MCP personalizados que viva dentro del host VS Code.
- Que `serena-local-py` aparezca habilitado en la UI de VS Code no implica que el runtime del chat lo exponga como namespace o tool nativa.
- Si se requiere acceso desde este chat, hace falta una de estas rutas:
  1. que el runtime del chat permita registrar un MCP externo y apunte al mismo servidor local;
  2. que exista un bridge HTTP que reexporte `serena-local` hacia el runtime del chat;
  3. o usar VS Code como superficie principal para invocar Serena y este chat como apoyo sobre filesystem.

## Herramientas visibles en el host

El host debe ver exactamente estas herramientas publicadas con `_` en el nombre para compatibilidad con VS Code `1.115.0`:

1. `context_fetch_compact`
2. `governance_preflight`
3. `artifacts_evaluate_serena`
4. `artifacts_write_derived`
5. `canon_prepare_change`
6. `canon_apply_controlled_change`
7. `trace_append_operation`

Internamente Serena conserva los nombres canónicos con puntos para traza, política y compatibilidad de clientes; el servidor acepta llamadas tanto con `_` como con `.`.

## Checklist E2E de aceptacion humana

1. Abrir el repositorio en la raiz correcta del workspace.
2. Confirmar que `.vscode/mcp.json` exista y que `SISTEMA_TESIS_ROOT` apunte a `${workspaceFolder}`.
3. Confirmar o permitir el autoarranque de la tarea `Serena MCP HTTP` para levantar el servidor local en `127.0.0.1:8765`.
4. Confirmar que `.vscode/mcp.json` apunte a `http://127.0.0.1:8765/mcp`.
5. Ejecutar `Developer: Reload Window` en VS Code.
6. Aceptar la ejecución automática de tareas del workspace si VS Code la solicita (o fijar `"task.allowAutomaticTasks": "on"` en `.vscode/settings.json`).
7. Abrir el panel MCP o la superficie de herramientas del host Codex.
8. Confirmar que aparezca `serena-local` sin error de arranque.
9. Confirmar que el host liste las 7 herramientas visibles en `serena-local`.
10. Si se reactiva `serena-local-py` para diagnóstico, tratarlo solo como ruta auxiliar y no como requisito E2E del workspace.
11. Ejecutar `context_fetch_compact` con una consulta de solo lectura.
12. Ejecutar `governance_preflight` sobre una ruta canónica o protegida.
13. Confirmar que exista o se actualice `historial interno no público/serena_mcp_operations.jsonl`.
14. Si el servidor no responde al `initialize`, revisar `historial interno no público/serena_mcp_debug.log`.
15. Ejecutar `python 07_scripts/check_serena_access.py` para verificar que `serena-local` siga disponible y recomendado, y para recordar la frontera entre host y runtime.
16. Si se requiere un runtime externo, exportar `SERENA_BRIDGE_BEARER_TOKEN` y arrancar `python runtime/serena_bridge/bin/serena_bridge.py`.

## Prueba minima recomendada

### Consulta compacta

- Tool: `context_fetch_compact`
- `query`: `DEC-0022`
- `paths`:
  - `00_sistema_tesis/decisiones/2026-04-08_DEC-0022_arquitectura_operativa_escritorio_primario_y_orange_pi_edge.md`

Resultado esperado:

- `status: ok`
- `write_scope: read_only`
- al menos una coincidencia en `matches`
- referencia explicita al archivo consultado

### Preflight de gobernanza

- Tool: `governance_preflight`
- `tool_name`: `canon.apply_controlled_change`
- `target_paths`:
  - `00_sistema_tesis/decisiones/2026-04-08_DEC-0022_arquitectura_operativa_escritorio_primario_y_orange_pi_edge.md`

Resultado esperado:

- respuesta estructurada con `status`, `risk_level`, `write_scope`, `evidence` y `next_required_action`
- si no se incluye `step_id`, la respuesta debe bloquear el cambio o marcarlo como pendiente de validacion humana

## Flujo corto Codex + Serena MCP

1. `context_fetch_compact` para ubicar contexto relevante sin abrir documentos completos.
2. `governance_preflight` para validar intencion, riesgo y requisitos.
3. `canon_prepare_change` para revisar diff y hashes antes de tocar canon.
4. `canon_apply_controlled_change` solo cuando exista validación humana interna no pública vigente y evidencia fuente corroborada si aplica.
5. `python 07_scripts/build_all.py` para auditoria posterior.

## Regla de interpretacion

- Si VS Code muestra `serena-local`, las 7 tools y una traza nueva en JSONL, la integracion E2E se considera operativa.
- Si además se reactiva `serena-local-py` y muestra las mismas 7 tools, el diagnóstico por `stdio` se considera operativo, pero no es requisito para el workspace actual.
- Si solo existe `.vscode/mcp.json`, la integracion esta declarada pero no validada en uso real.
- En Windows con host local, el launcher recomendado para uso bajo demanda es una tarea de VS Code que ejecute `.vscode/serena-http.cmd`.
- `serena-local-py` no redefine el contrato MCP; solo ofrece una ruta opcional de diagnóstico al mismo servidor lógico cuando se habilita manualmente.
- Si hay espera infinita durante `initialize`, el archivo `serena_mcp_debug.log` debe indicar si el proceso arrancó, leyó el mensaje y escribió respuesta.
- `serena_mcp_debug.log` y `serena_mcp_debug_http_check.log` son artefactos diagnósticos locales; sirven para depuración y no deben tratarse como evidencia principal de publicación.
- Los archivos `serena_http_probe_*`, `serena_compare_*` y `serena_write_probe_*` en `audit_history/` se consideran sondas temporales salvo que una validación humana los promueva explícitamente a evidencia canónica.

## Recuperacion rapida

1. Ejecutar `Developer: Reload Window`.
2. Confirmar trust del servidor MCP si VS Code lo solicita.
3. Verificar `MCP: List Servers` y comprobar que `serena-local` siga visible como perfil activo.
4. Correr `python 07_scripts/check_serena_access.py`.
5. Si `serena-local` falla por HTTP, primero recargar la ventana o relanzar la tarea `Serena MCP HTTP`; si `check_serena_access.py` muestra `stdio` sano pero no expuesto, tratar `serena-local-py` solo como diagnóstico local o reactivarlo manualmente bajo decisión explícita.
6. Si el host sigue sin ver tools MCP aunque HTTP responda bien, asumir primero una limitacion del host/runtime antes que un fallo de negocio en Serena.
7. Si un host externo no puede registrar `127.0.0.1`, desplegar el bridge detras de un tunel o reverse proxy con auth y registrar esa URL publica.

_Última actualización: `2026-04-14`._
