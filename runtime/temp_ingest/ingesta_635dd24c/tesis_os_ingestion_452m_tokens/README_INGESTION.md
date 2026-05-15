# Paquete de ingestión — Caso 452M tokens, agentes IA y control de costos

**Fecha UTC:** 2026-05-01T10:05:42Z  
**Proyecto:** Tesis posgrado IoT / Sistema operativo de tesis  
**Propósito:** convertir la historia de usuario sobre 452M tokens por ~$22 USD en un objeto de conocimiento verificable, auditable e ingerible por RAG, Obsidian, OpenClaw o un servidor MCP local.

## 1. Alcance de validación

Validado en este paquete:

- consistencia aritmética de tokens, solicitudes, ratios y costos bajo supuestos explícitos;
- plausibilidad del costo reportado con cache alto;
- riesgo operativo de loops multiagente;
- necesidad de budgets, circuit breakers, deduplicación y telemetría;
- utilidad del stack Tezkatli + Orange Pi como middleware de control.

No validado en este paquete:

- dashboard privado real;
- facturación real del autor de la historia;
- precios web vigentes al momento de ingestión;
- configuración exacta de modelos/proveedor.

## 2. Resultados numéricos

| Métrica | Valor |
|---|---:|
| Tokens entrada | 452.0M |
| Tokens salida | 3.1M |
| Solicitudes | 17,189 |
| Costo reportado | $22.81 USD |
| Entrada promedio / solicitud | 26295.89 tokens |
| Salida promedio / solicitud | 180.35 tokens |
| Ratio input/output | 145.81:1 |
| Cache hit implícito bajo supuestos DeepSeek | 92.23% |
| Costo estimado con 91% cache hit | $24.21 USD |

## 3. Veredicto

La historia es **plausible como caso operativo**, pero **no debe usarse como benchmark académico completo**. Sirve como evidencia motivacional para diseñar un middleware local con:

- cache;
- RAG;
- control de loops;
- presupuesto por agente;
- métricas de costo;
- auditoría de prompts;
- fallback a API externa;
- humano en el circuito para acciones críticas.

## 4. Archivos incluidos

| Archivo | Uso |
|---|---|
| `ingestion_chunks.jsonl` | Ingestión directa en RAG/vector DB. |
| `claims_register.jsonl` | Registro auditable de afirmaciones. |
| `claims_register.csv` | Revisión tabular de claims. |
| `guardrails.yaml` | Reglas operativas para agentes. |
| `manifest.json` | Metadatos del paquete. |

## 5. Reglas de ingestión recomendadas

- Chunk por línea JSONL.
- Usar `id`, `type`, `title`, `text`, `tags`, `validation` y `metadata`.
- Indexar `text` y `title`.
- Guardar `validation.status` como filtro.
- No promover claims `requiere_revalidacion` a conclusiones finales sin auditoría adicional.

_Última actualización: `2026-05-15`._
