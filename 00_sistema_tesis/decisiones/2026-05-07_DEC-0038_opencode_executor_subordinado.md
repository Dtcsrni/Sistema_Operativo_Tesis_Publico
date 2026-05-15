<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0038 | 2026-05-07 | v1.0 | Especificación Técnica -->

# DEC-0038 Integración de OpenCode como Executor Subordinado con RAG Weaviate Obligatorio

- Fecha: 2026-05-07
- Estado: especificación técnica
- Alcance: arquitectura | ejecución | trazabilidad
- Relacionada con: DEC-0031, DEC-0030
- Tema: automatización de tareas complejas con garantías RAG

## Contexto

OpenCode es conveniente **solo como executor subordinado** a OpenClaw/Mission Control, no como nuevo orquestador. La especificación oficial confirma:
- Modo `run`: ejecución no interactiva de tareas
- Modo `serve`: servidor headless
- Proveedores: proveedor de IA no publicado-compatible (local via Ollama) + LiteLLM
- Modelo por defecto: DeepSeek-R1:7b via ollama-pc:11434

**Restricción RAG Obligatoria (Usuario):** "Solo Weaviate" = sin fallback a JSONL. Cualquier tarea marcada como `requires_rag` o académica DEBE:
1. Consultar Weaviate en preflight
2. Recuperar chunks con trazabilidad (source_hash, chunk_hash)
3. Bloquear ejecución si Weaviate no ready o sin hits
4. Registrar source y decisión en trazabilidad

## Cambios Clave

### 1. Servicio Docker: opencode-executor
**Ubicación:** docker-compose.pc.yml → nuevo servicio `opencode-executor`
**Configuración:**
- Imagen: `opencode:latest` (basada en `python:3.11-slim` + opencode CLI)
- Modo: headless no interactivo
- Modelo: `deepseek-r1:7b` via `http://ollama-pc:11434` (proveedor de IA no publicado-compatible)
- Volúmenes: workspace permitido, cache, logs
- Red: `siot-network` (comunicación interna con tablero, toltecayotl, pasarela)
- Healthcheck: `opencode --version` o webhook a Mission Control API

### 2. Preflight RAG (Bloqueo Duro)
**Script:** `07_scripts/preflight_rag_mandatory.py`
**Lógica:**
```
Para cada tarea con requires_rag=true:
  1. health_check(weaviate:8080)
     → si 503/offline → BLOQUEAR con status=RAG_BLOCKED
  2. rag_query(question, context_hint)
     → registrar: query_ts, chunks[], hit_count, backend_version
  3. si hit_count == 0 → BLOQUEAR con status=RAG_NO_HITS
  4. si hit_count > 0:
     → calcular SHA256(chunks) → chunk_hash
     → registrar source_hash del corpus Weaviate
     → permitir ejecución
  5. trazabilidad: [rag_session_id, query_hash, chunks_recovered, source_hash, timestamp]
```

**Condiciones de Bloqueo (No Recuperable):**
- Weaviate HTTP status != 200
- No hay conexión a `base-semantica-toltecayotl:8080`
- 0 chunks recuperados
- Response time > 5s (timeout RAG)

### 3. Ejecución del Executor
**Flujo:**
```
Mission Control → preflight_rag_mandatory.py → Weaviate ✓
  ↓ (ok)
OpenCode Executor (entrada en cola)
  ├─ workspace prep: clone contextual, setup env
  ├─ context inject: chunks RAG como referencia de sistema
  ├─ task execution: opencode run --task <script>
  │  └─ modelo: deepseek-r1:7b vía ollama-pc
  └─ output capture: deliverable, exit_code, logs, hashes

Resultado → Mission Control (checkpoint) → trazabilidad (ledger)
```

### 4. Trazabilidad de Ejecución
**Registro en:** `00_sistema_tesis/bitacora/execution_log.jsonl`

Cada entrada:
```json
{
  "timestamp": "2026-05-07T14:32:00Z",
  "session_id": "exec-session-abc123",
  "executor": "opencode-executor",
  "task_id": "TASK-001",
  "task_label": "generate_figure_4.1",
  "requires_rag": true,
  "rag_session_id": "rag-session-xyz789",
  "rag_chunks_recovered": 3,
  "rag_source_hash": "hash omitido
  "rag_chunk_hash": "hash omitido
  "model": "deepseek-r1:7b",
  "provider": "ollama",
  "node": "pc",
  "node_hardware": "Docker",
  "provider_endpoint": "http://ollama-pc:11434",
  "commands_allowed": [
    "python", "pip install", "edit_file", "read_file",
    "mkdir", "git", "docker compose"
  ],
  "workspace_path": "/app/runtime/workspaces/task-abc123",
  "exit_code": 0,
  "stdout_size_bytes": 1024,
  "stderr_size_bytes": 0,
  "deliverable_files": [
    {"path": "output/figure.pdf", "size_bytes": 256000, "hash": "hash omitido
  ],
  "errors": null,
  "duration_seconds": 45.32,
  "decision": "COMPLETED",
  "mission_control_checkpoint": "TASK_COMPLETED",
  "created_by": "DEC-0038",
  "audit_hash": "hash omitido
}
```

