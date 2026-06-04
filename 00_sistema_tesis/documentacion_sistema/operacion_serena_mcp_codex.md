# Operación MCP Agnóstica para Agentes Compatibles

## Proposito

Definir como operar Serena MCP y los perfiles Docker MCP desde cualquier host agéntico compatible sin perder soberania humana, trazabilidad ni claridad sobre la raiz real del workspace.

## Arquitectura operativa

- **Host:** cualquier cliente MCP compatible, por ejemplo Codex Desktop, Codex en VS Code, Antigravity, Antigravity IDE, Cursor, Continue, JetBrains u otro runtime con soporte MCP.
- **Plano de autoría/control:** el host agéntico conserva Git, Caveman, Serena HTTP, trazabilidad y `build_all.py` sobre la raiz real del repositorio.
- **Plano reproducible de servicios:** Docker Compose ejecuta servicios del PC Hub (`siot-docs`, `siot-agent`) sin reemplazar el workspace soberano.
- **Transporte recomendado en Windows local:** MCP por Streamable HTTP sobre `http://127.0.0.1:8765/mcp`.
- **Transporte alterno:** `stdio`, conservado para pruebas y hosts que no puedan consumir HTTP local.
- **Raiz efectiva:** `${workspaceFolder}`.
- **Adaptador MCP:** `07_scripts/serena_mcp.py`.
- **Gobernanza y permisos:** `07_scripts/serena_policy.py`.
- **Ejecucion de operaciones:** `07_scripts/serena_core.py`.
- **Configuracion del servidor:** `00_sistema_tesis/config/serena_mcp.json`.
- **Plantilla agnóstica de host:** `docs/03_operacion/mcp-agent-host-template.json`.
- **Implementacion local de referencia:** `.vscode/mcp.json`.
- **Wrappers locales Windows:** `.vscode/serena-http.cmd` y `.vscode/serena-local-py.cmd`; otros hosts pueden lanzar el mismo servidor por comando equivalente.

Serena MCP no reemplaza `tesis.py` ni `ab_pilot.py`. Su funcion es exponer herramientas compactas y auditables para que cualquier agente compatible opere con menos contexto repetido y con enforcement explicito.
Adicionalmente, `OpenClaw` lo consume ahora como adapter interno de contexto/gobernanza, sin incorporarlo al ruteo de proveedores de inferencia.

## Runtime hibrido WSL + Docker

- El host agéntico local es la superficie primaria de autoria, decisiones, Git, Serena, Caveman y cierre de auditoria.
- Docker es superficie de ejecucion reproducible para servicios, pruebas E2E y dependencias pesadas; no es la fuente de verdad del canon.
- Los bind mounts desde rutas Windows o montajes `/mnt/*` pueden degradar rendimiento; para cargas pesadas se debe medir primero o usar clon operativo en filesystem Linux/ext4, volumen nombrado o cache persistente.
- El canon no se mueve ni se convierte en volumen primario sin decision explicita y trazada.
- `docker-compose.yml` puede operar el PC Hub una vez formalizado DEC-0025 con validacion humana vigente; hasta entonces es infraestructura propuesta/implementada pendiente de cierre canonico.

## Caveman como modo base de agente

- Caveman no es un servidor MCP adicional: es el modo operativo conciso que debe estar disponible para cualquier agente de IA antes de entrar al trabajo tecnico.
- La comprobacion minima es `command -v caveman` seguido de `caveman --help`; si falla, el agente debe intentar restaurar la disponibilidad del wrapper o del bundle global antes de seguir.
- Cuando Caveman y Serena estan disponibles, la secuencia preferida es: Caveman como modo base de redaccion/ejecucion, Serena como primera capa de contexto compacto y gobernanza, y `build_all.py` como cierre de auditoria.
- Caveman no sustituye la disciplina de trazabilidad ni la politica de Serena; complementa la capa de contexto con un modo de trabajo mas directo y menos ruidoso.
- Para verificación operativa conjunta de sesión, usar `python3 07_scripts/check_agent_context_tools.py --attempt-start-http`.

## Contrato común para hosts/agentes

