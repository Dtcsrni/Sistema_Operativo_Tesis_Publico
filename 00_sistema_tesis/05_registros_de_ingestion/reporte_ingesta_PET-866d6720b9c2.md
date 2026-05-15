# Informe de Ingestión Epistémica: PET-866d6720b9c2

**Fecha de Ingesta:** 2026-05-01 08:12  
**ID de Sesión Original:** SESION_LOCAL_FIRST_20260501  
**Agente Generador:** GPT-5.5 Thinking  
**Hash de Raíz:** 866d6720b9c267362f41e0107b7669ae36e07504212196a554d6de75e7aae05b

## 1. Tesis de la Sesión
La sesión establece que la infraestructura de la tesis debe operar bajo el principio **Local-First**. Se descarta el uso de ChatGPT Plus vía navegador (Web Assisted) como componente crítico debido a la inestabilidad de la automatización externa y los bloqueos anti-bot detectados.

## 2. Hallazgos Técnicos
- **Ollama API:** Confirmada como funcional en `http://127.0.0.1:11434` incluso cuando el CLI no está en el PATH.
- **Gobernanza:** Se define que **OpenClaw** actúa como plano de control, **Serena MCP** como capa de contexto y **Codex** como ejecutor bajo tickets controlados.
- **Seguridad:** El modo `chatgpt_plus_web_session` con Playwright es detectado por los sistemas de seguridad de proveedor de IA no publicado, lo que refuerza la necesidad de modelos locales.

## 3. Evaluación de Modelos (Ranking Toltecayotl)
1. **Mistral-Nemo (12b):** Excelente balance entre razonamiento y fidelidad al contexto. Aprobado como modelo académico principal.
2. **Qwen2.5-Coder (14b):** Potente para código pero con tendencia a alucinar rutas absolutas y comandos no existentes. Requiere revisión humana estricta.
3. **Hermes 3 (8b):** Propenso a informalidad y metáforas; útil solo para borradores con prompts restrictivos.

## 4. Decisiones Derivadas
- Se formaliza la **DEC-0030** para adoptar la arquitectura Local-First.
- Se establece el ruteo prioritario hacia modelos locales vía Ollama.

## 5. Acciones Pendientes
- [ ] Configurar ruteo de Telegram hacia `qwen3:4b`.
- [ ] Validar la latencia de `mistral-nemo:12b` en tareas de larga duración.
- [ ] Ejecutar auditoría completa del sistema con `build_all.py` tras los cambios de configuración.

_Última actualización: `2026-05-15`._
