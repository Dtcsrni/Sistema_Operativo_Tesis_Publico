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
- **Telemetría Obligatoria (Solo Notificación):** Toda tarea técnica que se prevea dure más de 30 segundos (benchmarks, compilaciones, ingesta) DEBE utilizar el sistema de telemetría remota (`long_process_monitor`) bajo el estándar "Total Awareness" (DEC-0037). En la arquitectura actual, Telegram actúa como un canal de **solo-lectura (Push)** para monitoreo y reporte de actividades; no se procesan comandos interactivos ni se requiere interacción humana en este canal.
- **Cierre de Trazabilidad:** Toda instrucción humana crítica, cambio de política o ajuste de infraestructura debe quedar reflejado en el Ledger y en la Matriz con fecha, Step ID si existe, archivos afectados, hash del contenido citado y resultado de auditoría; no se considera cerrada la trazabilidad si falta una de esas piezas.
- **Evidencia Operativa:** Para cambios en configuración o infraestructura, conserva el `.bak`, registra el alcance del diff y deja constancia del `build_all.py` ejecutado antes de pedir cierre o publicación.

## 3. Seguridad de Infraestructura (Guardrails)
- **Archivos Protegidos:** Si detectas la marca `<!-- SISTEMA_TESIS:PROTEGIDO -->`, NO edites el archivo sin autorización específica y el uso de los mecanismos de respaldo definidos en `07_scripts/guardrails.py`.
- **Backups:** Siempre realiza un backup `.bak` antes de modificar archivos de configuración o infraestructura.
- **Protocolo de Eliminación (Guardrail):** NUNCA ejecutes eliminaciones (rm, Remove-Item, del) en directorios de datos o infraestructura sin: 1) Listar y verificar el contenido previamente y 2) Solicitar confirmación humana explícita si el destino no está vacío. Esta regla aplica incluso para carpetas creadas por el agente en la misma sesión. [SAFE-2026-05-08-DEL-GUARD]

## 4. Ejecución de Auditoría
- Antes de entregar cualquier trabajo, ejecuta localmente:
  ```bash
  python 07_scripts/build_all.py
  ```
  Si la auditoría falla, corrige el formato o la integridad antes de proponer el cambio al usuario.

## 5. Política Toltecayotl Epistemic Inference Engine
- El núcleo de razonamiento se apoya en el **Toltecayotl Epistemic Inference Engine**, que coordina la ingestión de literatura académica heterogénea y su procesamiento mediante **Weaviate (PC)** y **NPU (Edge)**.
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

## 7. Política Caveman (Niveles L1-L3)
- **Modo Operativo Base:** Usa Caveman como modo operativo base de cualquier agente de IA antes de iniciar trabajo técnico.
- **Nivel 1 (L1) - Verbose/Diagnóstico:**
    - Cuándo: Nuevas arquitecturas, bugs complejos, modo interactivo profundo.
    - Requisitos: Razonamiento completo paso a paso, diagnósticos detallados, formatos FRE y ESE extendidos.
- **Nivel 2 (L2) - Compact/Estándar (Default):**
    - Cuándo: Tareas operativas normales, implementación de features conocidas.
    - Requisitos: Razonamiento conciso, Step ID obligatorio, bloque ESE resumen.
- **Nivel 3 (L3) - Ultra-Conciso/Binary:**
    - Cuándo: Tareas repetitivas, validaciones de masa, cierre de sesiones, modo `/caveman` activo.
    - Requisitos: Solo resultados, Step ID y hash de validación. Mínimo consumo de tokens.
- **Enforcement:** Trata la disponibilidad shell de `caveman` como el punto de entrada de estilo y control de ruido.
- **Gobernanza:** Cuando Caveman y Serena coexistan, la secuencia es: Caveman (Estilo) -> Serena (Contexto) -> Filesystem (Respaldo).

## 8. Política de Retención y Rotación de Backups
- El sistema utiliza `07_scripts/ops/rotate_backups.py` para gestionar la acumulación de archivos `.bak` en `config/backups/`.
- **Niveles de Retención:**
    - **Crítico:** 180 días (Decisiones, Canon, Gobernanza, Manifest de Integridad).
    - **Alto:** 90 días (Ledger, Matriz de Trazabilidad).
    - **Operativo:** 30 días (Otros scripts y archivos temporales).
- **Límites de Volumen:** Máximo 500 archivos o 1GB total; se aplica purga automática por antigüedad en caso de exceder límites, priorizando la eliminación de archivos de riesgo "operativo".
- **Ventana de Protección:** Todo backup tiene una ventana mínima de protección de 7 días donde NO puede ser eliminado por rotación automática.

