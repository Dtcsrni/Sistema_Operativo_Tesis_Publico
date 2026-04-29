# ISSUE-0042: Arquitectura Atzin Scientific Engine (Fase Conocimiento Distribuido)

**Estado**: PLANIFICACIÃ“N ABIERTA
**Prioridad**: ALTA
**VinculaciÃ³n**: validación humana interna no pública

## Resumen de la SesiÃ³n [2026-04-29]
Se validÃ³ con Ã©xito el modelo **Qwen 2.5 1.5B (W8A8)** en la Orange Pi 5 Plus, alcanzando **8.8 TPS con 8k de contexto**. Se implementÃ³ **Prompt Caching** (mejora del 70% en TTFT). Se identificÃ³ que la fragmentaciÃ³n de memoria CMA impide el uso simultÃ¡neo de dos modelos en NPU, optando por la estrategia de **Cerebro Unificado**.

## Decisiones Pendientes (Handshake Requerido)
1. **Modelo de Embeddings**: Â¿BGE-M3 (PC) o proveedor de IA no publicado (Cloud)?
2. **TopologÃ­a Weaviate**: Â¿PC Centralizado o HÃ­brido con Milvus Lite en Edge?
3. **Esquema GraphRAG**: Â¿IngestiÃ³n simple o Grafo de Conocimiento denso?
4. **PolÃ­tica de IngestiÃ³n**: Â¿AutomÃ¡tica (Watcher) o Bajo Demanda (Telegram)?
5. **Prioridad EpistÃ©mica**: Â¿Empirismo (Sensores) o TeorÃ­a (Literatura)?

## Tareas TÃ©cnicas PrÃ³ximas
- [ ] Configurar servidor Weaviate en PC de Control.
- [ ] Implementar `knowledge_sync.py` basado en el protocolo de transferencia Hermes.
- [ ] Crear el parser de PDFs acadÃ©micos `atzin_ingestor.py`.
- [ ] Integrar el ruteo de conocimiento en `openclaw_local/engine.py`.

---
**Firmado**: Antigravity (IA) | **ValidaciÃ³n**: Pendiente [validación humana interna no pública]

_Última actualización: `2026-04-29`._
