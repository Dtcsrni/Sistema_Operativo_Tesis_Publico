# Bitácora de sesión 2026-04-08

- **ID de Sesión:** codex-local-20260408-dec0022-desktop-edge
- **Cadena de Confianza (Anterior):** `sha256/6098e4bbcbc5a7cf4e27e36191f486677f927c6fc6e22413de1715423dde4719`
- **Bloque principal:** B0
- **Tipo de sesión:** diseño | implementación | validación

## Infraestructura de Sesión
- **OS:** Windows 11
- **Python:** 3.14.3
- **Herramientas Clave:** Codex, `tesis.py`, `build_all.py`, Git, Visual Studio Code

## Objetivo de la sesión
Formalizar la arquitectura operativa con escritorio primario y Orange Pi como nodo edge integrado, dejando la decisión, la documentación, el manifiesto operativo y la trazabilidad canónica consistentes.

## Tareas del día
- [x] Emitir una decisión nueva para fijar el modelo `desktop-first`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Actualizar arquitectura, operación humana y topología de almacenamiento para distinguir escritorio y edge.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Agregar un manifiesto máquina-legible para la topología operativa.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Registrar la evidencia fuente de conversación y promover el validación humana interna no pública enlazado a `DEC-0022`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Reauditar y rematerializar el sistema tras los cambios.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Trabajo realizado
- Se creó [DEC-0022](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-04-08_DEC-0022_arquitectura_operativa_escritorio_primario_y_orange_pi_edge.md) para declarar explícitamente al escritorio con VS Code como estación principal de autoría y a la Orange Pi como nodo edge operativo.
- Se actualizaron la arquitectura general, el manual de operación humana y la topología de almacenamiento para reflejar el flujo `desktop_workspace -> orange_pi_edge`.
- Se añadió `manifests/operational_topology.yaml` y se extendió `manifests/storage_layout.yaml` con la topología operativa máquina-legible.
- Se reforzaron pruebas documentales y de manifiesto para verificar el modelo `desktop-first` y la restricción de no usar workspace montado por red como flujo principal.
- Se registró la evidencia fuente de la instrucción humana en evento interno no público y se promovió validación humana interna no pública con referencia a `DEC-0022`.

## Evidencia Técnica e Integridad
- **Commits:** no aplicado en esta sesión
- **Archivos Clave:** `00_sistema_tesis/decisiones/2026-04-08_DEC-0022_arquitectura_operativa_escritorio_primario_y_orange_pi_edge.md`, `docs/02_arquitectura/arquitectura-general.md`, `00_sistema_tesis/manual_operacion_humana.md`, `docs/02_arquitectura/topologia-de-almacenamiento.md`, `manifests/operational_topology.yaml`, `manifests/storage_layout.yaml`, `tests/test_domain_integration_security.py`, `tests/test_domain_isolation.py`
- **Validación del Sistema:** [x] Auditoría `build_all.py` aprobada.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Uso de IA y Gobernanza
- **Proveedor:** proveedor de IA no publicado
- **Modelo/Versión:** modelo de IA no publicado
- **Objetivo:** Implementar y dejar trazable la precisión arquitectónica escritorio primario + Orange Pi edge integrado.
- **Nivel de Razonamiento:** medio
- **Alineación Ética:**
    - [x] Transparencia (NIST RMF)
      - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
    - [x] Soberanía Humana (UNESCO)
      - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
    - [x] Responsabilidad (ISO 42001)
      - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

### Validación de Soberanía (Handshake)
- **Pregunta Crítica:** Instrucción humana directa registrada sin pregunta previa del agente.
- **Respuesta Erick Vega:** "PLEASE IMPLEMENT THIS PLAN:" seguido del plan de arquitectura operativa escritorio primario + Orange Pi edge integrado.
- **Criterio de Aceptación:** [x] Validado.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** [validación humana interna no pública]
  - **Texto exacto de confirmación verbal:** "PLEASE IMPLEMENT THIS PLAN: # Plan de Arquitectura Operativa Escritorio Primario + Orange Pi Edge Integrado ## Resumen Formalizar el flujo oficial del sistema con estas reglas base: - El **PC de escritorio con VS Code** es la estación principal de autoría, diseño, análisis, construcción documental y mantenimiento del repositorio soberano. - La **Orange Pi** queda como **nodo edge operativo** para `edge_iot` y para las capacidades locales que convenga ejecutar ahí por hardware, proximidad al entorno físico o control del stack IoT. - La integración entre ambos se fija por **sincronización Git + artefactos/contratos explícitos**, no por edición principal en la Orange Pi ni por montaje remoto compartido. - La Orange Pi puede operar como nodo técnico de experimentación/control edge, pero **no sustituye** al escritorio como superficie principal de tesis ni como sede normal de decisiones arquitectónicas."
  - **Hash de confirmación verbal:** `hash omitido:omitido`
  - **Fuente de verdad de confirmación:** `00_sistema_tesis/canon/events.jsonl :: validación humana interna no pública :: human_validation.confirmation_text`
  - **Hash (Contenido):** `hash omitido:omitido`
  - **Fingerprint:** `hash omitido:omitido`
  - **Nivel de Riesgo:** Alto
  - **Modo:** Confirmación Verbal
  - **Pregunta crítica o disparador:** Implementar el plan de arquitectura operativa escritorio primario + Orange Pi edge integrado.
  - **Fuente de verdad de evidencia fuente:** `00_sistema_tesis/canon/events.jsonl :: evento interno no público :: conversation_source_registered.quoted_text`

## Economía de uso
- Presupuesto vs Avance: Se concentró el cambio en una decisión nueva, documentación puntual, un manifiesto nuevo y pruebas de consistencia, evitando rediseños innecesarios.
- Qué se evitó: convertir la Orange Pi en estación principal de trabajo o introducir un flujo ambiguo de workspace compartido por red.
- Qué ameritaría subir razonamiento en la siguiente sesión: contratos más detallados de despliegue escritorio -> edge y reglas de sincronización operativa por tipo de artefacto.

## Siguiente paso concreto
Traducir esta frontera arquitectónica en procedimientos de despliegue y sincronización más finos entre el workspace de escritorio y el nodo edge de Orange Pi.

[LID]: log_sesiones_trabajo_registradas.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../07_scripts/build_all.py

_Última actualización: `2026-04-25`._
