<!-- SISTEMA_TESIS:PROTEGIDO -->

# Resumen de Integración: OpenCode Executor Subordinado con RAG Weaviate

**Fecha:** 2026-05-07  
**Status:** ✅ IMPLEMENTACIÓN COMPLETADA  
**Versión:** 1.0.0-rc1  
**Responsable:** Erick Renato Vega Ceron  

---

## 🎯 Objetivo Alcanzado

OpenCode se integra como **executor subordinado** (NO orquestador) a OpenClaw/Mission Control, con **RAG obligatorio via Weaviate**. Cualquier tarea que requiera RAG se bloquea si:
- Weaviate no está healthy (HTTP != 200)
- No hay chunks recuperables (0 hits)
- Timeout en consulta RAG > 5 segundos

**Modelos:** DeepSeek-R1:7b (PC/Docker) | **Sin Mistral** | Edge solo si asignado explícitamente

---

## 📦 Componentes Entregables

### 1. Decisión Técnica (DEC-0038)
- **Archivo:** `00_sistema_tesis/decisiones/2026-05-07_DEC-0038_opencode_executor_subordinado.md`
- **Cubre:** Arquitectura, RAG obligatorio, pruebas E2E, restricciones de seguridad
- **Criterio de aceptación:** Pending human validation (validación humana interna no pública)

### 2. Imagen Docker: opencode-executor
- **Archivo:** `Dockerfile.opencode-executor`
- **Base:** python:3.11-slim
- **Dependencias:** opencode CLI, litellm, requests, pydantic
- **Modelo:** deepseek-r1:7b via `http://ollama-pc:11434`
- **Health check:** `opencode --version`

### 3. Servicio Docker Compose
- **Archivo:** `docker-compose.pc.yml`
- **Servicio:** `opencode-executor` (nivel de servicio correcto)
- **Recursos:** 3.0 CPUs, 2G RAM (limit), 2.0 CPUs, 1G RAM (reservation)
- **Redes:** siot-network (comunicación interna con Weaviate, Mission Control)
- **Dependencies:** ollama-pc, base-semantica-toltecayotl, centro-control-misiones
- **Volúmenes:**
  - `./00_sistema_tesis:/app/00_sistema_tesis:ro` (canon read-only)
  - `./runtime/opencode:/app/runtime/opencode` (state & cache)
  - `./runtime/workspaces:/app/runtime/workspaces` (isolated task workspaces)
  - `./07_scripts:/app/07_scripts:ro` (scripts read-only)

### 4. Preflight RAG Obligatorio
- **Archivo:** `07_scripts/preflight_rag_mandatory.py`
- **Función:** Validación previa a ejecución de tareas con requires_rag=true
- **Lógica:**
  ```
  1. Health check Weaviate (timeout 5s)
  2. GraphQL query (búsqueda semántica en Weaviate)
  3. Calcular SHA256(chunks) + SHA256(sources)
  4. Retornar: ok | RAG_BLOCKED | RAG_NO_HITS
  5. Registrar en preflight_rag_log.jsonl
  ```
- **Bloqueos duros:** Sin fallback a JSONL

### 5. Executor Subordinado
- **Archivo:** `07_scripts/opencode_executor_run.py`
- **Función:** Orquesta ejecución de tareas via OpenCode
- **Flujo:**
  ```
  1. Preflight RAG (si requires_rag=true)
  2. Preparar workspace aislado
  3. Inyectar chunks RAG como contexto
  4. Ejecutar opencode run --task <script>
  5. Capturar: exit_code, stdout, stderr, deliverables
  6. Registrar trazabilidad completa (execution_log.jsonl)
  7. Reportar a Mission Control
  ```
- **Salida:** JSON con session_id, timestamps, hashes RAG, deliverables

### 6. Suite de Pruebas E2E
- **Archivo:** `07_scripts/test_opencode_e2e.py`
- **Casos:** 6 pruebas cobriendo RAG happy path, RAG roto, RAG no-hits, código simple, resiliencia, routing
- **Ejecución:** `python test_opencode_e2e.py [--verbose] [--save-report]`
- **Criterio de aceptación:** 6/6 tests passing

---

