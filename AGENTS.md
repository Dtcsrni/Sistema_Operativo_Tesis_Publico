# Instrucciones para Sistemas Agénticos de IA (AGENTS.md)

<!-- SISTEMA_TESIS:PROTEGIDO -->

Este repositorio es un **Sistema Operativo de Tesis de Posgrado** gobernado por principios de control humano directo y gobernanza de datos inmutable. Si eres una inteligencia artificial o un agente asistido por LLM, DEBES seguir estas reglas incondicionalmente.

## 1. Contrato de Control y Gobernanza Humana
- **Prohibición de Auto-Validación:** NUNCA marques una tarea o decisión como "validada" por tu cuenta. Toda validación requiere el consentimiento humano explícito vinculado a un **Step ID** (ej. `[validación humana interna no pública]`).
- **Protocolo Handshake:** Sigue estrictamente el protocolo definido en [`DEC-0014`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md).

## 2. Trazabilidad de Evidencia
- **Libro Mayor (Ledger):** Registra cada instrucción humana crítica en [`log_sesiones_trabajo_registradas.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md).
- **Integridad SHA-256:** Cada entrada en el Ledger debe incluir campos de Hash SHA-256 calculados sobre el contenido exacto entre delimitadores `<<< >>>`.
- **Jerarquía de Validación:** NUNCA marques una tarea principal como completada (`[x]`) si sus sub-tareas de pre-requisitos técnicos están pendientes (`[ ]`).
- **Autoauditoría Documental:** Cada documento de trazabilidad debe ser autoportante; esto incluye el uso de **Referencias Globales** (`[LID]`, `[GOV]`, `[AUD]`) y bloques de autoauditoría compactos para demostrar evidencia inmediata.
- **Matriz de Trazabilidad:** Mantén actualizada la [`matriz_trazabilidad.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/bitacora/matriz_trazabilidad.md).
- **Cierre de Trazabilidad:** Toda instrucción humana crítica, cambio de política o ajuste de infraestructura debe quedar reflejado en el Ledger y en la Matriz con fecha, Step ID si existe, archivos afectados, hash del contenido citado y resultado de auditoría; no se considera cerrada la trazabilidad si falta una de esas piezas.
- **Evidencia Operativa:** Para cambios en configuración o infraestructura, conserva el `.bak`, registra el alcance del diff y deja constancia del `build_all.py` ejecutado antes de pedir cierre o publicación.

## 3. Seguridad de Infraestructura (Guardrails)
- **Archivos Protegidos:** Si detectas la marca `<!-- SISTEMA_TESIS:PROTEGIDO -->`, NO edites el archivo sin autorización específica y el uso de los mecanismos de respaldo definidos en `07_scripts/guardrails.py`.
- **Backups:** Siempre realiza un backup `.bak` antes de modificar archivos de configuración o infraestructura.

## 4. Ejecución de Auditoría
- Antes de entregar cualquier trabajo, ejecuta localmente:
  ```bash
  python 07_scripts/build_all.py
  ```
  Si la auditoría falla, corrige el formato o la integridad antes de proponer el cambio al usuario.

## 5. Política Atzin Scientific Engine
- El núcleo de razonamiento se apoya en el **Atzin Scientific Engine**, que coordina la ingestión de literatura académica heterogénea y su procesamiento mediante **Weaviate (PC)** y **NPU (Edge)**.
- Los agentes deben priorizar la integridad de los datos de investigación y la trazabilidad de cada síntesis generada.
- La base de conocimientos se sincroniza bidireccionalmente, garantizando que el nodo Edge posea contexto relevante para inferencia local offline.

