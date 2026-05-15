# OpenCode Executor — Quick Start & Testing Guide

## Status de Implementación

✅ **COMPLETADO:** Diseño, decisión técnica, scripts, Docker config  
⏳ **PENDIENTE:** Pruebas E2E, compilación Docker, validación humanatural

---

## 1. Verificación Rápida de Configuración

### 1.1 Validar Docker Compose
```bash
cd  ruta local no pública 

# Validar sintaxis YAML
docker compose -f docker-compose.pc.yml config --services

# Esperado:
# base-semantica-toltecayotl
# tablero-gobernanza
# nucleo-openclaw
# ollama-pc
# opencode-executor          ← ¡NUEVO!
# pasarela-openclaw
# api-persistencia-misiones
# centro-control-misiones
```

### 1.2 Verificar Weaviate
```bash
curl http://localhost:8080/v1/meta

# Esperado: JSON con version 1.31.4
```

---

## 2. Ejecutar Suite de Pruebas E2E

```bash
cd  ruta local no pública 

# Ejecutar todas las pruebas
python 07_scripts/test_opencode_e2e.py

# Con output verboso
python 07_scripts/test_opencode_e2e.py --verbose

# Guardar reporte
python 07_scripts/test_opencode_e2e.py --save-report /tmp/e2e_report.json
```

**Casos cubiertos:**
1. ✅ RAG Happy Path — Weaviate responde, recupera chunks, ejecuta
2. ✅ RAG Broken — Weaviate offline → tarea bloqueada
3. ✅ RAG No Hits — Query sin chunks → tarea bloqueada
4. ✅ Code Simple — Sin RAG, ejecución normal
5. ✅ Timeout & Resilience — Captura timeouts, fallos recuperables
6. ✅ Routing Verified — PC/DeepSeek, no Mistral, no Edge

---

## 3. Ejecutar Preflight RAG

```bash
# Test: Preflight OK
python 07_scripts/preflight_rag_mandatory.py \
  --task-id TASK-001 \
  --question "¿Qué es PDR en redes LoRa?" \
  --context iot \
  --output /tmp/preflight_result.json

# Test: Preflight sin RAG
python 07_scripts/preflight_rag_mandatory.py \
  --task-id TASK-002 \
  --question "test" \
  --no-rag \
  --output /tmp/preflight_no_rag.json

# Verificar salida
cat /tmp/preflight_result.json
```

---

## 4. Ejecutar Tarea via OpenCode Executor (Simulado)

```bash
# Crear task.json de prueba
cat > /tmp/task.json << 'EOF'
{
  "label": "test_executor",
  "requires_rag": false,
  "script": "print('Hello from OpenCode'); open('output.txt', 'w').write('SUCCESS')"
}
EOF

# Ejecutar
python 07_scripts/opencode_executor_run.py \
  --task-id TEST-001 \
  --task-file /tmp/task.json \
  --no-rag

# Verificar log de ejecución
cat 00_sistema_tesis/bitacora/execution_log.jsonl | tail -1 | python -m json.tool
```

---

## 5. Compilar Imagen Docker (Opcional)

```bash
# Si tienes Docker disponible y quieres compilar la imagen
docker compose -f docker-compose.pc.yml build opencode-executor

# Verificar que fue compilada
docker images | grep opencode
```

---

## 6. Auditoría Completa del Sistema

```bash
# Ejecutar build_all.py (auditoría completa)
python 07_scripts/build_all.py

# Revisar resultados en:
# - 00_sistema_tesis/bitacora/
# - 00_sistema_tesis/canon/
```

---

## 7. Archivos Generados

Después de ejecutar pruebas:

### Logs de Preflight RAG
```
00_sistema_tesis/bitacora/preflight_rag_log.jsonl
```
Cada línea: query_hash, chunks_recovered, status, timestamp

### Logs de Ejecución
```
00_sistema_tesis/bitacora/execution_log.jsonl
```
Cada línea: task_id, session_id, model, exit_code, deliverables, audit_hash

