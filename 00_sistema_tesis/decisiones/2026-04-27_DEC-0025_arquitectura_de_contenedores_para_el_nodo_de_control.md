<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0025 | 2026-04-27 | v1.1 | ACEPTADA -->

# DEC-0025 Arquitectura de Contenedores para el Nodo de Control (PC Hub)

- Fecha: 2026-04-27
- Estado: aceptada
- Alcance: arquitectura | infraestructura | operación
- Relacionada con bloques: B0
- Relacionada con decisiones: [DEC-0022], [DEC-0016]

## Contexto

Para garantizar la reproducibilidad del entorno de investigación y facilitar el despliegue distribuido entre el Escritorio Primario (PC) y el Nodo Edge (Orange Pi), es necesario estandarizar el runtime operativo del sistema de tesis sin desplazar la superficie principal de autoría. La ejecución directa sobre el host (Windows/WSL) presenta riesgos de derivas de dependencias para servicios, navegadores y agentes; a la vez, mover todo a Docker degradaría la ergonomía y el control fino de VS Code, Codex, Serena, Git y trazabilidad manual.

## Decisión

Adoptar una arquitectura **híbrida WSL + Docker** para el Nodo de Control (PC Hub):

1.  **Plano de autoría y control `wsl_authoring`**:
    *   **Rol**: Superficie principal de trabajo humano-agente.
    *   **Runtime**: WSL + VS Code + Codex.
    *   **Procesos**: Git, Caveman, Serena MCP HTTP, trazabilidad, edición controlada y `build_all.py`.
    *   **Regla**: El repositorio soberano y el canon no se trasladan íntegramente a Docker.
2.  **Plano reproducible `docker_services`**:
    *   **Rol**: Servicios reproducibles, pruebas E2E y dependencias pesadas.
    *   **Runtime**: Docker Compose.
    *   **Proceso**: Encapsular `siot-docs`, `siot-agent`, Playwright, FFmpeg y runtime asistivo sin sustituir los guardrails.
3.  **Estrategia de filesystem**:
    *   **Desarrollo normal**: Mantener el workspace actual en WSL/VS Code.
    *   **Cargas pesadas Docker**: Medir impacto de bind mounts desde `/mnt/*`; si degrada, usar clon operativo en filesystem Linux/ext4 o volúmenes nombrados para estado/cache/generados.
    *   **Canon**: No mover el canon ni convertirlo en volumen primario sin una decisión explícita adicional.

El stack de contenedores inicial queda estructurado así:

1.  **Servicio `siot-docs`**:
    *   **Rol**: Servidor de gobernanza y visualización.
    *   **Runtime**: Nginx (Alpine).
    *   **Proceso**: Construye el dashboard estático mediante `build_all.py` durante el build de la imagen.
    *   **Puerto**: 8080 (mapeado localmente).
2.  **Servicio `siot-agent`**:
    *   **Rol**: Agente de Inteligencia Operativa (OpenClaw).
    *   **Runtime**: Python 3.12-slim.
    *   **Dependencias**: FFmpeg, Playwright (Chromium).
    *   **Persistencia**: Volúmenes compartidos para el Canon (`00_sistema_tesis`), Estado del Agente y Logs.
3.  **Orquestación**:
    *   Uso de `docker-compose.yml` para gestionar redes internas, volúmenes y variables de entorno.
4.  **Resiliencia de Secretos**:
    *   El agente debe ser capaz de arrancar y permanecer estable incluso si faltan secretos (como el Token de Telegram), operando en modo espera hasta que se provean.
5.  **Economía de tokens y orquestación agéntica**:
    *   `agent_task_router` clasifica tareas por privacidad, riesgo, complejidad, rutas objetivo y necesidad de documentación externa.
    *   Serena mantiene repo/canon/gobernanza como primera capa de contexto.
    *   Modelos locales (`ollama_local`, `desktop_compute` via Ollama) pueden ejecutar subtareas automáticas, pero no escribir directamente en el repositorio.
    *   `Context7 MCP` se limita a documentación externa actualizada.
    *   `GitHub Models` se permite solo para contexto público o redactado, con token `models:read`; queda prohibido para evidencia privada, secretos, ledger privado, canon no público y rutas sensibles.

