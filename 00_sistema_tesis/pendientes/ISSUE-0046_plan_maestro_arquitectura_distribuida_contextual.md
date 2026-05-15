# Plan Maestro: Arquitectura Distribuida y Evolución Contextual (validación humana interna no pública)

<!-- SISTEMA_TESIS:PROTEGIDO -->
**ID del Plan:** ISSUE-0046
**Estado:** COMPLETADO
**Prioridad:** CRÍTICA
**Dueño:** Tesista Principal / Sistema Agéntico

## 1. Visión General
Este plan maestro define la hoja de ruta para transformar el Sistema Operativo de Tesis en una plataforma de investigación distribuida, resiliente y capaz de aprendizaje persistente a través de múltiples sesiones y agentes. Se basa en los principios de soberanía de datos, eficiencia en el Edge (NPU) y trazabilidad inmutable.

## 2. Fases de Implementación Evolutiva

### Fase I: Infraestructura de Sesiones y Contexto (Completada - validación humana interna no pública)
*   **Objetivo**: Implementar el Framework de Sesiones Multicontextuales (MSCF).
*   **Hitos**:
    - [x] Creación del directorio raíz de sesiones: `00_sistema_tesis/sesiones/`.
    - [x] Actualización de `07_scripts/utils/new_session.py` para soportar arquetipos (Investigación, Operaciones, Fiscalía, Síntesis, Diálogo).
    - [x] Estandarización del descriptor `session_context.json` con niveles de privacidad.
    - [x] Implementación de la Capa de Diálogo: Protección de OSINT/Privacidad en charlas sociales/filosóficas.

### Fase II: Persistencia Epistémica Acumulativa (Memoria) (Completada - validación humana interna no pública)
*   **Objetivo**: Garantizar que el aprendizaje de una sesión sea heredable por la siguiente.
*   **Hitos**:
    - [x] Implementación de **"Cápsulas de Conocimiento"** (.capsule) al cierre de cada sesión académica.
    - [x] Desarrollo del **Filtro de Relevancia Epistémica**: Extracción automatizada de valor para la tesis desde sesiones de arquetipo `Diálogo`, garantizando anonimización de datos sensibles.
    - [x] Integración de las cápsulas en el **Índice Maestro de Ingestión**.
    - [x] Desarrollo del motor de búsqueda de "Nexos Cruzados" para vincular temas aparentemente no relacionados.

### Fase III: Optimización de la Inteligencia Distribuida (Hardware) (Completada - validación humana interna no pública)
*   **Objetivo**: Maximizar el aprovechamiento del NPU en el Edge y la GPU en la PC mediante algoritmos adaptativos.
*   **Hitos**:
    - [x] Implementación del **Enrutador de Capacidades (Capability Router)** con lógica **Sistema 1 (Edge/NPU)** vs **Sistema 2 (PC/GPU)**.
    - [x] Desarrollo de `07_scripts/ops/bench_distribuido.py` para automatización de benchmarks comparativos.
    - [x] Implementación de **Escalación por Confianza**: Si el modelo en el Edge reporta baja confianza, la tarea se re-enruta automáticamente a la PC.
    - [x] Fine-tuning de parámetros de cuantización INT8 para el modelo 1.5B en el nodo Orange Pi.

### Fase IV: Orquestación Multia-Agente (Mission Control) (Completada - validación humana interna no pública)
*   **Objetivo**: Coordinar múltiples agentes especializados trabajando en paralelo.
*   **Hitos**:
    - [x] Despliegue del Dashboard de Mission Control (SQLite/Next.js) en `04_implementacion/control_mission/`.
    - [x] Protocolo de comunicación Inter-Agente (Local-First): `TASK_COMPLETE` / `PROGRESS_UPDATE`.
    - [x] Automatización de la **"Auditoría de Pares"** entre agentes (El Fiscal validando al Cronista).

## 3. Estándares y Gobernanza
*   **Trazabilidad**: Cada cambio debe estar vinculado a un VAL-STEP y registrado en el Ledger.
*   **Integridad**: El uso de SHA-256 es mandatorio para toda cápsula de conocimiento.
*   **Soberanía**: El nodo Edge debe ser funcionalmente autónomo en escenarios de desconexión.

## 4. Matriz de Riesgos
| Riesgo | Impacto | Mitigación |
| :--- | :--- | :--- |
| Contaminación de Contexto | Alto | Aislamiento estricto por Arquetipos de Sesión. |
| Deriva de Versiones PC/Edge | Medio | Sincronización Física Integral (validación humana interna no pública) semanal. |
| Saturación de Memoria en Edge | Medio | Uso de Base de Datos Vectorial local (Weaviate). |

---
**Aprobación requerida para iniciar Fase I.**

_Última actualización: `2026-05-15`._
