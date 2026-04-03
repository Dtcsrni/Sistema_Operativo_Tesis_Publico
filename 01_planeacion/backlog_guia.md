# Guía de Formato Detallado: Backlog

Para mantener la trazabilidad de alto nivel requerida por el Sistema Operativo de la Tesis, cada entrada en el `backlog.csv` debe cumplir con los siguientes criterios de "detalle".

## Columnas Obligatorias y su Uso Detallado

1.  **task_id:** Formato `T-XXX`. Único y secuencial.
2.  **bloque:** Debe coincidir con los IDs en `00_sistema_tesis/config/bloques.yaml` (ej. `B0`, `B1`).
3.  **subbloque:** Nombre descriptivo de la agrupación funcional (ej. `Seguridad`, `Caso Pachuca`).
4.  **tarea:** Una oración en imperativo que describa el resultado esperado (ej. "Implementar validador de integridad GPG").
5.  **tipo:** `arquitectura`, `investigacion`, `implementacion`, `documentacion`, `validacion`, `datos`.
6.  **prioridad:** `critica`, `alta`, `media`, `baja`.
7.  **estado:** `pendiente`, `ejecutando`, `hecho`, `bloqueado`, `descartado`.
8.  **dependencia:** ID de la tarea que debe completarse antes (ej. `T-001`).
9.  **hipotesis:** IDs de las hipótesis vinculadas separadas por pipe (ej. `H1|H3`). **Toda tarea técnica debe apoyar al menos una hipótesis.**
10. **entregable:** ID del entregable final al que contribuye (ej. `ENT-001`).
11. **fecha_objetivo:** Formato `YYYY-MM-DD`.
12. **notas:** **Aquí reside el detalle.** Debe incluir:
    - Breve descripción del "Por qué".
    - Criterio de éxito simple.
    - Riesgos detectados para esta tarea específica.

## Definición de "Detalle" para Tareas Complejas

Si una tarea es demasiado compleja para describirse en la columna `notas`, se debe crear un archivo complementario en `01_planeacion/tareas/T-XXX_detalle.md` siguiendo la plantilla de diseño técnico.

## Ciclo de Vida de la Tarea
- **Pendiente:** Definida con hipótesis y prioridad.
- **Ejecutando:** Debe tener un autor asignado (en sistemas multi-usuario) y fecha de inicio en bitácora.
- **Hecho:** Debe tener un enlace a la evidencia técnica en la bitácora correspondiente.

_Última actualización: `2026-04-03`._
