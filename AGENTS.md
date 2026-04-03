# Instrucciones para Sistemas Agénticos de IA (AGENTS.md)

<!-- SISTEMA_TESIS:PROTEGIDO -->

Este repositorio es un **Sistema Operativo de Tesis de Posgrado** gobernado por principios de soberanía humana estricta y trazabilidad inmutable. Si eres una inteligencia artificial o un agente asistido por LLM, DEBES seguir estas reglas incondicionalmente.

## 1. Contrato de Soberanía Humana
- **Prohibición de Auto-Validación:** NUNCA marques una tarea o decisión como "validada" por tu cuenta. Toda validación requiere el consentimiento humano explícito vinculado a un **Step ID** (ej. `[[validacion_humana_interna]]`).
- **Protocolo Handshake:** Sigue estrictamente el protocolo definido en [`DEC-0014`](06_dashboard/wiki/nota_seguridad_y_acceso.md).

## 2. Trazabilidad de Evidencia
- **Libro Mayor (Ledger):** Registra cada instrucción humana crítica en [`log_conversaciones_ia.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
- **Integridad SHA-256:** Cada entrada en el Ledger debe incluir campos de Hash SHA-256 calculados sobre el contenido exacto entre delimitadores `<<< >>>`.
- **Jerarquía de Validación:** NUNCA marques una tarea principal como completada (`[x]`) si sus sub-tareas de pre-requisitos técnicos están pendientes (`[ ]`).
- **Autoauditoría Documental:** Cada documento de trazabilidad debe ser autoportante; esto incluye el uso de **Referencias Globales** (`[LID]`, `[GOV]`, `[AUD]`) y bloques de autoauditoría compactos para demostrar evidencia inmediata.
- **Matriz de Trazabilidad:** Mantén actualizada la [`matriz_trazabilidad.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).

## 3. Seguridad de Infraestructura (Guardrails)
- **Archivos Protegidos:** Si detectas la marca `<!-- SISTEMA_TESIS:PROTEGIDO -->`, NO edites el archivo sin autorización específica y el uso de los mecanismos de respaldo definidos en `07_scripts/guardrails.py`.
- **Backups:** Siempre realiza un backup `.bak` antes de modificar archivos de configuración o infraestructura.

## 4. Ejecución de Auditoría
- Antes de entregar cualquier trabajo, ejecuta localmente:
  ```bash
  python 07_scripts/build_all.py
  ```
  Si la auditoría falla, corrige el formato o la integridad antes de proponer el cambio al usuario.

---
**Firmado:**
Erick Renato Vega Ceron (Tesista Soberano)
2026-03-24
