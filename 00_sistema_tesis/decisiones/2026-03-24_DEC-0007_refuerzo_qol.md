<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0007_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0007: Refuerzo QoL y Estandarización Final de B0

- **Fecha:** 2026-03-24
- **Estado:** aceptado
- **Autor(es):** Tesista / Sistema Operativo de Tesis

## Contexto

Tras estabilizar la base operativa y la wiki remota, se identificó la necesidad de reducir el error humano en el registro diario y mejorar la visibilidad de las dependencias estructurales de la tesis.

## Decisión

Se han implementado tres pilares de refuerzo para finalizar el Bloque 0:

1. **Scripts QoL (Quality of Life):** 
   - `new_log.py`: Automatiza la creación de bitácoras pre-llenando tareas pendientes.
   - `new_decision.py`: Automatiza la creación de ADRs con IDs secuenciales.
2. **Visualización Mermaid:** El generador de wiki (`build_wiki.py`) ahora inyecta bloques de código Mermaid para renderizar grafos de dependencias entre bloques y mapas de hipótesis de forma dinámica.
3. **Estandarización via Docker:** Se ha creado un `Dockerfile` que define el entorno exacto de ejecución, aislando la lógica del sistema de las particularidades del host (especialmente útil para la Orange Pi).
4. **Gestión de Entorno:** Integración de `python-dotenv` para manejar configuraciones sensibles o locales.

## Alternativas consideradas

1. Alternativa A
2. Alternativa B
3. Alternativa elegida

## Criterio de elección

Retroactivo: Decisión tomada durante la fase de infraestructura inicial.

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

- **Positivas:**
  - **Eficiencia:** Menos de 5 segundos para iniciar un registro de sesión o una decisión.
  - **Analitica Visual:** El tesista puede "ver" el avance de su investigación como un grafo vivo.
  - **Portabilidad:** El sistema puede moverse entre Windows, Linux y Orange Pi con la misma imagen Docker.
- **Negativas/Riesgos:**
  - Requiere mantener el `requirements-dev.txt` actualizado para la imagen Docker.
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

- [x] Implementación completada en Fase B0.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

N/A

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-03`._