- `serena-local` se mantiene como nombre lógico común para hosts MCP compatibles.
- `serena-local-py` se admite como alias operativo local para fallback y diagnóstico por `stdio`.
- La plantilla mínima de conexión compartida vive en `docs/03_operacion/serena-mcp-host-template.json`.
- La plantilla agnóstica completa para Serena + perfiles Docker MCP vive en `docs/03_operacion/mcp-agent-host-template.json`.
- El contrato reutilizable para agentes externos e internos está documentado en `00_sistema_tesis/documentacion_sistema/contrato_serena_mcp_agentes.md`.
- Codex Desktop, Codex en VS Code, Antigravity, Antigravity IDE, Copilot, Cursor, Continue, JetBrains y otros clientes MCP se consideran consumidores equivalentes del mismo contrato. Ningun host redefine las reglas de negocio.

## Perfiles MCP del workspace

- `serena-local`: perfil recomendado y activo del workspace para el endpoint HTTP local `http://127.0.0.1:8765/mcp`. La tarea `Serena MCP HTTP` queda configurada con autoarranque al abrir la carpeta para que Serena permanezca disponible durante el trabajo agéntico normal.
- `serena-local-py`: wrapper y ruta de diagnóstico por `stdio`, conservado en el repo pero deshabilitado temporalmente en `.vscode/mcp.json` por incompatibilidad práctica con `LocalProcess` de VS Code `1.115.0`.
- El contrato lógico del servidor sigue siendo `serena-local`; `serena-local-py` no redefine herramientas, gobernanza ni `serverInfo.name`.
- `docker-mcp-architecture`: gateway Docker MCP por `stdio` sobre el perfil `siot-architecture`. Publica Context7, Sequential Thinking, GitHub en lectura, Fetch y Filesystem restringido al workspace para arquitectura, revisión y economía de tokens.
- `docker-mcp-runtime`: gateway Docker MCP por `stdio` sobre el perfil `siot-runtime`. Publica Fetch y Filesystem en modo lectura para inspección operativa de archivos del repo; las operaciones Docker reales siguen usando CLI/scripts locales hasta contar con un servidor Docker de inspección específico.
- `docker-mcp-accessibility`: gateway Docker MCP por `stdio` sobre el perfil `siot-accessibility`. Publica Playwright con herramientas de navegación, snapshot, consola, red, screenshot e interacción básica; `browser_run_code_unsafe` queda fuera del allowlist.
- `docker-mcp-observability`: gateway Docker MCP por `stdio` sobre el perfil `siot-observability`. Publica Grafana en modo consulta/lectura contra `http://127.0.0.1:3000` y Fetch; acciones mutantes de dashboards, alertas, incidentes o carpetas quedan fuera del allowlist.
- No se publica perfil Figma en este workspace. Si alguna superficie de diseño lo requiere, debe incorporarse mediante una decisión separada y trazada.

## Bridge para runtimes externos

- El repo incorpora un bridge HTTP autenticado en `runtime/serena_bridge/bin/serena_bridge.py`.
- El bridge reutiliza `SerenaMCPServer` y no redefine el contrato ni las reglas de gobernanza.
- Endpoint por defecto: `http://127.0.0.1:8766/mcp/serena`.
- Token requerido por defecto: variable `SERENA_BRIDGE_BEARER_TOKEN`.
- Los hosts externos deben enviar headers de identidad para que la traza distinga `host_kind=external_runtime`.
- Un host local que pueda registrar `http://127.0.0.1:8765/mcp` no necesita bridge. El bridge se usa cuando el runtime no hereda el localhost del agente, vive fuera del IDE o requiere endpoint autenticado.

## Limite entre host y runtime

- Cualquier host MCP puede registrar los perfiles publicados en `docs/03_operacion/mcp-agent-host-template.json`.
- `.vscode/mcp.json` es solo una implementacion local de referencia para VS Code; no es la fuente unica de verdad del contrato.
- En el estado actual del workspace (`2026-06-02`), el contrato publica `serena-local` por HTTP y cuatro gateways Docker MCP por `stdio`: `docker-mcp-architecture`, `docker-mcp-runtime`, `docker-mcp-accessibility` y `docker-mcp-observability`.
- Una conversación o runtime de chat no hereda automaticamente los servidores MCP de otro host. Debe registrar los mismos servidores, consumir el bridge o delegar la invocación MCP al host que sí los expone.
- Que un perfil exista en una configuracion de IDE no implica que otro runtime lo exponga como namespace o tool nativa.

