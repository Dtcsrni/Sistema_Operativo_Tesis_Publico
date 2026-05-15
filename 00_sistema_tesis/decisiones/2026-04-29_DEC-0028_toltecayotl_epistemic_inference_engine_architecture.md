<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0028 | 2026-04-29 | v1.0 | APROBADO -->

# DEC-0028: Arquitectura del Motor Epistémico de Inferencia "Toltecayotl"

| Campo | Valor |
| :--- | :--- |
| **ID** | DEC-0028 |
| **Título** | Arquitectura Distribuida y Gobernanza del Motor Epistémico "Toltecayotl" |
| **Fecha** | 2026-04-29 |
| **Estado** | APROBADO (Handshake implícito validación humana interna no pública) |
| **Contexto** | Necesidad de un motor de conocimiento académico distribuido con alta eficiencia en el borde. |

## 1. Declaración del Problema
El sistema requiere una infraestructura que permita la ingestión, procesamiento y recuperación de conocimiento académico de forma soberana, optimizando el uso de recursos limitados en hardware Edge (NPU) mientras se aprovecha la potencia de la PC para tareas pesadas de indexación y síntesis.

## 2. Decisión Arquitectónica (Topología Híbrida)
Se establece el uso de una arquitectura de **"Cerebro Unificado"** con los siguientes componentes:

1.  **Motor de Búsqueda Vectorial**: **Weaviate** actuará como el núcleo de GraphRAG, desplegado en el nodo de control (PC).
2.  **Nodo Edge (NPU)**: Ejecución de modelos optimizados (Qwen 2.5 1.5B W8A8) con **8k de Contexto** y **Prompt Caching** activo para respuesta inmediata.
3.  **Sincronización**: Protocolo de transferencia de vectores y fragmentos de conocimiento entre PC y Borde para garantizar operatividad offline parcial.

## 3. Estrategia de Ingestión
- **Formatos**: Soporte para PDF, Markdown, LaTeX y JSONL.
- **Procesamiento**: Extracción de entidades y relaciones para alimentar el grafo de conocimiento (GraphRAG).
- **Embeddings**: Uso de modelos multilingües (ej. BGE-M3) para asegurar la compatibilidad entre literatura técnica en inglés y redacción de tesis en español.

## 4. Implicaciones
- **Memoria**: El nodo Edge debe gestionar estrictamente la memoria CMA para evitar fragmentación.
- **Latencia**: El uso de Prompt Caching es mandatorio para mantener el TTFT por debajo de los 200ms en el borde.
- **Trazabilidad**: Toda respuesta generada por Toltecayotl debe incluir referencias al corpus de Weaviate con su respectivo hash de integridad.

## 5. Auditoría
Este documento queda bajo la protección de los guardrails del sistema. Cualquier modificación requiere una actualización del manifiesto de integridad.

## 6. Referencias Globales

- [LID] Ledger de sesiones registradas.
- [GOV] Política de gobernanza IA.
- [AUD] Auditoría local reproducible.

[LID]:  ruta local no pública 
[GOV]:  ruta local no pública 
[AUD]:  ruta local no pública 

---
**Firmado:**
Erick Renato Vega Ceron (Tesista Principal)
2026-04-29

_Última actualización: `2026-05-15`._
