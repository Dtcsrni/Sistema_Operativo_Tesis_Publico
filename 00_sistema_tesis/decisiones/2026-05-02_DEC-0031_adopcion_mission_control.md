<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0031 | 2026-05-02 | v1.0 | Propuesta -->

# DEC-0031 Adopción de Mission Control para Supervisión Agéntica

- Fecha: 2026-05-02
- Estado: propuesta
- Alcance: arquitectura | operación
- Relacionada con bloques: B1, B5
- Relacionada con hipótesis: HG, H2

## Contexto

Con la expansión de la red de agentes (OpenClaw, Toltecayotl, Bots de Telegram/Matrix) distribuidos entre el PC y el nodo Edge, se vuelve crítica la necesidad de un punto centralizado de observación y mando. La falta de una interfaz visual en tiempo real dificulta la detección de derivas operativas y la gestión de colas de tareas complejas.

## Decisión

Implementar e integrar el módulo **OpenClaw Mission Control** como el orquestador visual y centro de mando del sistema.

1.  **Tecnología**: Basado en el stack React + Next.js + Convex (Real-time backend).
2.  **Ubicación**: El código residirá en `04_implementacion/control_mission/`.
3.  **Integración de Datos**: Utilizará los sinks de telemetría de OpenClaw y los eventos del Motor Epistémico Toltecayotl.
4.  **Control Humano**: El dashboard incluirá botones de "Kill Switch" y validación manual de tareas antes de su ejecución en el nodo Edge.
5.  **Local-First**: Se priorizará la ejecución de la instancia de Convex en modo local o mediante el CLI de desarrollo para mantener la soberanía de los datos (DEC-0030).

## Alternativas consideradas

1.  Uso de Grafana/Prometheus (Rechazado por ser demasiado enfocado a métricas de infraestructura y no a orquestación de tareas agénticas).
2.  Logs de terminal puros (Insuficientes para supervisión de múltiples nodos).
3.  **OpenClaw Mission Control (Elegida)**: Diseñado específicamente para el ecosistema de agentes que estamos utilizando.

## Criterio de elección

Ofrece la mejor integración nativa con OpenClaw y permite una visualización rica de grafos de tareas, necesaria para el Motor Epistémico.

## Criterio de Aceptación Humana

- [ ] El Tesista aprueba la arquitectura de Mission Control.
  - [ ] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** [validación humana interna no pública]
  - **Texto exacto de confirmación verbal:** "openclaw-mission-control"
  - **Hash de confirmación verbal:** `hash omitido:omitido`
  - **Fuente de verdad de confirmación:** `00_sistema_tesis/canon/events.jsonl :: validación humana interna no pública :: human_validation.confirmation_text`

## Referencias
- [DEC-0014: Protocolo Humano-Agente](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- [DEC-0030: Local-First Architecture](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-05-01_DEC-0030_adopcion_arquitectura_local_first.md)

[LID]:  ruta local no pública 
[GOV]:  ruta local no pública 
[AUD]:  ruta local no pública

_Última actualización: `2026-05-15`._
