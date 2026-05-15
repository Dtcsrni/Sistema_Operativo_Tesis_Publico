<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0035 | 2026-05-05 | v1.0 | Validado -->

# DEC-0035: Optimización de VRAM y Poda de Modelos de Razonamiento

- **Fecha:** 2026-05-05
- **Estado:** **APROBADO**
- **Involucrados:** Tesista Principal, Antigravity (AI Agent)
- **Step ID:** [validación humana interna no pública]

## Contexto
Tras las pruebas de benchmarking masivo (PEV-02) ejecutadas en el nodo de control (RTX 4060 Ti 8GB), se ha identificado una degradación crítica del rendimiento en modelos que superan los 8B de parámetros. La latencia observada en modelos de 14B (~2.8 TPS) hace inviable su uso en flujos agénticos de tiempo real.

## Fundamentos Técnicos y Literatura
1. **ISO/IEC 25059:2023 (Eficiencia de Desempeño):** La norma establece que la eficiencia debe medirse en función del tiempo de respuesta y los recursos utilizados. El desbordamiento de VRAM (swapping) viola este principio al degradar el rendimiento en un factor de 20x.
2. **ISO/IEC 30141:2024 (Arquitectura IoT):** La delegación de tareas debe basarse en la capacidad del nodo. Un nodo saturado (VRAM excedida) compromete la fiabilidad de la red de inferencia distribuida.
3. **MLPerf Inference v3.1 Standards:** El umbral de usabilidad para agentes conversacionales se establece típicamente por encima de los 10-15 TPS. Los modelos de 14B en este hardware se sitúan por debajo de este estándar mínimo.

## Decisión
Se procede a la "Poda Tecnológica" de los siguientes modelos y sus artefactos relacionados:
- **Descartar:** `qwen3:14b`, `phi4:14b`, `qwen2.5-coder:14b`.
- **Consolidar:** Uso de `hermes3:8b` como modelo primario de razonamiento.
- **Reserva:** Mantener `mistral-nemo:12b` como único modelo pesado para tareas asíncronas de alta precisión.

## Consecuencias
- **Positivas:** Liberación de recursos de disco y VRAM, eliminación de riesgos de swapping accidental, simplificación del Router Adaptativo.
- **Negativas:** Ligera pérdida de capacidad de razonamiento extremo en tareas que requerían específicamente >14B parámetros.

## Evidencia
- Reportes de Benchmark: `runtime/pc_control/benchmarks/reports/` (Archivos pre-poda).
- Tasa de éxito: 51.7 TPS (8B) vs 2.8 TPS (14B).


---

## 🔗 Referencias Globales

- **[LID]:** Decisión registrada en canon / log_sesiones_trabajo_registradas.md
- **[GOV]:** Política de Gobernanza / AGENTS.md  
- **[AUD]:** Validación vía build_all.py / operabilidad humana


[LID]:  ruta local no pública /00_sistema_tesis/decisiones/2026-05-05_DEC-0035_optimizacion_vram_y_poda_de_modelos.md
[GOV]: AGENTS.md
[AUD]: build_all.py

_Última actualización: `2026-05-15`._
