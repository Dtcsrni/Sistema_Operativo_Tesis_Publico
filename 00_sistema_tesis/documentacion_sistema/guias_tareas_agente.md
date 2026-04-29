# Guías de Tareas con el Agente OpenClaw

Esta sección proporciona tutoriales prácticos y guías de tareas para maximizar el uso del agente soberano en el flujo de investigación de la tesis.

## 1. Investigación y Síntesis Académica (`/investiga`)

El comando `/investiga` está diseñado para realizar búsquedas profundas y síntesis académicas utilizando el modelo más capaz (actualmente **Hermes 3: 8B** en el PC).

### Escenario: Revisión de Literatura
1. **Prompt:** `/investiga "Estado del arte sobre sistemas operativos embebidos para IoT con enfoque en resiliencia 2023-2026"`
2. **Lo que hace OpenClaw:**
   - Realiza búsquedas web multi-fuente.
   - Filtra por relevancia académica.
   - Genera un reporte estructurado con citas y referencias.
   - Inyecta la trazabilidad en el ledger (`[VAL-STEP]`).

### Buenas Prácticas
- Usa comillas para términos específicos.
- Especifica el rango de años para forzar actualidad.
- Solicita formatos específicos (ej. "Resume en una tabla comparativa").

---

## 2. Depuración de Datos IoT y Sensores (`/debug`)

Cuando el nodo Edge detecta anomalías en los sensores (intermitencia), OpenClaw puede ayudar a diagnosticar la causa raíz.

### Escenario: Fallo de Conectividad en Pachuca
1. **Prompt:** `/chat "Analiza los últimos logs de conectividad del nodo B1 y busca patrones de caída de energía"`
2. **Lo que hace OpenClaw:**
   - Recupera logs de `00_sistema_tesis/bitacora/`.
   - Cruza datos con la taxonomía de intermitencia urbana.
   - Sugiere si el fallo es por red o por suministro eléctrico local.

---

## 3. Gobernanza y Gestión de Decisiones (`/decision`)

OpenClaw asiste en la creación de registros formales que cumplen con los guardrails del sistema.

### Escenario: Cambio de Política de Inferencia
1. **Flujo de Trabajo:**
   - Discute la idea con el agente en `/chat`.
   - Solicita: `"Genera un borrador de DEC-XXXX siguiendo la política de soberanía para cambiar el modelo base a Qwen 2.5"`.
   - El agente genera el Markdown con los bloques de auditoría obligatorios (`[LID]`, `[GOV]`, `[AUD]`).
2. **Validación:**
   - Revisa el archivo generado.
   - Firma digitalmente (Step ID).

---

## 4. Automatización de Backups y Salud del Sistema

Uso de herramientas CLI integradas para mantener la integridad de la tesis.

### Comandos Rápidos vía Bot
- `/status`: Reporte rápido de salud (Storage, VRAM, Token Budget).
- `/backup`: Inicia el pipeline de respaldo encriptado.
- `/audit`: Ejecuta `build_all.py` y reporta fallos de trazabilidad.

---

## Cuadro Maestro de Capacidades

| Categoría | Comando | Modelo Recomendado | Nivel de Autonomía |
|-----------|---------|-------------------|--------------------|
| **Investigación** | `/investiga` | Hermes 3 (8B) | Supervisada |
| **Consultas** | `/chat` | Qwen 2.5 (3B/4B) | Alta |
| **Codificación** | `/chat` | Qwen 2.5-Coder | Media |
| **Diagnóstico** | `/status` | N/A (Scripts) | Total |

> [!IMPORTANT]
> Recuerda que toda acción significativa debe quedar reflejada en el Ledger. La IA propone, pero el Tesista Soberano certifica.

_Última actualización: `2026-04-29`._
