<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-23_DEC-0001_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0001 Arquitectura base del sistema operativo de tesis

- Fecha: 2026-03-23
- Estado: aceptada
- Alcance: arquitectura
- Relacionada con bloques: B0
- Relacionada con hipótesis: HG

## Contexto

La tesis requiere una infraestructura documental y técnica que pueda crecer sin rehacerse, soporte semanas de alta carga cognitiva y mantenga trazabilidad entre decisiones, hipótesis, backlog, evidencia y redacción.

## Decisión

Se adopta una arquitectura de **repositorio privado como fuente de verdad** con artefactos fuente en Markdown, YAML y CSV, más un **dashboard HTML estático generado automáticamente** como vista operativa.

## Alternativas consideradas

1. Dashboard editable manualmente.
2. Aplicación web con base de datos y frontend dedicado.
3. Repositorio canónico con generación estática.

## Criterio de elección

La opción elegida minimiza complejidad operativa, preserva trazabilidad bajo control de versiones, reduce dependencia de infraestructura externa y facilita reproducibilidad. También permite exportes sanitizados futuros sin romper la base privada canónica.

## Métricas de Éxito

- [x] Validación operativa de la infraestructura.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Consistencia en auditorías automáticas.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] Firma digital GPG del tesista.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Validación de integridad estructural.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

  - **Soporte:** [Retroactivo | Step ID]
  - **Modo:** [Retroactivo | Confirmación Verbal]
  - **Fecha de Validación:** 2026-03-24
  - **Integridad:** `[hash_redactado]` 
  - **Fingerprint:** `[hash_redactado]` 
  - **Nivel de Auditoría:** Bajo
## Consecuencias

- Habilita validadores simples y exportes derivados reproducibles.
- Reduce riesgo de deriva entre fuente y visualización.
- Impone disciplina: los artefactos generados no deben editarse a mano.

## Trazabilidad de IA

- **Proveedor:** Google (DeepMind)
- **Modelo/Versión:** Gemini 1.5 Pro / Advanced Agentic Coding v1.0
- **Agente/Rol:** Antigravity (Assistant)
- **Nivel de Razonamiento:** alto
- **Prompts/Contexto clave:** Normalización de repositorio.

## Impacto en Presupuesto de Razonamiento

- **Consumo:** Bajo (Retroactivo)
- **Justificación:** Normalización de formato de trazabilidad.

## Implementación o seguimiento

- [x] Definir archivos canónicos de configuración
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Definir backlog y entregables iniciales
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Implementar scripts de validación y generación
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Abrir decisión específica para sanitización pública ([DEC-0015])
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

- Wilkinson et al. plantean principios FAIR para hacer datos y metadatos más localizables, accesibles, interoperables y reutilizables: [Scientific Data](https://www.nature.com/articles/sdata201618)
- Smith et al. establecen principios de citación de software útiles para trazabilidad de artefactos técnicos: [PeerJ Computer Science](https://peerj.com/articles/cs-86/)
- The Turing Way documenta prácticas reales de reproducibilidad, colaboración y gobernanza en proyectos de investigación: [The Turing Way](https://book.the-turing-way.org/)
- NASA Systems Engineering Handbook formaliza gestión de configuración, riesgos y trazabilidad en proyectos complejos: [NASA SP-2016-6105 Rev2](https://www.nasa.gov/reference/systems-engineering-handbook/)

[LID]: [ruta_local_redactada]
[GOV]: [ruta_local_redactada]
[AUD]: [ruta_local_redactada]
