---
name: zoom-out
description: Tell the agent to zoom out and give broader context or a higher-level perspective. Use when you're unfamiliar with a section of code or need to understand how it fits into the bigger picture of the OpenClaw/thesis system.
source: https://github.com/mattpocock/skills/blob/main/skills/engineering/zoom-out/SKILL.md
disable-model-invocation: true
---

I don't know this area of code well. Go up a layer of abstraction. Give me a map of all the relevant modules and callers, using the project's domain glossary vocabulary (`00_sistema_tesis/CONTEXT.md` if exists, else `_agents/skills/openclaw_context/SKILL.md`).

## Adaptación OpenClaw
Para el proyecto OpenClaw, el mapa debe incluir:
- **Módulo raíz** (nombre en el glosario, no el nombre del archivo)
- **Callers directos** y su rol en el sistema
- **Dependencias hacia abajo** (servicios, modelos, hardware)
- **Decisiones relevantes** (DEC-XXXX que afectan el módulo)
- **Seams de test** existentes o ausentes

_Última actualización: `2026-05-15`._