### Reporte E2E (si se genera)
```
/tmp/e2e_report.json  ← JSON con resultados de todas las pruebas
```

---

## 8. Verificar Routing (PC/DeepSeek, sin Mistral)

```bash
# Buscar en logs de ejecución
grep "deepseek" 00_sistema_tesis/bitacora/execution_log.jsonl
grep "ollama-pc" 00_sistema_tesis/bitacora/execution_log.jsonl

# Verificar que NO hay Mistral (salvo asignación explícita)
grep "mistral" 00_sistema_tesis/bitacora/execution_log.jsonl
# Esperado: sin resultados

# Verificar que NO hay Edge (salvo asignación explícita)
grep "192.168.1.124" 00_sistema_tesis/bitacora/execution_log.jsonl
# Esperado: sin resultados
```

---

## 9. Validar Trazabilidad RAG Obligatorio

```bash
# Confirmar que tareas con requires_rag=true fueron bloqueadas si Weaviate estaba down
cat 00_sistema_tesis/bitacora/preflight_rag_log.jsonl | \
  python -c "import sys, json; [print(json.loads(l)['status']) for l in sys.stdin]"

# Esperado: mix de "OK", "RAG_BLOCKED", "RAG_NO_HITS"
```

---

## 10. Parámetros de Configuración (Env)

Editables en `config/env/openclaw.env`:

```bash
# Modelo y Provider
OPENCODE_MODEL=deepseek-r1:7b          # Cambiar si es necesario
OPENCODE_PROVIDER=ollama
OPENCODE_BASE_URL=http://ollama-pc:11434

# Timeouts
OPENCODE_TIMEOUT_SEC=180               # Timeout de tarea (segundos)

# RAG
RAG_ENDPOINT=http://base-semantica-toltecayotl:8080
RAG_REQUIRED=true                      # Obligatorio

# Mission Control
MISSION_CONTROL_API=http://centro-control-misiones:4000
```

---

## 11. Troubleshooting

### Problema: `docker compose config` no muestra opencode-executor
**Solución:** 
```bash
# Verificar indentación (debe tener 2 espacios a nivel de servicio)
grep "^  opencode-executor:" docker-compose.pc.yml

# Si retorna vacío, hay problema de indentación
```

### Problema: Weaviate retorna 503
**Solución:**
```bash
# Reiniciar Weaviate
docker compose restart base-semantica-toltecayotl

# Verificar health
curl http://localhost:8080/v1/meta
```

### Problema: OpenCode CLI no instalada
**Solución:**
```bash
pip install opencode
opencode --version
```

### Problema: Task bloqueda pero debería ejecutarse
**Solución:**
```bash
# Verificar que requires_rag=false en task.json si no quieres RAG
# O verificar que Weaviate tiene chunks relevantes
```

---

## 12. Archivos Clave para Referencia

| Archivo | Propósito |
|---------|-----------|
| `Dockerfile.opencode-executor` | Imagen Docker del executor |
| `docker-compose.pc.yml` | Configuración Docker (servicio opencode-executor) |
| `00_sistema_tesis/decisiones/2026-05-07_DEC-0038_...` | Decisión técnica |
| `07_scripts/preflight_rag_mandatory.py` | Validador RAG |
| `07_scripts/opencode_executor_run.py` | Ejecutor de tareas |
| `07_scripts/test_opencode_e2e.py` | Suite E2E |
| `00_sistema_tesis/reportes_semanales/RESUMEN_INTEGRACION_...` | Resumen entregable |

---

## 13. Próximas Validaciones Recomendadas

1. **Compilar imagen Docker** (si ambiente permite)
2. **Ejecutar full E2E suite** (6/6 tests deben pasar)
3. **Validar trazabilidad** (execution_log.jsonl debe tener entradas)
4. **Verificar Mission Control integration** (si está disponible)
5. **Ejecutar `build_all.py`** para auditoría completa

---

**Última actualización:** 2026-05-07  
**Responsable:** GitHub Copilot (IA asistida)  
**Status:** Listo para pruebas del usuario
