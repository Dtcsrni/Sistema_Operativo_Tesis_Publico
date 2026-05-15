<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0036 | 2026-05-05 | v1.0 | Validado -->

# DEC-0036: Restricción de RAM en Nodo Edge y Selección de Modelos

- **Fecha:** 2026-05-05
- **Estado:** **APROBADO**
- **Involucrados:** Tesista Principal, Antigravity (AI Agent)
- **Step ID:** [validación humana interna no pública]

## Contexto
Se ha verificado empíricamente que el hardware de borde Orange Pi 5 Plus utilizado en el proyecto dispone de **8GB de RAM LPDDR4x**, corrigiendo asunciones previas de 16GB. Esta capacidad física impone un límite estricto a los modelos LLM que pueden coexistir con el sistema operativo y los daemons de telemetría.

## Fundamentos Técnicos
1. **OOM (Out of Memory) Risk:** Un modelo de 8B parámetros en cuantización de 4 bits ocupa ~5GB. Sumando el contexto (KV Cache) y el sistema operativo (~1.5GB), el margen de maniobra es <1GB, lo que eleva el riesgo de fallos críticos durante picos de inferencia.
2. **Coexistencia de Servicios:** El nodo Edge debe ejecutar no solo la inferencia, sino también `hw_status_daemon.py`, el Gateway MQTT y el cliente LoRa. La saturación de RAM comprometería la estabilidad de la red de sensores.

## Decisión
1.  **Modelo Techo:** Se establece a **Llama-3.2-3B (RKLLM)** como el modelo de mayor tamaño permitido para ejecución operativa sostenida en el nodo Edge.
2.  **Exclusión de 8B:** Se descarta el uso de modelos de 8B o superiores en el Orange Pi 5 Plus para tareas de tiempo real, delegando estas al nodo de control (PC) vía ruteo adaptativo.
3.  **Configuración de Swap:** Se prohíbe el uso de swap en tarjeta SD/eMMC para compensar RAM en inferencia, para evitar la degradación de latencia y desgaste de hardware.

## Consecuencias
- **Positivas:** Estabilidad determinista del nodo Edge, eliminación de latencias impredecibles por swapping, mayor presupuesto de memoria para agentes de telemetría.
- **Negativas:** Limitación del razonamiento local; las tareas complejas DEBEN ser delegadas al PC.

## Evidencia
- Memoria total detectada: `8,320,172,032 bytes` (Reporte BENCH-20260428).
- Carga base del sistema: ~1.2GB.

---

## Cláusula de Excepción Experimental
Se autoriza la ejecución controlada de modelos de hasta **7B parámetros** (específicamente `DeepSeek-R1-Distill-Qwen-7B`) bajo las siguientes condiciones estrictas:
1.  **Cuantización:** Mínimo `W4A16`.
2.  **Aislamiento:** Cierre de todos los servicios no esenciales en el Orange Pi.
3.  **Monitoreo:** Registro obligatorio de telemetría CMA (Contiguous Memory Allocator) durante la inferencia.
4.  **Propósito:** Evaluación de capacidades de razonamiento "System 2" vs. estabilidad operativa.


---

## 🔗 Referencias Globales

- **[LID]:** Decisión registrada en canon / log_sesiones_trabajo_registradas.md
- **[GOV]:** Política de Gobernanza / AGENTS.md  
- **[AUD]:** Validación vía build_all.py / operabilidad humana


[LID]:  ruta local no pública /00_sistema_tesis/decisiones/2026-05-05_DEC-0036_restriccion_ram_edge.md
[GOV]: AGENTS.md
[AUD]: build_all.py

_Última actualización: `2026-05-15`._
