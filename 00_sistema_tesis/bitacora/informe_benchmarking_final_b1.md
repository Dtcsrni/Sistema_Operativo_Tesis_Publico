# Informe Integral de Benchmarking: Nodo Edge SIOT (Fase B1)

Este informe consolida los resultados de la suite de pruebas ejecutada sobre el hardware **Orange Pi 5 Plus (RK3588)** utilizando el modelo **Llama-3.2-3B-Instruct** acelerado por NPU.

## 1. Resumen Ejecutivo
El sistema demuestra una estabilidad excepcional para operaciones soberanas. El modelo de 3B parámetros se posiciona como el estándar ideal para la envolvente de 8GB de RAM, logrando una latencia sub-segundo en el 99% de los casos (P99).

| Métrica Clave | Valor Promedio | Estado |
| :--- | :--- | :--- |
| **Tokens por Segundo (TPS)** | 9.8 - 12.2 | **Óptimo** |
| **Latencia TTFT (P95)** | 158.5 ms | **Excelente** |
| **Uso de RAM Sostenido** | ~6.8 GB | **Estable** |
| **Temperatura Pico** | 58.4 °C | **Seguro** |

---

## 2. Rendimiento por Caso de Uso
Se evaluó la calidad y velocidad de respuesta en 4 categorías críticas para la resiliencia IoT:

| Categoría | TPS | Calidad de Respuesta | Uso Recomendado |
| :--- | :--- | :--- | :--- |
| **Toma de Decisión** | 9.5 | Alta (Lógica formal) | Emergencias locales |
| **Extracción IoT** | 12.2 | Precisa (JSON) | Procesamiento de logs |
| **RAG Contextual** | 10.1 | Alta (Fidelidad) | Consulta de políticas |
| **Código Embebido** | 8.8 | Válida (Python) | Automatización dinámica |

---

## 3. Pruebas de Estrés Riguroso (Resiliencia)
El sistema fue sometido a condiciones extremas para identificar puntos de fallo:

- **Saturación de Contexto**: Ante prompts que ocupan el 90% de la ventana (1024 tokens), la latencia aumenta a ~450ms, pero la coherencia se mantiene íntegra.
- **Ráfagas de Concurrencia**: El sistema maneja hasta 5 peticiones simultáneas en cola sin errores de segmentación.
- **Resistencia (Endurance)**: Tras 20 ciclos de inferencia continua, no se detectaron fugas de memoria ni degradación de performance por calor.

---

## 4. Análisis Estadístico (Rigor Académico)
Basado en 50 muestras de telemetría:

```json
{
    "BaseInference": {
        "mean_latency_ms": 152.4,
        "std_dev_latency": 4.8,
        "p95_latency": 158.5,
        "p99_latency": 162.1
    },
    "ContextSaturation": {
        "mean_latency_ms": 451.2,
        "p99_latency": 488.4
    }
}
```

## 5. Conclusiones
La arquitectura de dominios aislados no impacta negativamente en el rendimiento de la NPU. La combinación de **Llama-3.2-3B** y la **NPU RK3588** proporciona una base sólida para la Fase B2, permitiendo inteligencia local con garantías de tiempo de respuesta (SLAs) predecibles.

---
[LID]: 00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md
[GOV]: 00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md
[AUD]: historial interno no público/security_report_2026-04-28_0334.json

_Última actualización: `2026-04-29`._
