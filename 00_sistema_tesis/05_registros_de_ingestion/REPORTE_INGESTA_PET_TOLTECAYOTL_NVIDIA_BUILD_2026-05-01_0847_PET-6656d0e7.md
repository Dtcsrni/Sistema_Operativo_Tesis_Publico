# Informe de Ingestión Epistémica: pet_toltecayotl_nvidia_build.zip

**Identificador de Paquete:** PET-6656d0e745ba9196b002d8bc791b1b1e87f8579fadb5da06627af0c861002d3f
**Fecha de Operación:** 2026-05-01
**Motor de Auditoría:** Toltecayotl Engine v2.1 ("El Cronista")

## 1. Análisis de Contenido (Resumen Narrativo)
Este paquete contiene **10 unidades de conocimiento**. 
El contenido trata principalmente sobre: pet toltecayotl nvidia build.

### Fragmentos Destacados:
- **Excerpto 1:** Ese enlace es el **catálogo NVIDIA Build / NVIDIA NIM**. En términos prácticos: es una plataforma para **probar, comparar y desplegar modelos de IA mediante APIs o microservicios optimizados para GPU ...
- **Excerpto 2:** También aparecen modelos recientes y pesados, por ejemplo:...
- **Excerpto 3:** La documentación oficial de NVIDIA confirma que sus APIs incluyen **NIM y microservicios CUDA-X**, y que se pueden usar endpoints cloud para prototipado. ([docs.api.nvidia.com](https://docs.api.nvidia...

##):** 0 fragmentos validados directamente.

## 4. Nexos de Verdad (Fundamentos)
- **FF001:** Basado en *>>>

[F002]
sha256=7f12b76b0eca3796855a30af439ea09f18cb055e8eaa000b211182b44b0e8a54*
- **FF003:** Basado en *>>>

[F004]
sha256=feebf52da362eec9fbbd8b28a6b490568cb2bbf7145df2f33e7d0fed9f381b1f*
- **FF005:** Basado en *|---|---:|---|
| `mistral-medium-3.5-128b` | razonamiento, código, agentes | Endpoint gratuito en catálogo |
| `deepseek-v4-flash` / `deepseek-v4-pro` | código, agentes, contexto largo | 284B / MoE, no viable local en tu RTX 4060 Ti |
| `nemotron-3-nano-omni-30b-a3b-reasoning` | multimodal: imagen, video, voz, texto | Interesante para análisis documental/multimedia |
| `llama-nemotron-rerank-1b-v2` | reranking para RAG | Muy útil para tesis/documentos |
| `nemotron-ocr-v1` | OCR y extracción de tablas | Útil para papers, PDFs, fichas técnicas |
| `qwen3.5-122b-a10b` | razonamiento/código/agentes | Modelo MoE, probablemente solo cloud o GPU grande |
>>>

[F006]
sha256=133cdffc84fb98ec70f1bc8672564d2e938c20a2e6d768c8d43646dba29adc55*
- **FF007:** Basado en *>>>

[F008]
sha256=192886b505dbd720369172afc319f5db24a1ac5c5688526f0cf6ad5bf62f853c*
- **FF009:** Basado en *1. **Endpoint cloud desde build.nvidia.com**  
   Sirve para prototipar rápido con API, sin instalar el modelo localmente.

2. **Contenedor NIM descargable/self-hosted**  
   Sirve para desplegar modelos en infraestructura propia con GPU NVIDIA.
>>>

[F010]
sha256=c71c5a82c8cb7fbfdc67ec59a4efd5fd9b6bed4ff2aa2e69375fa71b48282013*
- **FF011:** Basado en *>>>

[F012]
sha256=bb2ef265d58f442485c60d6ee5f513de3801e25cdf45ab34b79b36a8f86cd52a*
- **FF013:** Basado en *>>>

[F014]
sha256=b7ea1b63ec83b969b6822a60ec72fdccaaf85d6f4e7db26bd4657ed0e49ff25a*
- **FF015:** Basado en *>>>

[F016]
sha256=4571bc24d90ed43c0c69d62c0e7e958c791c1405da534adae77c3434d9c51659*
- **FF017:** Basado en *> **NVIDIA Build debe usarse como banco de pruebas y capa de referencia externa para modelos grandes, no como base principal del stack local edge.**
>>>

[F018]
sha256=371209409caff5651036ecc8cfd04f733ef66b5a41998fd4964e1f7dc891d387*
- **FN/A:** Basado en *Derivado de sesión*

---
*Este informe garantiza que el contenido ingestado es trazable y fundamentado. Si existen riesgos, deben ser mitigados antes de la integración al canon.*

_Última actualización: `2026-05-15`._
