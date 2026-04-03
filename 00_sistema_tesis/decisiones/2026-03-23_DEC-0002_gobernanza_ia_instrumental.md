<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-23_DEC-0002_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0002 Gobernanza de IA instrumental y registro de uso

- Fecha: 2026-03-23
- Estado: aceptada
- Alcance: operación
- Relacionada con bloques: B0
- Relacionada con hipótesis: HG

## Contexto

La tesis requiere apoyo de IA para acelerar tareas documentales, analíticas y de automatización, pero sin diluir autoría, validación humana ni integridad metodológica.

## Decisión

Se establece un marco agnóstico de gobernanza de IA con cuatro categorías de uso, revisión humana proporcional al riesgo y registro obligatorio de uso cuando la IA afecte código, redacción sustantiva, interpretación o decisiones.

## Alternativas consideradas

1. No documentar uso de IA.
2. Permitir uso amplio con validación informal.
3. Gobernanza explícita con validación y trazabilidad.

## Criterio de elección

El enfoque explícito reduce riesgos de alucinación, fuga de contexto y dependencia cognitiva. También ayuda a que la IA funcione como apoyo formativo y no como sustituto del aprendizaje.

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
  - **Integridad:** `Hash omitido por seguridad` 
  - **Fingerprint:** `Hash omitido por seguridad` 
  - **Nivel de Auditoría:** Bajo
## Consecuencias

- Aumenta disciplina de revisión.
- Vuelve auditable el uso de IA en etapas sensibles.
- Añade una pequeña carga administrativa, compensada por menor riesgo metodológico.

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

- [x] Definir archivo `ia_gobernanza.yaml`
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Incorporar sección de IA en plantilla de bitácora
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [ ] Evaluar más adelante una vista sanitizada de uso de IA para anexos o metodología
  - [ ] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

- NIST AI RMF 1.0 propone gobernanza, medición y gestión de riesgos de IA: [NIST](https://www.nist.gov/itl/ai-risk-management-framework)
- UNESCO fija principios de supervisión humana, transparencia y responsabilidad para IA: [UNESCO](https://www.unesco.org/en/legal-affairs/recommendation-ethics-artificial-intelligence)
- The Turing Way ofrece pautas prácticas de colaboración responsable y escritura asistida: [The Turing Way](https://book.the-turing-way.org/)

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-03`._
