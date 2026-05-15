<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0041 | 2026-05-08 | v1 | draft -->
# DEC-0041: Motor de Calidad Toltecayotl (MCT) - Evaluación de Calidad Epistémica

## Contexto
El Tesista requiere una forma "precisa y altamente confiable" de medir la calidad de las respuestas y procesos del sistema OpenClaw, priorizando la validez académica sobre el costo y manteniendo la coherencia lingüística con la política de español mexicano del proyecto.

## Decisión
Se implementará el **Motor de Calidad Toltecayotl (MCT)**, un marco de evaluación multi-capa alineado con el ecosistema central de conocimiento, que audita cada respuesta crítica (especialmente Informes de Pertinencia e Ingesta) antes de su entrega final.

## 1. Métricas de Calidad Soberanas (MCT-V1)

| Métrica | Definición | Método de Cálculo | Umbral Crítico |
| :--- | :--- | :--- | :--- |
| **Fidelidad** | Grado de verdad y apego estricto a los documentos fuente (sin invenciones). | G-Eval usando Gemini 3 Flash como Juez de Calidad. | > 0.95 |
| **Densidad de Evidencia** | Relación entre afirmaciones fácticas y testimonios/citas verificables. | Conteo de claims vs. citas en el Ledger/Canon. | > 1:1 |
| **Consistencia Lógica** | Ausencia de contradicciones internas en la cadena de razonamiento (CoT). | Verificación cruzada (Cross-check) con un segundo modelo. | Sin fallas |
| **Puntaje Epistémico** | Calificación integral de la validez científica de la respuesta. | Ponderación Toltecayotl: 50% Fidelidad, 30% Evidencia, 20% Lógica. | > 85/100 |

## 2. Protocolo de Validación en Cascada
Para asegurar la máxima confiabilidad, el sistema seguirá este flujo:
1.  **Generación**: El modelo primario genera la respuesta bajo el formato FRE.
2.  **Auto-Auditoría Toltecayotl**: Un prompt de "Auditor Interno" revisa la respuesta buscando inconsistencias.
3.  **Cross-Check (Opcional)**: Un modelo local verifica las citas y testimonios fácticos.
4.  **Validación Humana**: Resultados con Puntaje Epistémico < 85 requieren revisión obligatoria del Tesista.

## 3. Implementación Técnica
- **Módulo**: `runtime/openclaw/openclaw_local/motor_calidad_toltecayotl.py`
- **Registro de Logs**: `runtime/openclaw/state/logs_calidad/`
- **Integración**: El núcleo ruteador invocará al **MCT** para todas las tareas de dominio `academico`.

## 4. Consecuencias
- Eliminación de respuestas "técnicamente correctas pero académicamente inválidas".
- Trazabilidad total de la *calidad* en la Matriz de Trazabilidad.
- Refuerzo de la identidad soberana del sistema mediante el uso de terminología propia y centralizada.

---
**Referencias Globales:**
[LID]: log_sesiones_trabajo_registradas.md
[GOV]: AGENTS.md
[AUD]: matriz_trazabilidad.md

_Última actualización: `2026-05-15`._
