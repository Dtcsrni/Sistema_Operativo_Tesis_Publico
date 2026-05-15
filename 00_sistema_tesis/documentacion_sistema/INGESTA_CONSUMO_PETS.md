# Ingesta y Consumo de PET Bundles en OpenClaw

## Visión General

El sistema OpenClaw consume **PET Bundles (Paquetes de Evidencia Académica)** que son generados por sistemas externos (e.g., ResearchLLM, herramientas de síntesis de literatura, validadores de claims). Los PETs se ingestan, validan y enriquecen como contexto para sesiones académicas.

**Flujo Principal:**
1. **Ingesta:** PET bundle JSON → validación SHA-256 → base de datos SQLite
2. **Auditoría:** Claims en CSV → clasificación (factual/no-factual, con/sin soporte)
3. **Consumo:** Sesión académica recupera PETs → enriquece contexto → dispatcher inyecta evidencia

---

## 1. Estructura de PET Bundle

Un **PET Bundle** es un paquete JSON con:

```json
{
  "bundle_id": "PEB-XXXXXXXX",
  "package_id": "PKG-CONTEXT-001",
  "source_system": "ResearchLLM-v2",
  "source_timestamp": "2026-05-02T05:19:31.881121+00:00",
  "content_literal": "FRAGMENTO: F001\nHASH_hash omitido: abc123\n...\nFIN_FRAGMENTO",
  "claims_matrix_csv": "claim_id,afirmacion,tipo_afirmacion,...",
  "decisions_log_md": "# Decisiones\n- D001: ...",
  "metadata": {"doi": "10.1234/example", "version": 1},
  "integrity_hash": "hash omitido:omitido..."
}
```

### Campos Principales

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `bundle_id` | str | ID único del bundle (ej. PEB-{uuid[:8]}) |
| `package_id` | str | Referencia al paquete académico que origina el PET |
| `source_system` | str | Sistema externo que generó el bundle |
| `source_timestamp` | ISO 8601 | Cuándo se creó el bundle en el sistema origen |
| `content_literal` | str | Fragmentos académicos en formato FRAGMENTO...FIN_FRAGMENTO |
| `claims_matrix_csv` | str | Matriz de claims auditables (CSV con headers estándar) |
| `decisions_log_md` | str | Decisiones tomadas durante la síntesis del bundle |
| `metadata` | dict | Metadatos opcionales (DOI, versión, tags, etc.) |
| `integrity_hash` | str | SHA-256 del contenido (usado para validar integridad) |

---

## 2. Ingesta de PETs

### 2.1 Via CLI

```bash
python 07_scripts/tesis.py pet ingest <ruta-a-bundle.json>
```

**Ejemplo:**
```bash
python 07_scripts/tesis.py pet ingest external_research_bundle.json
```

**Salida:**
```
[OK] PET bundle ingestado:
  - Bundle ID: PEB-1080e5d2e639
  - Package ID: PKG-TEST-CLI-001
  - Sistema origen: ResearchLLM-v2
  - Estado: validated
  - Claims: 2
  - Fragmentos: 2
```

### 2.2 Via API Programática

```python
from openclaw_local.epistemic import ingest_pet_bundle, sha256_dict
from openclaw_local.storage import OpenClawStore
from datetime import datetime, UTC

store = OpenClawStore("runtime/openclaw/openclaw_store.db")

# Preparar payload
payload = {
    "content_literal": "FRAGMENTO: F001\n...\nFIN_FRAGMENTO",
    "claims_matrix_csv": "claim_id,afirmacion,...",
}
integrity_hash = sha256_dict(payload)

# Ingestar
result = ingest_pet_bundle(
    bundle_id="PEB-CUSTOM-001",
    package_id="PKG-ACADEMIC-001",
    source_system="CustomGenerator",
    source_timestamp=datetime.now(UTC).isoformat(),
    content_literal=payload["content_literal"],
    claims_matrix_csv=payload["claims_matrix_csv"],
    decisions_log_md="# Decisiones de síntesis",
    metadata={"custom_field": "valor"},
    integrity_hash=integrity_hash,
)

# Persistir
store.ingest_pet_bundle(
    bundle_id=result.bundle_id,
    package_id=result.package_id,
    source_system=result.source_system,
    source_timestamp=result.source_timestamp,
    content_literal=result.content_literal,
    claims_matrix_csv=result.claims_matrix_csv,
    decisions_log_md=result.decisions_log_md,
    metadata=result.metadata,
    integrity_hash=result.integrity_hash,
    status=result.status,
    claims_count=result.claims_count,
    fragments_count=result.fragments_count,
)
```