## 6. Política Serena MCP
- Usa Serena como primera capa de trabajo solo cuando `python 07_scripts/check_serena_access.py --json` confirme que el perfil activo del host esta disponible y recomendado para uso real.
- Prefiere `serena-local` por HTTP como ruta normal del workspace y tratalo como servicio esperado durante el trabajo agéntico en VS Code; si deja de estar disponible, intenta restaurarlo con recarga de ventana o la tarea `Serena MCP HTTP` antes de degradar a filesystem.
- Si Serena no esta disponible al inicio o durante la sesion, intenta activarla o restaurarla primero, siempre, usando la ruta operativa vigente del workspace antes de continuar por filesystem.
- No asumas que `serena-local-py` este habilitado; si existe, tratalo como diagnostico opcional por `stdio`, no como ruta operativa por defecto.
- Antes de abrir muchos archivos o reconstruir contexto manualmente, consulta Serena con `context.fetch_compact` y `governance.preflight` cuando el perfil recomendado este expuesto por el host.
- Distingue entre backend sano y perfil expuesto: si `check_serena_access.py` indica que un transporte esta saludable pero no publicado en `.vscode/mcp.json`, no lo uses como base operativa normal.
- Si Serena no esta disponible o no esta recomendado para el host activo, sigue trabajando con el filesystem del repo y deja constancia del bloqueo operativo en la salida de trabajo.

## 6. Política Caveman
- Usa Caveman como modo operativo base de cualquier agente de IA en este repositorio antes de iniciar trabajo técnico: `command -v caveman` debe resolver y `caveman --help` debe estar disponible.
- Si Caveman no esta disponible al inicio o durante la sesion, intenta activarlo o restaurarlo primero por la ruta global del host antes de degradar a texto genérico o a flujo filesystem-only.
- Trata la disponibilidad shell de `caveman` como el punto de entrada de estilo y control de ruido; no la confundas con la capa de contexto del repositorio.
- Cuando Caveman y Serena coexistan, la secuencia normal es: Caveman como modo de trabajo conciso, Serena como primera capa de contexto compacto y gobernanza cuando el perfil recomendado este disponible, y filesystem solo como respaldo.
- No sobreentiendas que `caveman` resuelve por sí solo la política del repo: la enforcement real sigue viniendo de AGENTS, los hooks y la documentación operativa.

## 7. Política de Skills de Ingeniería (mattpocock/skills)

Los siguientes skills están disponibles en `_agents/skills/` e integrados al flujo de trabajo agéntico del proyecto. Fueron adaptados de [mattpocock/skills](https://github.com/mattpocock/skills) y ajustados a las convenciones del Sistema Operativo de Tesis.

### Skills de Ingeniería

| Skill | Cuándo usar |
|---|---|
| `diagnose` | Bug reportado, segfault, OOM, fallo de pipeline, regresión de benchmark |
| `grill-with-docs` | Antes de un cambio técnico mayor; actualiza `CONTEXT.md` y decisiones DEC-XXXX inline |
| `tdd` | Construir features o corregir bugs con loop red-green-refactor |
| `to-prd` | Crear un PRD desde el contexto actual; publica en `00_sistema_tesis/pendientes/` |
| `zoom-out` | Área de código desconocida; necesita mapa de módulos y callers |
| `improve-codebase-architecture` | Encontrar oportunidades de refactoring; ejecutar periódicamente |
| `triage` | Gestionar issues en `00_sistema_tesis/pendientes/` |

### Skills de Productividad

| Skill | Cuándo usar |
|---|---|
| `caveman` | Modo de comunicación ultra-compacto (~75% menos tokens); activar con "caveman mode" |
| `grill-me` | Stress-test rápido de un plan sin actualizar documentación |
| `write-a-skill` | Crear nuevos skills para el proyecto |

### Reglas de uso

- **Supervisión Humana**: Ningún skill puede marcar decisiones como validadas autónomamente. Toda validación requiere Step ID del Tesista.
- **Glosario**: Todos los skills usan `00_sistema_tesis/CONTEXT.md` como fuente de verdad de términos del dominio.
- **Decisiones**: Los skills respetan las decisiones DEC-XXXX existentes y solo proponen reabrirlas cuando la fricción es real.
- **Triage tracker**: Issues gestionados como archivos locales en `00_sistema_tesis/pendientes/` (no GitHub Issues).

---
**Firmado:**
Erick Renato Vega Ceron (Tesista Principal)
2026-04-29

_Última actualización: `2026-04-29`._
