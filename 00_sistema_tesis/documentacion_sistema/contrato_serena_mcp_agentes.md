# Contrato Serena MCP para Agentes Compatibles

## Propósito
Definir a `serena-local` como contrato MCP común del proyecto para hosts externos compatibles y para consumidores internos como `OpenClaw`.

## Servidor estándar
- **Nombre lógico:** `serena-local`
- **Transporte preferido:** Streamable HTTP local en `http://127.0.0.1:8765/mcp`
- **Transporte alterno:** `stdio`
- **Raíz efectiva:** `${workspaceFolder}` o la raíz real del repositorio

## Herramientas expuestas
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

Todo host MCP compatible debe ver nombres con `_` en `tools/list` cuando normalice nombres de herramientas. Internamente el contrato canonico conserva nombres con punto (`context.fetch_compact`, `governance.preflight`, etc.) y el servidor acepta ambas formas en `tools/call`.

## Requisitos mínimos de identidad y entorno
- `SISTEMA_TESIS_ROOT`: raíz efectiva del repositorio.
- `SERENA_MCP_DEBUG_LOG`: ruta del log técnico de arranque/JSON-RPC.
- `SISTEMA_TESIS_AGENT_ROLE`
- `SISTEMA_TESIS_AGENT_PROVIDER`
- `SISTEMA_TESIS_AGENT_MODEL_VERSION`
- `SISTEMA_TESIS_AGENT_RUNTIME`

## Consumidores objetivo en esta fase
- **Hosts agénticos locales:** Codex Desktop, Codex en VS Code, Antigravity, Antigravity IDE, Cursor, Continue, JetBrains, Copilot u otros clientes MCP pueden registrar directamente el servidor local o el bridge.
- **OpenClaw:** adapter interno que consume el contrato MCP sin entrar al `provider_registry`.
- **Runtimes separados del IDE:** deben usar el bridge HTTP autenticado si no heredan el MCP del host.

## Frontera entre host y runtime

- El contrato `serena-local` describe el servidor y sus herramientas, no garantiza que cualquier runtime de chat herede automaticamente el acceso del host.
- Cualquier host MCP puede descubrir el servidor mediante una configuracion equivalente a `docs/03_operacion/mcp-agent-host-template.json`, iniciar el transporte configurado y presentar las tools en su UI.
- `.vscode/mcp.json` es una implementacion local de referencia, no la fuente unica de verdad.
- Un runtime de chat separado solo podra invocarlo si soporta registrar MCP externos, si consume el bridge autenticado o si delega la invocacion al host que si expone el MCP.
- `serena-local-py` se considera un alias operativo del host para `stdio`; no es un segundo contrato de negocio ni cambia `serverInfo.name`.
- En el workspace actual (`2026-06-02`), `serena-local` y los perfiles Docker MCP recomendados se describen en `docs/03_operacion/mcp-agent-host-template.json`.
- En el estado actual del workspace (`2026-06-02`), `serena-local-py` queda como diagnostico por `stdio`; su backend puede seguir sano localmente, pero eso no lo vuelve automaticamente disponible ni recomendado para los agentes del host activo.
- La politica operativa debe distinguir entre perfil expuesto y backend saludable: los agentes deben usar Serena a traves del perfil realmente publicado y recomendado por `check_serena_access.py`.
- La verificacion operativa recomendada del repo es `python3 07_scripts/check_agent_context_tools.py --attempt-start-http --json`.
- La verificacion del contrato multi-host es `python3 07_scripts/check_serena_multi_host_contract.py --json`.
- Cuando un runtime externo necesite consumir Serena sin compartir el localhost del host agéntico, la via oficial es el bridge HTTP autenticado en `runtime/serena_bridge/bin/serena_bridge.py`.

## Criterios E2E
- El host descubre `serena-local`.
- El host ve las 29 herramientas esperadas.
- `context_fetch_compact` responde en lectura con `status: ok`.
- `context_repo_map`, `context_fetch_changes`, `context_trace_lookup` y `context_session_brief` estan disponibles como herramientas compactas de economia de tokens.
- `context_bundle`, `context_search_ranked`, `memory_lookup` y `memory_evidence_digest` quedan disponibles como rutas principales de reducción de contexto y memoria.
- `canon_apply_multi_change` y `artifacts_write_memory_derived` escriben solo bajo las reglas de gobernanza, backups, manifest y traza aplicables.
- `governance_preflight` reporta bloqueo cuando falta `step_id` en cambios controlados.
- La traza de operación queda registrada en `historial interno no público/serena_mcp_operations.jsonl`.
- Si el acceso llega por bridge, la traza incluye identidad del host y `host_kind=external_runtime`.
- La garantia multi-IDE significa contrato, plantillas, verificador y bridge disponibles; cada IDE debe registrar el servidor o el bridge y pasar `tools/list` en su propio runtime.

## Referencias
- `00_sistema_tesis/documentacion_sistema/operacion_serena_mcp_codex.md`
- `docs/03_operacion/openclaw-workspace-local.md`
- `docs/03_operacion/mcp-agent-host-template.json`
- `docs/03_operacion/serena-mcp-host-template.json`

_Última actualización: `2026-06-03`._
