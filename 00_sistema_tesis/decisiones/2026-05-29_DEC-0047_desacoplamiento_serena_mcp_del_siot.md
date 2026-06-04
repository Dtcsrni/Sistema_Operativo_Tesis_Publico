<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0047 | 2026-05-29 | v1.1 | Aceptada | validación humana interna no pública -->
---
id: DEC-0047
title: Desacoplamiento de Serena MCP del Stack SIOT — Herramienta de Host Tezkatli
date: 2026-05-29
status: Aceptada
tags:
  - Infraestructura
  - Serena
  - Arneses
  - Gobernanza
  - PC-Tezkatli
---

# Contexto y Problema

La DEC-0045 ("Migración a Infraestructura Docker Total") incluía a `servidor-contexto-serena`
como un contenedor del stack operativo principal del SIOT (listado en `docker-compose.yml` y
`docker-compose.pc.yml`). Sin embargo, Serena MCP **no es parte del SIOT ni de OpenClaw**;
es una herramienta de gestión de contexto de proyecto para IDEs y agentes que corre
directamente en el host de la PC de desarrollo **Tezkatli**, exponiéndose por defecto en el
puerto `8765`.

Incluir Serena en los composes del SIOT genera una dependencia de infraestructura incorrecta
que puede impedir el inicio del sistema si el host Tezkatli no está disponible o si Serena
no se requiere en el entorno de ejecución (e.g., producción edge, entorno CI).

# Decisión

Se desacopla `servidor-contexto-serena` del stack de servicios principal del SIOT:

1. **Remoción de `docker-compose.yml`**: El servicio `servidor-contexto-serena` es eliminado,
   incluyendo la dependencia (`depends_on`) del servicio `bot-agente-telegram` hacia él.

2. **Remoción de `docker-compose.pc.yml`**: El servicio `servidor-contexto-serena` es
   eliminado de este archivo de override de la PC de escritorio.

3. **Posición canónica de Serena**: Serena MCP **no forma parte de OpenClaw** ni de los
   arneses de desarrollo del proyecto. Es una herramienta de host que corre en la PC
   **Tezkatli** para gestionar contexto de proyecto en VS Code, IDEs y agentes externos.
   Su configuración reside en `.vscode/mcp.json` y `.vscode/tasks.json` del workspace;
   su ciclo de vida es gestionado por el usuario directamente en el host, no por Docker.

4. **`docker-compose-openclaw.yml`**: Este archivo orquesta únicamente los arneses de
   OpenClaw (e.g., `openclaw-sovereign-core`). **No incluye a Serena**, y su cabecera
   documenta explícitamente este hecho.

5. **Política AGENTS.md**: La Política Serena MCP (sección 6 de `AGENTS.md`) documenta
   el flujo de verificación de disponibilidad de Serena y el fallback a filesystem. Esta
   política permanece vigente, ya que opera en el ámbito del host, no del stack Docker.

# Consecuencias

- **Positivas**:
  - El stack SIOT puede inicializarse sin requerir que Serena esté levantada en el host.
  - Separación clara de responsabilidades: Docker ↔ herramientas de host.
  - La DEC-0045 sigue siendo válida para los servicios que sí son parte del SIOT.
- **Riesgos**:
  - Los agentes que no tengan acceso al host Tezkatli no podrán usar Serena; el fallback
    a filesystem (`AGENTS.md §6`) cubre este caso.
- **Acciones completadas**:
  - Backups `.bak` de `docker-compose.yml`, `docker-compose.pc.yml` y
    `docker-compose-openclaw.yml` creados antes de la modificación.
  - Auditoría modular `build_all.py --no-serena-gate` ejecutada y aprobada (PASS).
  - Evento validación humana interna no pública registrado en el canon (`events.jsonl`).

# Referencias

[LID]:  ruta local no pública 
[GOV]:  ruta local no pública 
[AUD]:  ruta local no pública 
[REF-DEC-0045]:  ruta local no pública 
[REF-AGENTS-MD]:  ruta local no pública 
[VAL]: validación humana interna no pública | Erick Renato Vega Ceron | 2026-05-29 | evento interno no público

_Última actualización: `2026-06-03`._