### 5. Restricciones de Seguridad
- **Rutas permitidas:** solo `runtime/workspaces/<task_id>/` + `/app/07_scripts` (RO)
- **Comandos permitidos:** python, git, edit dentro de workspace, docker compose (solo info)
- **Prohibido:** modificar canon, bitácora, decisiones, archivos protegidos
- **Exit codes:** cualquier código != 0 es error recuperable (no genera crash global)

### 6. Routing Exclusivo
- **Modelo por defecto:** DeepSeek-R1:7b (PC, Docker)
- **Mistral:** excluido por defecto (requiere selector explícito en tarea)
- **Edge (192.168.1.124:11434):** solo si tarea.assigned_node == "edge"
- **Verificación:** logs deben mostrar `provider=ollama`, `endpoint=http://ollama-pc:11434`

## Pruebas End-to-End

### E2E-1: RAG Feliz
```
Setup: Weaviate ✓, chunks académicos en Toltecayotl
Tarea: "Genera tabla de PDR comparativo" (requires_rag=true)
Preflight: ✓ RAG recupera 5 chunks
Ejecución: deepseek escribe tablatarea
Resultado: ✓ deliverable + trazabilidad + checkpoint en MC
```

### E2E-2: RAG Roto (503)
```
Setup: Weaviate down (simular stop/restart)
Tarea: "Genera tabla PDR" (requires_rag=true)
Preflight: ✗ Weaviate 503 → bloqueo inmediato
Resultado: task.status=RAG_BLOCKED, no ejecución, sin fallback
```

### E2E-3: RAG Sin Hits
```
Setup: Weaviate ✓, pero pregunta no recupera chunks (ej. "generavalencia subatómica")
Tarea: "Genera tabla subatómica" (requires_rag=true)
Preflight: ✗ 0 hits → bloqueo
Resultado: task.status=RAG_NO_HITS, no ejecución
```

### E2E-4: Código Simple (no RAG)
```
Setup: Tarea sin requires_rag
Tarea: "Crear script de salud check" (requires_rag=false)
Preflight: ✓ saltado (no RAG requerido)
Ejecución: ✓ OpenCode ejecuta, crea archivo
Resultado: ✓ deliverable + trazabilidad + checkpoint
```

### E2E-5: Timeout y Resiliencia
```
Setup: Tarea larga (180s timeout configurado)
Escenarios:
  a) Timeout durante ejecución → exit code 124 → error recuperable
  b) Fallo de modelo (conexión) → exit code 1 → retry automático (3x)
  c) Disk full durante escritura → exit code ENOSPC → alert + bloqueo
Resultado: logs claros, sin corrupción de trazabilidad
```

### E2E-6: Routing Verificado
```
Setup: Logs + auditoría de ejecución
Verificaciones:
  • grep "provider=ollama" → ✓
  • grep "deepseek-r1:7b" → ✓
  • grep "http://ollama-pc:11434" → ✓
  • grep "mistral" → ✗ (no debe aparecer)
  • grep "edge|192.168.1.124" → ✗ (excepto si assigned_node=edge)
Resultado: ✓ routing correcto, sin spillover
```

## Supuestos

1. OpenCode CLI se instala en el Dockerfile y resuelve `opencode run` + `opencode serve`
2. Ollama-PC está healthy y deepseek:7b está pulleado
3. Weaviate responde en puerto 8080 (verificado ✓)
4. Mission Control API disponible en puerto 4000
5. Usuario no modificará trazabilidad ni archivos protegidos sin Step ID

## Criterio de Aceptación Humana

• Tesista aprueba arquitectura de opencode-executor subordinado
  • Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
> **Soporte:** Pendiente de aprobación
> **Texto exacto:** "opencode-executor-subordinado"
> **Fuente:** `00_sistema_tesis/canon/events.jsonl`

• Todas las pruebas E2E pasan (6/6)

• `python 07_scripts/build_all.py` ejecuta sin errores canónicos (fallas preexistentes reportadas por separado)

## Referencias
- [DEC-0031: Mission Control](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-05-02_DEC-0031_adopcion_mission_control.md)
- [DEC-0030: Local-First](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-05-01_DEC-0030_adopcion_arquitectura_local_first.md)
- [OpenCode Docs: CLI](https://opencode.ai/docs/cli/)
- [OpenCode Docs: Providers](https://opencode.ai/docs/providers/)

---

**Escrita:** 2026-05-07 00:00 UTC
**Próxima revisión:** post-E2E


---

## 🔗 Referencias Globales

- **[LID]:** Decisión registrada en canon / log_sesiones_trabajo_registradas.md
- **[GOV]:** Política de Gobernanza / AGENTS.md  
- **[AUD]:** Validación vía build_all.py / operabilidad humana


[LID]:  ruta local no pública /00_sistema_tesis/decisiones/2026-05-07_DEC-0038_opencode_executor_subordinado.md
[GOV]: AGENTS.md
[AUD]: build_all.py

_Última actualización: `2026-05-15`._