## Alternativas consideradas

1.  Ejecución nativa solo en WSL (rechazada como estándar único por dificultad de replicación de servicios y dependencias pesadas).
2.  Migración total a Docker (rechazada porque degrada el flujo de autoría/control con VS Code, Codex, Serena, Git y trazabilidad manual).
3.  Contenedores individuales sin orquestación (rechazada por complejidad de gestión de redes y volúmenes).
4.  **Arquitectura híbrida WSL + Docker Compose (elegida).**

## Criterio de elección

Maximiza la portabilidad y el aislamiento de dependencias pesadas sin perder la ergonomía ni la soberanía operativa del workspace WSL/VS Code. Además prepara la infraestructura para sincronización con el Nodo Edge y permite medir antes de mover cargas pesadas a filesystem Linux/ext4 o volúmenes nombrados.

## Métricas de Éxito

- [x] Disponibilidad del Dashboard en `http://localhost:8080`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte operativo**: `docker compose -f docker-compose.yml up -d --build siot-docs`; `docker inspect` reportó `running healthy`; `curl -I http://127.0.0.1:8080/` devolvió `HTTP/1.1 200 OK`.
- [x] Ejecución exitosa de `tests/test_docker_stack.py` dentro del contenedor.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte operativo**: contenedor efímero `python:3.12-slim` unido a `siot-network` con `SISTEMA_TESIS_RUNTIME=docker-test`; resultado `5 passed`.
- [x] Persistencia verificada del canon tras reinicio de contenedores.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte operativo**: SHA-256 de `/app/00_sistema_tesis/canon/events.jsonl` dentro del contenedor coincide con `00_sistema_tesis/canon/events.jsonl` del host: `0b163578865093e5b30629478ca70f8aad8ff497ee0f07c9f0e0e47414df8ec5`.
- [x] Política híbrida WSL + Docker formalizada sin sustituir Serena, Caveman, Git ni guardrails.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Política de nubes gratuitas formalizada: solo contexto público/redactado.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] El tesista aprueba la formalización del runtime híbrido WSL + Docker como estándar operativo del PC Hub.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte**: [validación humana interna no pública]
  - **Pregunta crítica o disparador**: "¿Autorizas la formalización de DEC-0025 y la integración de Docker como estándar operativo del PC Hub?"

## Consecuencias

- **Positivas**: Entorno determinista para servicios, despliegue rápido, aislamiento de riesgos técnicos y conservación del flujo de autoría WSL/VS Code.
- **Negativas**: Incremento en el consumo inicial de disco (imágenes Docker), necesidad de gestionar el ciclo de vida de los contenedores y posible degradación de rendimiento si se abusa de bind mounts desde `/mnt/*`.
- **Riesgo controlado**: el canon sigue en el repo soberano; Docker encapsula ejecución, no sustituye Serena, Caveman, guardrails ni validación humana.

## Trazabilidad del trabajo asistido

- **Proveedor**: Google (DeepMind)
- **Modelo/Versión**: Gemini 1.5 Pro / Advanced Agentic Coding v1.0
- **Agente/Rol**: Antigravity (Assistant)
- **Nivel de Razonamiento**: alto

## Implementación o seguimiento

- [x] Crear `Dockerfile` para `siot-docs`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Crear `Dockerfile.agent` para `siot-agent`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Implementar `docker-compose.yml`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Actualizar `manual_operacion_humana.md` con comandos Docker.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Formalizar la estrategia híbrida WSL + Docker.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Integrar política de economía de tokens con Serena, Caveman, modelos locales, Context7 MCP y GitHub Models público/redactado.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

[LID]:  ruta local no pública 
[GOV]:  ruta local no pública 
[AUD]:  ruta local no pública

_Última actualización: `2026-05-15`._
