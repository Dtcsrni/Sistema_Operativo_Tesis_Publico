# Instrucciones para Sistemas Agénticos de IA (AGENTS.md)

<!-- SISTEMA_TESIS:PROTEGIDO -->

Este repositorio es un **Sistema Operativo de Tesis de Posgrado** gobernado por principios de soberanía humana estricta y trazabilidad inmutable. Si eres una inteligencia artificial o un agente asistido por LLM, DEBES seguir estas reglas incondicionalmente.

## 1. Contrato de Soberanía Humana
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

## 5. Política Serena MCP
- Usa Serena como primera capa de trabajo solo cuando `python 07_scripts/check_serena_access.py --json` confirme que el perfil activo del host esta disponible y recomendado para uso real.
- Prefiere `serena-local` por HTTP como ruta normal del workspace y tratalo como servicio esperado durante el trabajo agéntico en VS Code; si deja de estar disponible, intenta restaurarlo con recarga de ventana o la tarea `Serena MCP HTTP` antes de degradar a filesystem.
- Si Serena no esta disponible al inicio o durante la sesion, intenta activarla o restaurarla primero, siempre, usando la ruta operativa vigente del workspace antes de continuar por filesystem.
- No asumas que `serena-local-py` este habilitado; si existe, tratalo como diagnostico opcional por `stdio`, no como ruta operativa por defecto.
- Antes de abrir muchos archivos o reconstruir contexto manualmente, consulta Serena con `context.fetch_compact` y `governance.preflight` cuando el perfil recomendado este expuesto por el host.
- Distingue entre backend sano y perfil expuesto: si `check_serena_access.py` indica que un transporte esta saludable pero no publicado en `.vscode/mcp.json`, no lo uses como base operativa normal.
- Si Serena no esta disponible o no esta recomendado para el host activo, sigue trabajando con el filesystem del repo y deja constancia del bloqueo operativo en la salida de trabajo.

---
**Firmado:**
Erick Renato Vega Ceron (Tesista Soberano)
2026-03-24

_Última actualización: `2026-04-14`._
