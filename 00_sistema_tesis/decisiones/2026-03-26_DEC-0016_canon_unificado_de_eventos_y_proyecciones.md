<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-26_DEC-0016_ | Versión: 1.0.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0016 Canon unificado de eventos y proyecciones derivadas

- Fecha: 2026-03-26
- Estado: aceptada
- Alcance: arquitectura | operación
- Relacionada con bloques: B0, B1
- Relacionada con hipótesis: HG

## Contexto

El sistema operativo de tesis acumuló varias fuentes operativas paralelas para una misma realidad de gobernanza: ledger, matriz, bitácoras, `ia_journal.json` y `sign_offs.json`. Esto elevó el costo de mantenimiento, volvió frágil el enforcement del gate y mezcló evidencia humana con vistas Markdown derivadas. La soberanía seguía siendo fuerte, pero el punto de control estaba demasiado cerca del diff textual y no del hecho canónico validado.

## Decisión

Adoptar un **canon unificado append-only** en `00_sistema_tesis/canon/events.jsonl` como única fuente operativa de trazabilidad humana y actividad agéntica. A partir de este canon, el sistema materializa como proyecciones derivadas:

1. `log_conversaciones_ia.md`
2. `matriz_trazabilidad.md`
3. bitácoras de sesión
4. `ia_journal.json`
5. `sign_offs.json`

El validación humana interna no pública se conserva como identificador semántico oficial de validación humana, ahora registrado como evento canónico de tipo `human_validation`.
Cada evento `human_validation` debe contener además la cita exacta del enunciado humano relevante, su hash SHA-256 y una ruta explícita de fuente de verdad para que la confirmación verbal pueda ser auditada por humanos sin depender de reconstrucciones narrativas.

## Alternativas consideradas

1. Mantener la arquitectura actual y endurecer validadores puntuales.
2. Separar ledger y matriz pero conservar bitácoras y journal como fuentes independientes.
3. **Canon unificado de eventos con proyecciones derivadas.**

## Criterio de elección

La alternativa elegida reduce duplicidad operativa, baja el riesgo de inconsistencia entre artefactos y mueve el control humano a la capa correcta: un evento canónico validado y enlazado, no una representación Markdown mutable.

## Métricas de Éxito

- [x] Existencia de `00_sistema_tesis/canon/events.jsonl` como fuente única para trazabilidad humana, journal agéntico y firmas de artefactos.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Materialización reproducible de ledger, matriz, bitácoras, `ia_journal.json` y `sign_offs.json` desde el canon.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Governance gate validando canon y drift de proyecciones primarias.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] El tesista instruye explícitamente implementar el rediseño v2 del sistema operativo de tesis.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** [validación humana interna no pública]
  - **Pregunta crítica o disparador:** Instrucción humana directa registrada sin pregunta previa del agente.
  - **Texto exacto de confirmación verbal:** "PLEASE IMPLEMENT THIS PLAN"
  - **Hash de confirmación verbal:** `hash omitido:omitido`
  - **Fuente de verdad de confirmación:** `00_sistema_tesis/canon/events.jsonl :: validación humana interna no pública :: human_validation.confirmation_text`
  - **Integridad:** `hash omitido:omitido`
  - **Fingerprint:** `Hash omitido por seguridad`
  - **Nivel de Auditoría:** Alto
  - **Modo:** Confirmación Verbal
  - **Fecha de Validación:** 2026-03-26

## Consecuencias

- **Positivas:** Menor deriva operativa, menor acoplamiento entre scripts y enforcement más claro sobre eventos reales, incluyendo confirmaciones verbales verificables como evidencia científica primaria.
- **Negativas:** Se introduce una migración arquitectónica que exige compatibilidad temporal y más pruebas.
- **Deuda explícita:** Los wrappers heredados deben permanecer durante la transición para no romper hábitos ni hooks existentes.

## Trazabilidad de IA

- **Proveedor:** proveedor de IA no publicado
- **Modelo/Versión:** modelo de IA no publicado
- **Agente/Rol:** Codex
- **Nivel de Razonamiento:** alto
- **Prompts/Contexto clave:** Instrucción explícita del tesista para implementar el plan "Rediseño v2 del Sistema Operativo de Tesis" con canon unificado, CLI `tesis.py`, proyecciones derivadas y gate centrado en eventos.

## Impacto en Presupuesto de Razonamiento

- **Consumo:** Alto.
- **Justificación:** La migración requiere consolidar varios artefactos históricos, preservar compatibilidad y rediseñar enforcement sin romper trazabilidad existente.

## Implementación o seguimiento

- [x] Crear el canon `00_sistema_tesis/canon/events.jsonl` y su `state.json`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Introducir la CLI `07_scripts/tesis.py` y wrappers de compatibilidad.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Reorientar `governance_gate.py` al canon y a la detección de drift de proyecciones.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Actualizar DEC-0014 para reconocer el modelo canónico v2.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

- [DEC-0014](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- Event sourcing y snapshots derivados para auditoría reproducible.
- Prácticas FAIR y trazabilidad de artefactos reproducibles en investigación.

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-03`._
