<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0037 | 2026-05-05 | v1.0 | Validado -->

# DEC-0037: Estandarización de Telemetría Remota y Monitoreo de Progreso

**Estado:** ✅ VALIDADO
**Fecha:** 2026-05-05
**Autor:** Antigravity (IA) / Tesista Principal
**Contexto:** [validación humana interna no pública]

## 1. Problema
La ejecución de tareas de larga duración en el Sistema Operativo de Tesis (compilaciones, benchmarks, ingesta de literatura) requiere un mecanismo de visibilidad remota para que el tesista pueda supervisar el estado del sistema sin necesidad de una sesión de terminal activa o presencial.

## 2. Decisión
Se formaliza el **Sistema de Notificaciones de Progreso** como una función básica y obligatoria del sistema. 

### Requisitos Técnicos
1. **Canal Primario:** Telegram API (OpenClaw Bot).
2. **Componente Core:** `AdvancedProgressMonitor` ([`progress.py`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/runtime/openclaw/openclaw_local/progress.py)).
3. **Fidelidad de Datos:**
    *   **Identificación de Host:** Ubicación física/lógica de la tarea.
    *   **Detalle Dinámico:** Extracción de hitos del log de salida.
    *   **Cálculo de ETA:** Algoritmo de proyección robusto con soporte para horas.
4. **Trazabilidad:** Generación mandatoria de `telegram_audit.log` para certificar la entrega de mensajes.

## 3. Justificación
*   **Eficiencia Operativa:** Permite la supervisión multi-nodo (PC/Edge) desde una interfaz centralizada y móvil.
*   **Rigor Académico:** Proporciona evidencia de tiempos de ejecución y estabilidad del sistema para la defensa de la tesis.
*   **Resiliencia:** El sistema de auditoría previene "monitoreo ciego" en caso de fallos de red.

## 4. Implicaciones
*   Todos los scripts en `07_scripts/` que realicen tareas de más de 30 segundos deben integrar el monitor de progreso.
*   Las habilidades agénticas (`skills`) deben estar alineadas con el estándar definido en `long_process_monitor`.

---
**Validación Humana:** [validación humana interna no pública]


---

## 🔗 Referencias Globales

- **[LID]:** Decisión registrada en canon / log_sesiones_trabajo_registradas.md
- **[GOV]:** Política de Gobernanza / AGENTS.md  
- **[AUD]:** Validación vía build_all.py / operabilidad humana


[LID]:  ruta local no pública /00_sistema_tesis/decisiones/2026-05-05_DEC-0037_estandarizacion_telemetria_remota.md
[GOV]: AGENTS.md
[AUD]: build_all.py

_Última actualización: `2026-05-15`._
