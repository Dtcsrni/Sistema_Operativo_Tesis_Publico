<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0003_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0003 Economía de uso y selección de razonamiento

- Fecha: 2026-03-24
- Estado: aceptada
- Alcance: operación
- Relacionada con bloques: B0
- Relacionada con hipótesis: HG

## Contexto

El sistema operativo de tesis depende de interacciones con IA y automatización asistida bajo límites prácticos de uso. Sin una política explícita, el proyecto corre el riesgo de gastar presupuesto en exploración redundante, sobrerazonamiento o tareas mecánicas que no justifican alto consumo.

## Decisión

Se adopta una política de economía de uso orientada a maximizar avance funcional verificable por unidad de consumo. La selección de nivel de razonamiento debe seguir el principio de suficiencia mínima: usar el menor nivel que produzca una salida adecuada para la tarea, escalando solo cuando haya ambigüedad real, alta carga de restricciones, alto costo del error o necesidad de consolidación extensa.

## Alternativas consideradas

1. Tratar todo trabajo relevante con razonamiento alto por precaución.
2. Elegir el nivel de razonamiento de manera intuitiva sin registro explícito.
3. Definir una política de suficiencia mínima con criterios de escalamiento y registro operativo.

## Criterio de elección

La política explícita reduce desperdicio de uso, mejora previsibilidad operativa y fuerza a distinguir entre tareas mecánicas, analíticas y fundacionales. También protege la calidad metodológica al reservar razonamiento alto para puntos donde realmente aporta más que su costo.

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

- Se vuelve obligatorio justificar de forma breve el nivel de razonamiento utilizado en sesiones con IA relevantes.
- La bitácora captura relación entre presupuesto de uso y avance funcional.
- El sistema podrá aprender con el tiempo qué tipos de tareas justifican mayor consumo.
- Se desincentiva exploración amplia sin objetivo operativo inmediato.

## Trazabilidad del trabajo asistido

- **Proveedor:** Google (DeepMind)
- **Modelo/Versión:** Gemini 1.5 Pro / Advanced Agentic Coding v1.0
- **Agente/Rol:** Antigravity (Assistant)
- **Nivel de Razonamiento:** alto
- **Prompts/Contexto clave:** Normalización de repositorio.

## Impacto en Presupuesto de Razonamiento

- **Consumo:** Bajo (Retroactivo)
- **Justificación:** Normalización de formato de trazabilidad.

## Implementación o seguimiento

- [x] Actualizar `00_sistema_tesis/config/ia_gobernanza.yaml`
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Actualizar plantilla de bitácora con registro de economía de uso
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Registrar ejemplo inicial en bitácora
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Actualizar backlog y riesgos asociados
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [ ] Evaluar en resúmenes semanales si la política reduce retrabajo y mejora cierre de piezas funcionales
  - [ ] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

- proveedor de IA no publicado recomienda ajustar el esfuerzo de razonamiento al tipo de tarea y escalar solo cuando la dificultad lo justifique: [GPT-5.4](https://developers.openai.com/api/docs/models/gpt-5.4)
- La guía de prompting para GPT-5 enfatiza instrucciones claras, contratos de salida y escalamiento de complejidad según necesidad real: [Prompt guidance](https://developers.openai.com/api/docs/guides/prompt-guidance)
- The Turing Way favorece procesos reproducibles y decisiones explícitas sobre herramientas y flujos de trabajo: [The Turing Way](https://book.the-turing-way.org/)

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-13`._
