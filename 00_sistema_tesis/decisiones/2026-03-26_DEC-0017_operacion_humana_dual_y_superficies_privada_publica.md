<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-26_DEC-0017_ | Versión: 1.0.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0017 Operación Humana Dual y Superficies Privada/Pública

- Fecha: 2026-03-26
- Estado: aceptada
- Alcance: arquitectura | operación | gobernanza
- Relacionada con bloques: B0, B1
- Relacionada con hipótesis: HG

## Contexto

El sistema operativo de tesis ya contaba con canon fuerte, guardrails y auditoría, pero seguía siendo costoso de operar para humanos nuevos o no continuos. Además, la necesidad de una capa pública segura exigía separar explícitamente la operación privada soberana de la exposición externa.

## Decisión

Adoptar un modelo de **operación humana dual** con dos superficies explícitas:

1. **Superficie privada:** canon, backlog, decisiones, bitácora, auditoría, evidencia y configuración íntegra.
2. **Superficie pública:** bundle público curado, derivado y reproducible para divulgación y evaluación externa.

Como regla estructural, todo flujo crítico debe tener una **vía manual explícita** y la IA queda institucionalizada como apoyo opcional, nunca como requisito operativo.
La capa humana visible del sistema debe mostrar también la cita exacta de la confirmación verbal relevante, su hash y la fuente canónica de verdad cuando un cambio o decisión dependa de autorización humana.

## Alternativas consideradas

1. Mantener el sistema actual y solo documentarlo mejor.
2. Endurecer controles sin rediseñar la experiencia humana.
3. **Reorganizar el sistema como operación humana dual con capa pública sanitizada.**

## Criterio de elección

La alternativa elegida reduce dependencia cognitiva de la IA, mejora legibilidad para tesista, colaboradores y jurado, y ordena la exposición pública sin romper el canon no público.

## Métricas de Éxito

- [x] Existencia de un manual operativo humano y comandos guiados (`status`, `doctor`, `next`, `publish`).
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Separación explícita entre superficie canónica no pública y pública en documentación, wiki y dashboard.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Validación automática de operabilidad humana y publicación pública en `build_all.py`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] El tesista ordena implementar la capa humana dual, la publicación sanitizada y la simplificación operativa.
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

- **Positivas:** hace el sistema más explicable, retirable y auditable por humanos sin rebajar trazabilidad.
- **Negativas:** aumenta el número de artefactos derivados y exige mantener consistencia documental.
- **Deuda explícita:** habrá que vigilar que la capa humana no duplique información que ya vive en fuentes canónicas.

## Trazabilidad de IA

- **Proveedor:** proveedor de IA no publicado
- **Modelo/Versión:** modelo de IA no publicado
- **Agente/Rol:** Codex
- **Nivel de Razonamiento:** alto
- **Prompts/Contexto clave:** Implementación autorizada del plan de operación humana dual, publicación sanitizada y simplificación del sistema.

## Impacto en Presupuesto de Razonamiento

- **Consumo:** Alto.
- **Justificación:** El cambio afecta CLI, validadores, decisiones, documentación, wiki, dashboard y flujo de publicación pública.

## Implementación o seguimiento

- [x] Incorporar manual de operación humana y rutas guiadas de retoma, auditoría y publicación.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Extender `tesis.py` con `doctor`, `next` y `publish` sin romper compatibilidad.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Actualizar README, wiki, dashboard, backlog y riesgos para reflejar el modelo dual.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

- [DEC-0014](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- [DEC-0015](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0015_protocolo_de_sanitización_para_exposición_pública.md)
- [DEC-0016](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-26_DEC-0016_canon_unificado_de_eventos_y_proyecciones.md)

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-03`._