## Herramientas visibles en el host

El host debe ver estas 29 herramientas publicadas con `_` en `tools/list` cuando el cliente normalice nombres MCP. Internamente Serena conserva nombres con `.` y acepta ambas formas en `tools/call`:

1. `context_fetch_compact`
2. `context_repo_map`
3. `context_fetch_changes`
4. `context_trace_lookup`
5. `context_session_brief`
6. `context_search_ranked`
7. `context_file_digest`
8. `context_symbol_index`
9. `context_dependency_map`
10. `context_related_paths`
11. `context_bundle`
12. `context_change_impact`
13. `context_todo_scan`
14. `memory_lookup`
15. `memory_session_recap`
16. `memory_derived_index`
17. `memory_evidence_digest`
18. `governance_preflight`
19. `governance_step_status`
20. `governance_trace_gap_scan`
21. `governance_protected_path_check`
22. `artifacts_evaluate_serena`
23. `artifacts_write_derived`
24. `artifacts_write_memory_derived`
25. `canon_prepare_change`
26. `canon_apply_controlled_change`
27. `canon_prepare_multi_change`
28. `canon_apply_multi_change`
29. `trace_append_operation`

Internamente Serena conserva los nombres canónicos con puntos para traza, política y compatibilidad de clientes; el servidor acepta llamadas tanto con `_` como con `.`.

## Checklist E2E de aceptacion humana

1. Abrir el repositorio en la raiz correcta del workspace.
2. Registrar en el host MCP la plantilla `docs/03_operacion/mcp-agent-host-template.json` o su equivalente adaptado al cliente.
3. Confirmar que `SISTEMA_TESIS_ROOT` apunte a la raiz real del repositorio.
4. Confirmar que `serena-local` apunte a `http://127.0.0.1:8765/mcp` o al bridge autenticado si el host no comparte localhost.
5. Reiniciar o recargar el host MCP segun su mecanismo propio.
6. Aceptar trust/autorizacion del servidor MCP si el host lo solicita.
7. Abrir el panel MCP o la superficie de herramientas del host agéntico.
8. Confirmar que aparezca `serena-local` sin error de arranque.
9. Confirmar que el host liste las 29 herramientas visibles en `serena-local`.
10. Si se reactiva `serena-local-py` para diagnóstico, tratarlo solo como ruta auxiliar y no como requisito E2E del workspace.
11. Ejecutar `context_fetch_compact` con una consulta de solo lectura.
12. Ejecutar `governance_preflight` sobre una ruta canónica o protegida.
13. Confirmar que exista o se actualice `historial interno no público/serena_mcp_operations.jsonl`.
14. Si el servidor no responde al `initialize`, revisar `historial interno no público/serena_mcp_debug.log`.
15. Ejecutar `python3 07_scripts/serena/check_serena_access.py --attempt-start-http` para verificar/recuperar `serena-local` y recordar la frontera entre host y runtime.
16. Ejecutar `python3 07_scripts/audit/check_agent_context_tools.py --attempt-start-http` para validar disponibilidad conjunta Caveman + Serena.
17. Si se requiere un runtime externo, exportar `SERENA_BRIDGE_BEARER_TOKEN` y arrancar `python runtime/serena_bridge/bin/serena_bridge.py`.

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

## Flujo corto agente + Serena MCP