---

## 3. Validación de PETs

### 3.1 Validación de Integridad

El sistema valida que el `integrity_hash` coincida con el contenido actual:

```python
from openclaw_local.epistemic import validate_pet_bundle_integrity

is_valid, error = validate_pet_bundle_integrity(
    content_literal=bundle["content_literal"],
    claims_matrix_csv=bundle["claims_matrix_csv"],
    decisions_log_md=bundle["decisions_log_md"],
    metadata=bundle["metadata"],
    expected_integrity_hash=bundle["integrity_hash"],
)
```

### 3.2 Auditoría de Claims

Cada claim en la matriz CSV se clasifica según:

- **Estado de Auditoría:**
  - `aprobado`: Afirmación factual (tipo_afirmacion en {hecho_verificado, inferencia_razonada}) con hash_soporte
  - `pendiente`: Hipótesis o afirmación no factual (tipo_afirmacion en {hipotesis, propuesta})
  - `bloqueado`: Afirmación factual SIN hash_soporte (rechazada por falta de evidencia)

```python
from openclaw_local.epistemic import audit_pet_bundle_claims

audited_claims, errors = audit_pet_bundle_claims(
    claims_matrix_csv=bundle["claims_matrix_csv"],
)

for claim in audited_claims:
    print(f"{claim.afirmacion}: {claim.estado_auditoria}")
```

---

## 4. Consumo de PETs en Sesiones

### 4.1 Asociar PETs a una Sesión

```python
from openclaw_local.session_pet_middleware import attach_pet_bundles_to_session

session_updated = attach_pet_bundles_to_session(
    store=store,
    session=session,
    pet_bundle_ids=["PEB-CUSTOM-001", "PEB-ANOTHER-002"],
)
```

### 4.2 Enriquecer Contexto de Sesión

```python
from openclaw_local.academic_context import load_pet_bundles_for_session

context = load_pet_bundles_for_session(
    store=store,
    session_id="SES-ACADEMIC-001",
    packet_id="AWP-001",
    pet_bundle_ids=["PEB-CUSTOM-001"],
)

# Acceder a fragmentos y claims auditados
print(f"Fragmentos: {len(context.contextual_fragments)}")
print(f"Claims auditados: {len(context.audited_claims)}")
print(f"\nEvidencia integrad ruta local no pública ")
```

### 4.3 Enriquecer Prompts con Contexto PET

```python
from openclaw_local.academic_context import enrich_session_prompt_with_pet_context

original_prompt = "¿Cómo funciona la investigación académica?"

enriched = enrich_session_prompt_with_pet_context(
    original_prompt=original_prompt,
    context=context,
    inject_position="prefix",  # o "suffix"
)

# enriched incluye automaticamente fragmentos y claims auditados
```

### 4.4 Middleware de Sesión (Enriquecimiento Automático)

El **dispatcher** (manejador de comandos de sesión) puede ser envuelto para inyectar contexto PET automáticamente:

```python
from openclaw_local.session_pet_middleware import wrap_dispatcher_with_pet_context

# Dispatcher original
def my_dispatcher(command: str, argument: str) -> dict:
    return {"text": f"Respuesta a {command}", "status": "ok"}

# Envuelto con contexto PET
wrapped_dispatcher = wrap_dispatcher_with_pet_context(
    my_dispatcher,
    store=store,
    session=session_with_pet_ids,
)

# Ejecutar
response = wrapped_dispatcher("chat", "Pregunta sobre investigación")
# response["text"] ahora incluye contexto de PETs si los hay
```

---

## 5. Consulta de PETs Ingestados

### 5.1 Via CLI

```bash
# Listar todos los PETs
python 07_scripts/tesis.py pet list

# Filtrar por sistema de origen
python 07_scripts/tesis.py pet list --source-system ResearchLLM-v2

# Filtrar por estado
python 07_scripts/tesis.py pet list --status validated

# Limitar resultados
python 07_scripts/tesis.py pet list --limit 5
```

### 5.2 Via API Programática

```python
# Recuperar un PET específico
bundle = store.get_pet_bundle_by_id("PEB-CUSTOM-001")

# Listar PETs con filtros
bundles = store.list_ingested_pet_bundles(
    source_system="ResearchLLM-v2",
    status="validated",
    limit=10,
)
```

