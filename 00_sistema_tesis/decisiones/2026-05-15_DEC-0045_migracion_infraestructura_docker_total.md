<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0045 | 2026-05-15 | v1.0 | Validado -->
---
id: DEC-0045
title: Migración a Infraestructura Docker Total y Nomenclatura Semántica
date: 2026-05-15
status: Aceptada
tags:
  - Infraestructura
  - Docker
  - llama.cpp
  - Gobernanza
---

# Contexto y Problema

El sistema actual depende de piezas nativas (Serena MCP, scripts de orquestación SSH) y utiliza una nomenclatura de contenedores que es abstracta o genérica (`nucleo-openclaw`, `pasarela`). Esto dificulta el monitoreo, la escalabilidad y la autonomía total del stack, además de no representar fielmente la función de cada componente. Asimismo, el uso de Ollama como capa intermedia añade overhead innecesario frente a motores de inferencia directos como `llama.cpp`.

# Decisión

Se adopta una infraestructura **100% basada en Docker** para todos los componentes operativos, eliminando dependencias nativas del host. Se establece una nueva convención de nombres semánticos para mejorar la observabilidad.

## 1. Nueva Nomenclatura Semántica

| Función | Nuevo Nombre Contenedor | Imagen |
| :--- | :--- | :--- |
| Cerebro/Bot Telegram | `bot-agente-telegram` | `siot-agente-core` |
| Orquestador/Gateway API | `gateway-orchestrator-api` | `siot-agente-core` |
| Persistencia PET | `api-persistencia-pet` | `siot-agente-core` |
| Servidor Contexto Serena | `servidor-contexto-serena` | `siot-serena-mcp` |
| Inferencia GGUF | `inferencia-llamacpp` | `llama-cpp-server` |
| Hub de Misiones (Web) | `hub-misiones-web` | `siot-hub-misiones` |
| Visor de Canon/Docs | `visor-canon-docs` | `siot-visor-docs` |
| Base Semántica | `db-vectorial-weaviate` | `weaviate:1.31.4` |
| Ejecutor de Código/RAG | `executor-codigo-rag` | `siot-executor-opencode` |
| Monitor de Telemetría | `monitor-telemetria` | `siot-agente-core` |

## 2. Transición a llama.cpp

Se reemplaza Ollama por `llama.cpp` (servidor nativo) en el PC para:
- Reducir el overhead de gestión.
- Permitir control directo sobre parámetros de cuantización y memoria.
- Exponer una API compatible con proveedor de IA no publicado (v1/chat/completions).

## 3. Optimización de Resiliencia

- **Volúmenes**: Uso de volúmenes nombrados para persistencia de logs y DBs; bind-mounts solo para código en desarrollo y el canon protegido.
- **Autonomía**: Uso de políticas `restart: unless-stopped` y healthchecks nativas en Docker.
- **Red**: Aislamiento en la red `siot-network` con descubrimiento por nombre de servicio.

# Consecuencias

- **Positivas**: Mayor independencia del host, mejor observabilidad, inferencia más rápida y ligera, alineación con estándares de la industria (proveedor de IA no publicado API).
- **Riesgos**: Requiere gestión manual de archivos `.gguf` en `runtime/models`.
- **Acciones**: Actualizar todos los archivos de configuración y el motor de routing (`engine.py`).

_Última actualización: `2026-05-15`._
