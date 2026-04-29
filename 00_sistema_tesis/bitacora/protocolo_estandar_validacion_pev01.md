# Protocolo Estándar de Validación SIOT-Edge (PEV-01)

Este documento define el procedimiento mandatorio para la ejecución de benchmarks en el nodo Edge, garantizando la reproducibilidad y validez estadística de los resultados reportados en la tesis.

## 0. Regla transversal PEV-02

Desde 2026-04-28, todo benchmark de PC, Edge, NPU, Ollama, llama.cpp u OpenClaw debe emitir evidencia primaria bajo el contrato `BenchmarkRun`:

- **Fuente primaria**: JSONL append-only en `runtime/<nodo>/benchmarks/runs/*.jsonl`.
- **Integridad**: cada registro debe incluir `record_hash` y `previous_record_hash` calculados con SHA-256 sobre JSON canonico.
- **Espejo operativo**: OpenClaw puede guardar un resumen en SQLite, pero la evidencia primaria es el JSONL.
- **Validez**: los registros `simulation_only` son utiles para pruebas de software, pero son `invalid_for_scientific_claim`.
- **Modelo PC primario**: `mistral-nemo:12b` para `desktop_compute` y `pc_native_llamacpp`.
- **Referencias metodologicas**: se adoptan principios de MLCommons MLPerf Inference, compatibilidad con EleutherAI `lm-evaluation-harness` y reporte transparente estilo Stanford HELM, sin afirmar certificacion oficial MLPerf.

## 1. Condiciones de Contorno
- **Estado Inicial**: El nodo debe haber estado en reposo (`idle`) por al menos 10 minutos.
- **Temperatura Base**: < 45°C.
- **Memoria**: Sin procesos secundarios activos (solo servicios esenciales de SIOT).

## 2. Procedimiento de Ejecución
1.  **Fase de Calentamiento (Warm-up)**: Se ejecutan 5 inferencias no registradas para estabilizar la frecuencia del reloj de la NPU y el estado de la caché del sistema.
2.  **Fase de Medición**:
    - **N = 50 muestras** por categoría.
    - **Intervalo**: 500ms entre muestras para evitar saturación de bus.
3.  **Captura de Telemetría**: Se registra la temperatura y el uso de CPU/RAM *antes* de cada muestra para detectar correlaciones entre calor y latencia.

## 3. Criterios de Validez Matemática
- **Intervalo de Confianza**: Se aplica un nivel de confianza del **95% (Z = 1.96)**.
- **Filtrado de Outliers**: Valores que excedan 3 desviaciones estándar (3-sigma) deben ser marcados como anomalías de sistema (no de modelo).
- **Margen de Error**: El reporte debe incluir explícitamente el margen de error calculado: `Mean +/- Error`.

## 4. Auditoría de Resultados
Todo reporte de benchmark (`benchmark_latest.json`) debe ir acompañado por su log raw (`standardized_run.jsonl`) para permitir la verificación independiente de la varianza.

## 5. Almacenamiento canonico de resultados

Los reportes `scientific_report_*.json`, dashboard y wiki son derivados. La cadena de custodia valida se verifica sobre:

1. `run_header`: entorno, git commit, modelo, promptset, comando, protocolo y referencias.
2. `sample`: warmup o medicion individual con latencia, tokens/s, memoria, GPU, hashes de entrada/salida y estado.
3. `run_summary`: estadisticos agregados, estado final y validez cientifica.
4. `index.json`: ultimo benchmark valido por nodo y ruta del JSONL primario.

---
[LID]: 00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md
[GOV]: 00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md
[AUD]: historial interno no público/security_report_2026-04-28_0334.json

_Última actualización: `2026-04-29`._