1. `context_fetch_compact` para ubicar contexto relevante sin abrir documentos completos.
2. `context_bundle` para construir el paquete principal de contexto con presupuesto de caracteres, referencias y omisiones.
3. `context_search_ranked`, `context_file_digest`, `context_symbol_index` y `context_dependency_map` para ampliar solo lo necesario.
4. `memory_lookup`, `memory_session_recap`, `memory_derived_index` y `memory_evidence_digest` para recuperar memoria derivada sin editar `MEMORY.md`.
5. `context_fetch_changes`, `context_change_impact` y `context_trace_lookup` para resumir diff, impacto y trazabilidad.
6. `governance_preflight`, `governance_step_status`, `governance_trace_gap_scan` y `governance_protected_path_check` para revisar requisitos antes de actuar.
7. `canon_prepare_change` o `canon_prepare_multi_change` para revisar diffs y hashes antes de tocar canon.
8. `canon_apply_controlled_change` o `canon_apply_multi_change` solo cuando exista validación humana interna no pública vigente y evidencia fuente corroborada si aplica.
9. `python3 07_scripts/build_all.py` para auditoria posterior.

## Router de tareas y economia de tokens

1. Caveman reduce ruido de salida y mantiene instrucciones de agente en modo conciso.
2. Serena resuelve contexto interno, mapa repo, trazabilidad y preflight.
3. `07_scripts/agent_task_router.py` clasifica tareas por privacidad, riesgo, complejidad, rutas objetivo y necesidad de documentacion externa.
4. Modelos locales (`ollama_local` o `desktop_compute` via `ollama-pc`) pueden ejecutar subtareas automáticas, pero no escriben directo al repositorio; el agente principal integra solo tras gates.
5. `context7_docs` se usa solo para documentacion externa actualizada y versionada.
6. `github_models_free` queda inactivo por defecto y solo puede recibir contexto `public` o `redacted` con token `models:read`; evidencia privada, secretos, ledger privado y rutas sensibles quedan bloqueadas.
7. `ab_pilot.py` compara rutas por tokens, costo, latencia, aceptacion, fallos de gate y retrabajo antes de promover una ruta.

## Regla de interpretacion

- Si el host MCP muestra `serena-local`, las 29 tools y una traza nueva en JSONL, la integracion E2E se considera operativa.
- Si además se reactiva `serena-local-py` y muestra las mismas 29 tools, el diagnóstico por `stdio` se considera operativo, pero no es requisito para el workspace actual.
- Si solo existe una configuracion MCP sin `tools/list` exitoso, la integracion esta declarada pero no validada en uso real.
- En Windows con host local, el launcher recomendado para uso bajo demanda es `.vscode/serena-http.cmd` o el comando equivalente del host para ejecutar `07_scripts/serena_mcp.py` por HTTP.
- `serena-local-py` no redefine el contrato MCP; solo ofrece una ruta opcional de diagnóstico al mismo servidor lógico cuando se habilita manualmente.
- Si hay espera infinita durante `initialize`, el archivo `serena_mcp_debug.log` debe indicar si el proceso arrancó, leyó el mensaje y escribió respuesta.
- `serena_mcp_debug.log` y `serena_mcp_debug_http_check.log` son artefactos diagnósticos locales; sirven para depuración y no deben tratarse como evidencia principal de publicación.
- Los archivos `serena_http_probe_*`, `serena_compare_*` y `serena_write_probe_*` en `audit_history/` se consideran sondas temporales salvo que una validación humana los promueva explícitamente a evidencia canónica.

## Recuperacion rapida

1. Reiniciar o recargar el host MCP.
2. Confirmar trust del servidor MCP si el host lo solicita.
3. Verificar la lista de servidores MCP del host y comprobar que `serena-local` siga visible como perfil activo.
4. Correr `python 07_scripts/serena/check_serena_access.py`.
5. Si `serena-local` falla por HTTP, primero recargar la ventana o relanzar la tarea `Serena MCP HTTP`; si `check_serena_access.py` muestra `stdio` sano pero no expuesto, tratar `serena-local-py` solo como diagnóstico local o reactivarlo manualmente bajo decisión explícita.
6. Si el host sigue sin ver tools MCP aunque HTTP responda bien, asumir primero una limitacion del host/runtime antes que un fallo de negocio en Serena.
7. Si un host externo no puede registrar `127.0.0.1`, desplegar el bridge detras de un tunel o reverse proxy con auth y registrar esa URL publica.

_Última actualización: `2026-06-03`._
