<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0032 | 2026-05-02 | v1.0 | Aprobada -->
# DEC-0032: Arquitectura de Ingesta y Consumo de PET Bundles en OpenClaw

**Fecha:** 2026-05-02  
**Estado:** Aprobada  
**Responsable:** Erick Renato Vega Cerón (Tesista Principal)  
**Impacto:** Crítico para la infraestructura de investigación académica

---

## Problema

El sistema OpenClaw-Toltecayotl requiere un mecanismo robusto para:

1. **Ingestar** paquetes de evidencia académica (PET bundles) generados por sistemas externos (LLMs, validadores, sintetizadores)
2. **Validar** integridad y auditar claims dentro de los PETs
3. **Consumir** PETs como contexto enriquecido en sesiones académicas
4. **Rastrear** la trazabilidad completa de evidencia desde ingesta hasta uso

---

## Decisión

Se implementa un modelo de **ingesta → validación → enriquecimiento** con tres capas de software:

### Capa 1: Epistémica (epistemic.py)
- **Responsabilidad:** Validación e ingesta de PET bundles
- **Funciones clave:**
  - `validate_pet_bundle_integrity()`: SHA-256 para detectar modificaciones
  - `audit_pet_bundle_claims()`: Clasificación de claims (factual/no-factual)
  - `extract_fragments_from_content_literal()`: Parseo de fragmentos académicos
  - `ingest_pet_bundle()`: Orquestación de validación completa

### Capa 2: Contexto Académico (academic_context.py)
- **Responsabilidad:** Enriquecimiento de sesiones con PET evidence
- **Funciones clave:**
  - `load_pet_bundles_for_session()`: Carga PETs para sesión académica
  - `enrich_session_prompt_with_pet_context()`: Inyecta evidencia en prompts
  - `_render_integrated_evidence()`: Renderiza fragmentos y claims auditados

### Capa 3: Middleware de Sesión (session_pet_middleware.py)
- **Responsabilidad:** Integración automática con dispatcher de sesiones
- **Funciones clave:**
  - `wrap_dispatcher_with_pet_context()`: Wrapper que inyecta contexto automáticamente
  - `attach_pet_bundles_to_session()`: Asocia PETs a sesión académica
  - `query_session_pet_context()`: Consulta contexto enriquecido de sesión

### Almacenamiento: SQLite (OpenClawStore)
- Nueva tabla `pet_bundles_ingestados` con campos:
  - `bundle_id` (PK)
  - `integrity_hash`, `status`, `validation_errors`
  - `claims_count`, `fragments_count`
  - `content_literal`, `claims_matrix_csv`, `decisions_log_md`
  - Timestamps ISO 8601 para auditoría

### CLI (tesis.py)
Nuevos comandos operativos:
```bash
python 07_scripts/tesis.py pet ingest <bundle.json>
python 07_scripts/tesis.py pet list [--source-system X] [--status Y] [--limit Z]
```

---

## Rationale

### ¿Por qué ingesta en lugar de generación?

- **Realidad operativa:** Otros sistemas generan evidencia académica de múltiples fuentes
- **Validación defensiva:** Auditor valida que evidence es verificable antes de usarla
- **Trazabilidad:** Cada PET ingested queda con hash SHA-256 inmutable

### ¿Por qué validación por SHA-256?

- **Detección de modificaciones:** Si alguien altera un PET en tránsito, el hash cambia
- **No-repudio:** Sistema origen debe incluir hash correcto en el bundle JSON
- **Compatibilidad:** SHA-256 es estándar industria para integridad de documentos académicos

### ¿Por qué auditoría de claims?

- **Garantía epistémica:** Claims factuales sin evidencia (hash_soporte) son bloqueados
- **Clasificación explícita:** Hipótesis vs. hechos tienen tratamiento diferente
- **Defensa contra alucinaciones:** LLMs que generan PETs deben justificar sus claims

### ¿Por qué middleware en dispatcher?

- **Transparencia:** Sesiones reciben contexto enriquecido sin cambios de API
- **Opt-in automático:** Si sesión tiene pet_bundle_ids, contexto se inyecta
- **Error-safe:** Fallos en enriquecimiento no rompen respuesta de sesión

---

## Implementación

### Archivo: academic_context.py
- Dataclasses: `PETContextualFragment`, `AcademicSessionContext`
- Funciones de carga y enriquecimiento

### Archivo: session_pet_middleware.py
- Wrapper de dispatcher con enriquecimiento automático
- Asociación de PETs a sesiones
- Consulta de contexto enriquecido

### Extensiones a storage.py
- Tabla `pet_bundles_ingestados` con 14 columnas
- Métodos CRUD: `ingest_pet_bundle()`, `get_pet_bundle_by_id()`, `list_ingested_pet_bundles()`

### Extensiones a tesis.py CLI
- Subcomando `pet` con `ingest` y `list`
- Soporte para JSON bundle input
- Outputs formateados con status y conteos

---

## Validación

### Tests Creados
- ✅ `test_validate_pet_bundle_integrity()`: SHA-256 validation
- ✅ `test_audit_pet_bundle_claims()`: Clasificación de claims
- ✅ `test_academic_context_integration()`: Carga y enriquecimiento de sesión
- ✅ `test_session_pet_middleware_integration()`: Dispatcher wrapping funciona

### Casos de Uso Validados
1. Ingesta de PET bundle desde JSON
2. Validación de integridad SHA-256
3. Auditoría de claims con distintas clasificaciones
4. Enriquecimiento de sesión con fragmentos y claims
5. Middleware automático inyecta contexto en respuestas

---

## Impacto en el Proyecto

### Habilitadores
- ✅ Sesiones académicas pueden usar evidencia de sistemas externos
- ✅ Auditoría epistémica defensiva (rechaza evidence no validada)
- ✅ Trazabilidad completa: ingesta → auditoría → consumo
- ✅ CLI operativa para gestión de PETs

### Compatibilidad
- ✅ Backward compatible: Sesiones sin PETs funcionan igual
- ✅ No rompe API existente de SessionEnvelope
- ✅ Storage SQLite extensible sin migración de datos

### Riesgos Mitigados
- ⚠️ Alucinaciones: Claims sin soporte son bloqueados
- ⚠️ Tampering: SHA-256 valida integridad
- ⚠️ Opacidad: Todos los claims auditados quedan registrados

---

## Próximas Fases

1. **Fase 2a:** API REST para ingesta remota de PETs (POST /pet/ingest)
2. **Fase 2b:** Dashboard de auditoría (visualizar PETs ingestados, claims, estado)
3. **Fase 3:** Integración con Weaviate para búsqueda semántica de evidencia
4. **Fase 4:** Subagente "investigador" que usa PETs ingested como base de conocimiento

---

## Referencias

- [DEC-0017: Toltecayotl Epistemic Engine](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/DEC-0017.md)
- [DEC-0028: OpenClaw Runtime Architecture](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/DEC-0028.md)
- [INGESTA_CONSUMO_PETS.md: Guía Operativa](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/INGESTA_CONSUMO_PETS.md)

---

**Firmado:**  
Erick Renato Vega Cerón (Tesista Principal)  
2026-05-02

[LID]: ../bitacora/log_sesiones_trabajo_registradas.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../07_scripts/build_all.py

_Última actualización: `2026-05-15`._