## 9. Política de Skills de Ingeniería (mattpocock/skills)

Los siguientes skills están disponibles en `_agents/skills/` e integrados al flujo de trabajo agéntico del proyecto. Fueron adaptados de [mattpocock/skills](https://github.com/mattpocock/skills) y ajustados a las convenciones del Sistema Operativo de Tesis.

### Skills de Ingeniería

| Skill | Cuándo usar |
|---|---|
| `diagnose` | Bug reportado, segfault, OOM, fallo de pipeline, regresión de benchmark |
| `grill-with-docs` | Antes de un cambio técnico mayor; actualiza `CONTEXT.md` y decisiones DEC-XXXX inline |
| `tdd` | Construir features o corregir bugs con loop red-green-refactor |
| `to-prd` | Crear un PRD desde el contexto actual; publica en `00_sistema_tesis/pendientes/` |
| `zoom-out` | Área de código desconocida; necesita mapa de módulos y callers |
| `resilient_orchestrator` | Ejecución de pipelines críticos; autodiagnóstico OOM y cambio de estrategia automático |
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
- **Formatos Mandatorios (DEC-0042)**: Todo skill que genere respuestas académicas o técnicas DEBE incluir el bloque **FRE (Formato de Respuesta Epistémica)** y el bloque **ESE (Esquema de Salida Estructurada)** en formato JSON para auditoría por el **MCT**.
- **Decisiones**: Los skills respetan las decisiones DEC-XXXX existentes.
- **Triage tracker**: Issues gestionados en `00_sistema_tesis/pendientes/`.

## 10. Política de Documentación Técnica y Visual
- **Idioma y Región:** Toda documentación, diagramas, manuales e infografías DEBEN estar redactados en **Español Mexicano** técnico de alta precisión.
- **Fidelidad de Hardware:** Toda representación visual de hardware DEBE ser verificada doblemente contra las especificaciones físicas reales. Debe incluir fabricante (ej. Shenzhen Xunlong Software), modelo exacto y posición de componentes con **precisión milimétrica** (ej. ubicación exacta de LEDs de estado respecto al puerto USB-C). **Toda información debe basarse estrictamente en fuentes oficiales altamente confiables y documentación de diseño mecánico (CAD/Schematics) cuando esté disponible.**
- **Consistencia de Software:** Los estados representados en manuales deben coincidir exactamente con la lógica implementada en el código fuente.
- **Calidad Premium:** Las guías visuales deben evitar estética genérica y priorizar diseños premium (Blueprint, Tech Dark Mode) que reflejen la sofisticación del sistema Toltecayotl.

## 11. Política de Soberanía del Centro de Control
- **Centro de Control de Misiones:** Es la interfaz primaria y soberana para la gestión de tareas, aprobación de herramientas y monitoreo detallado.
- **Bypass de Seguridad en Herramientas Seguras:** Cuando `OPENCLAW_BYPASS_SAFE_MODE` está activo, las herramientas de bajo riesgo (generación de imágenes, reinicio de servicios permitidos) se ejecutan de forma autónoma sin generar solicitudes de aprobación bloqueantes.
- **Aislamiento de Telegram:** El bot de Telegram está configurado en modo `OPENCLAW_TELEGRAM_TELEMETRY_ONLY`, lo que significa que ignora mensajes entrantes para garantizar que la lógica de decisión resida exclusivamente en el núcleo del sistema y el dashboard.

## 12. Prohibición de Stubs y Maquetas No Documentadas [SAFE-2026-05-15-STUB-GUARD]
- **Integridad Funcional:** Queda ESTRICTAMENTE PROHIBIDO crear stubs, maquetas (mockups), placeholders o funciones de "relleno" y presentarlas como piezas operativas, funcionales o probadas.
- **Etiquetado Obligatorio:** Si por necesidad técnica de arquitectura o testing se requiere crear un stub o placeholder, este DEBE incluir obligatoriamente el tag `[STUB_OPERATIVO: NO_FUNCIONAL]` en su docstring y comentarios, detallando qué funcionalidad falta y por qué no debe usarse en producción.
- **Validación de Código:** Antes de cada entrega, el agente debe verificar que no existan piezas de código simuladas que puedan inducir a error en la interpretación de la madurez del sistema.
- **Gobernanza de Pruebas:** Los mocks en suites de pruebas deben estar claramente aislados y nunca filtrarse al código de runtime como lógica de fallback "simulada".

---
**Firmado:**
Erick Renato Vega Ceron (Tesista Principal)
2026-05-06

_Última actualización: `2026-05-15`._
