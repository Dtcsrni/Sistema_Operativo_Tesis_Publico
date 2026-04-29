# Reporte de Modelos de Infraestructura Temprana (Fase B1)

Este documento preserva la evidencia técnica de los modelos utilizados para la validación inicial del hardware RK3588 antes de su eliminación para optimizar el almacenamiento.

## 1. TinyLlama-1.1B-Chat (RKLLM)
**Estado**: Validación de Driver Exitosa.

### Características
- **Formato**: `.rkllm` (v1.2.3 runtime compatible).
- **Cuantización**: W8A8 (Pesos de 8 bits / Activaciones de 8 bits).
- **Tamaño en Disco**: ~1.1 GB.
- **Uso de Memoria**: ~1.5 GB total (incluyendo OS).

### Benchmarks (RK3588 NPU)
| Métrica | Valor |
| :--- | :--- |
| **TTFT (Time to First Token)** | 145 - 155 ms |
| **TPS (Tokens Per Second)** | 18.0 - 18.5 tokens/s |
| **Estabilidad** | Alta (Carga continua por 5 min sin throttling) |

### Conclusiones de Prueba
Sirvió como el "Hello World" de la inferencia LLM en el nodo Edge. Demostró que el wrapper de `ctypes` es funcional y que la NPU puede manejar modelos Transformer con latencia sub-segundo.

---

## 2. ResNet18 (RKNN - Computer Vision)
**Estado**: Validación de Pipeline CV Exitosa.

### Características
- **Formato**: `.rknn` (Toolkit Lite 2 compatible).
- **Tarea**: Clasificación de imágenes (ImageNet).
- **Tamaño en Disco**: ~12 MB.

### Benchmarks
- **Inferencia**: ~1.2 ms por imagen.
- **Throughput**: >800 FPS (NPU core individual).

---

## 3. Registro de Eliminación
- **Archivos Afectados**: 
  - `runtime/models/edge/tinyllama_rkllm.rkllm`
  - `runtime/models/edge/resnet18_for_rk3588.rknn`
- **Motivo**: Migración a Llama-3.2-3B (Mayor capacidad de razonamiento) y optimización de espacio para el envolvente de 8GB RAM.

---
[LID]: 00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md
[GOV]: 00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md
[AUD]: historial interno no público/security_report_2026-04-28_0334.json

_Última actualización: `2026-04-29`._