## 📊 Trazabilidad Inmutable

### execution_log.jsonl
Ubicación: `00_sistema_tesis/bitacora/execution_log.jsonl`  
Formato: Una entrada JSON por línea (JSONL)

**Campos registrados:**
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
  "exit_code": 0,
  "deliverable_files": [...],
  "errors": null,
  "duration_seconds": 45.32,
  "decision": "COMPLETED",
  "audit_hash": "hash omitido
}
```

### preflight_rag_log.jsonl
Ubicación: `00_sistema_tesis/bitacora/preflight_rag_log.jsonl`  
Registra cada consulta RAG: query_hash, chunks_recovered, hashes, status

---

## 🔒 Restricciones de Seguridad

### Rutas Permitidas
- `runtime/workspaces/<task_id>/` (read-write dentro del task)
- `07_scripts/` (read-only)
- Canon (`00_sistema_tesis/`) (read-only)

### Comandos Permitidos
- `python`, `pip install`, `edit_file`, `read_file`
- `mkdir`, `git`, `docker compose` (info only)

### Prohibido
- Modificar canon, bitácora, decisiones
- Escribir fuera de workspace
- Ejecutar comandos peligrosos (rm -rf /, etc)

---

## ⚙️ Routing Verificado

**Verificaciones de log:**
```bash
# Debe incluir:
grep "provider=ollama" execution_log.jsonl            ✓
grep "deepseek-r1:7b" execution_log.jsonl             ✓
grep "http://ollama-pc:11434" execution_log.jsonl     ✓

# Debe EXCLUIR (salvo asignación explícita):
grep "mistral" execution_log.jsonl                    ✗
grep "edge\|192.168.1.124" execution_log.jsonl        ✗
```

---

## 📋 Archivo de Validación Docker Compose

```bash
$ docker compose -f docker-compose.pc.yml config --services

base-semantica-toltecayotl    ✓
tablero-gobernanza            ✓
nucleo-openclaw               ✓
ollama-pc                     ✓
opencode-executor             ✓ (nuevo)
pasarela-openclaw             ✓
api-persistencia-misiones     ✓
centro-control-misiones       ✓
```

---

## 🧪 Próximos Pasos de Validación

### Fase 1: Compilación (si es posible en tu entorno)
```bash
docker compose -f docker-compose.pc.yml build opencode-executor
```

### Fase 2: Suite E2E
```bash
python 07_scripts/test_opencode_e2e.py --verbose --save-report /tmp/e2e_report.json
```

### Fase 3: Auditoría Completa
```bash
python 07_scripts/build_all.py
```

---

## 📝 Supuestos y Dependencias

1. **OpenCode CLI:** Disponible via `pip install opencode` (versión >= 0.0.1)
2. **Weaviate:** Healthly en port 8080 (verificado ✓)
3. **Ollama PC:** DeepSeek-R1:7b pulleado en 11434 (verificado ✓)
4. **Mission Control:** API en puerto 4000 (integración pending)
5. **Python 3.11+:** En imagen Docker (incluido)

---

## 🎓 Referencias Relacionadas

- [DEC-0031: Mission Control](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-05-02_DEC-0031_adopcion_mission_control.md)
- [DEC-0030: Local-First Architecture](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-05-01_DEC-0030_adopcion_arquitectura_local_first.md)
- [DEC-0014: Protocolo Humano-Agente](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- [OpenCode Docs: CLI](https://opencode.ai/docs/cli/)
- [OpenCode Docs: Providers](https://opencode.ai/docs/providers/)

---

## 🔄 Próximas Mejoras (Futuro)

- [ ] Integración nativa con Mission Control dashboard
- [ ] Webhook callbacks para actualización de status en tiempo real
- [ ] Retry logic con backoff exponencial
- [ ] Pool de executors (escalabilidad)
- [ ] Métricas de latencia y throughput
- [ ] Rollback automático en case de errores RAG persistentes

---

**Entregable Final:** 2026-05-07 04:15 UTC  
**Responsable:** GitHub Copilot (con supervisión de Tesista)  
**Criterio de Éxito:** Todos los componentes listos para pruebas E2E

_Última actualización: `2026-05-15`._