---

## 6. Flujo Completo de Ejemplo

```python
from openclaw_local.storage import OpenClawStore
from openclaw_local.epistemic import ingest_pet_bundle, sha256_dict
from openclaw_local.academic_context import load_pet_bundles_for_session
from openclaw_local.session_pet_middleware import attach_pet_bundles_to_session
from datetime import datetime, UTC
import json

# 1. Crear store
store = OpenClawStore("runtime/openclaw/openclaw_store.db")

# 2. Ingestar PET bundle desde JSON
with open("external_bundle.json") as f:
    bundle_data = json.load(f)

result = ingest_pet_bundle(
    bundle_id=bundle_data["bundle_id"],
    package_id=bundle_data["package_id"],
    source_system=bundle_data["source_system"],
    source_timestamp=bundle_data["source_timestamp"],
    content_literal=bundle_data["content_literal"],
    claims_matrix_csv=bundle_data["claims_matrix_csv"],
    decisions_log_md=bundle_data.get("decisions_log_md", ""),
    metadata=bundle_data.get("metadata", {}),
    integrity_hash=bundle_data["integrity_hash"],
)

store.ingest_pet_bundle(
    bundle_id=result.bundle_id,
    package_id=result.package_id,
    source_system=result.source_system,
    source_timestamp=result.source_timestamp,
    content_literal=result.content_literal,
    claims_matrix_csv=result.claims_matrix_csv,
    decisions_log_md=result.decisions_log_md,
    metadata=result.metadata,
    integrity_hash=result.integrity_hash,
    status=result.status,
    claims_count=result.claims_count,
    fragments_count=result.fragments_count,
)

# 3. Crear sesión académica
session = store.get_session("SES-ACADEMIC-001") or {
    "session_id": "SES-ACADEMIC-001",
    "payload": {},
}

# 4. Asociar PETs a sesión
session = attach_pet_bundles_to_session(
    store=store,
    session=session,
    pet_bundle_ids=[result.bundle_id],
)

# 5. Cargar contexto enriquecido
context = load_pet_bundles_for_session(
    store=store,
    session_id="SES-ACADEMIC-001",
    packet_id="AWP-RESEARCH-001",
    pet_bundle_ids=[result.bundle_id],
)

# 6. Usar contexto en respuestas
print(f"✓ {len(context.contextual_fragments)} fragmentos cargados")
print(f"✓ {len(context.audited_claims)} claims auditados")
print(f"\n{context.integrated_evidence}")
```

---

## 7. Arquitectura de Almacenamiento

Los PETs se persisten en SQLite con la tabla `pet_bundles_ingestados`:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `bundle_id` | TEXT (PK) | ID único |
| `package_id` | TEXT | Referencia a paquete académico |
| `source_system` | TEXT | Sistema origen |
| `source_timestamp` | TEXT (ISO 8601) | Timestamp del origen |
| `integrity_hash` | TEXT | SHA-256 de validación |
| `status` | TEXT | {ingested, validated, rejected} |
| `content_literal` | TEXT | Fragmentos academicos |
| `claims_matrix_csv` | TEXT | Matriz de claims |
| `decisions_log_md` | TEXT | Decisiones de síntesis |
| `metadata_json` | TEXT | JSON de metadatos |
| `validation_errors` | TEXT | Errores encontrados |
| `claims_count` | INTEGER | Número de claims |
| `fragments_count` | INTEGER | Número de fragmentos |
| `created_at` | TEXT (ISO 8601) | Timestamp de ingesta |

---

## 8. Garantías de Auditoría

- **Integridad SHA-256:** Cada PET ingested incluye hash para detectar modificaciones
- **Trazabilidad de Claims:** Cada claim audited queda registrado con estado explícito
- **Sesiones Enriquecidas:** Todo contexto PET inyectado en respuestas queda registrado en el payload de la sesión
- **Fragmentos Citables:** Cada fragmento incluye hash y autoridad para citación académica

---

## 9. Próximas Funcionalidades (Roadmap)

- [ ] Deduplicación de PETs por integrity_hash
- [ ] Versionamiento de PET bundles (v1, v2, etc.)
- [ ] Revalidación automática de PETs vencidos
- [ ] Mecanismo de reclamación y reporte de PETs con errores
- [ ] API REST para ingesta remota de PETs
- [ ] Dashboard de auditoría de PETs ingestados

_Última actualización: `2026-05-15`._
