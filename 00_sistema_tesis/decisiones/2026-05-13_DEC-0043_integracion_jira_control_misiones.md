<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0043 | 2026-05-13 | v1 | draft -->
# DEC-0043: IntegraciÃ³n de Jira en el Centro de Control de Misiones
<!-- GID: [validación humana interna no pública] -->

## Estado
**Propuesto** (2026-05-13)

### [RAZONAMIENTO]
El Centro de Control de Misiones (CCM) opera como el nÃºcleo de gobernanza y despacho de tareas del sistema Toltecayotl. Sin embargo, para integrarse con flujos de trabajo corporativos y acadÃ©micos externos, se requerÃ­a una conexiÃ³n con Jira.

La implementaciÃ³n busca automatizar la trazabilidad entre el backlog tÃ©cnico de la tesis y los sistemas de gestiÃ³n de proyectos, eliminando la duplicidad manual de reportes.

### [EVIDENCIA Y TRAZABILIDAD]
- Hallazgos en rama `feat/jira-integration` (Repositorio `control_mission`).
- MigraciÃ³n de DB confirmada en `src/lib/db/migrations.ts` (030_jira_sync).
- ClasificaciÃ³n de confianza: [ALTO].

### [SÃ NTESIS CIENTÃ FICA]
Se ha decidido unificar la funcionalidad de Jira en la rama principal (`main`) del repositorio `control_mission` bajo los siguientes tÃ©rminos:

1.  **Esquema de Base de Datos**: Se integra la tabla `jira_sync` (Migración 030) que almacena el vínculo `task_id` <-> `jira_issue_key`.
2.  **API Pipeline**: Se implementa un cliente de Jira (`jira-client`) que permite operaciones de vinculación/desvinculación mediante endpoints protegidos.
3.  **Interfaz de Usuario**:
    *   Se añade un modal de gestión de Jira dentro de `TaskModal`.
    *   Se implementan indicadores visuales ("Badges") en la cola de misiones para identificar tareas sincronizadas.
4.  **Localización**: Toda la interfaz de Jira se mantiene en **Español Mexicano (es-MX)** siguiendo la política de documentación del proyecto.

## Consecuencias
*   **Positivas**: Mayor interoperabilidad con herramientas de gestión de proyectos estándar. Trazabilidad académica mejorada.
*   **Negativas**: Nueva dependencia de red externa y del servicio de Jira. Incremento ligero en la complejidad del esquema de base de datos.
*   **Riesgos**: Posible divergencia si los estados de Jira cambian sin que el CCM sea notificado (sincronización fire-and-forget inicial).

## Evidencia
*   **Repositorio**: `control_mission`
*   **Archivos clave**: `src/lib/db/schema.ts`, `src/lib/db/migrations.ts`, `src/components/TaskModal.tsx`.
*   **Step ID**: [validación humana interna no pública]

### [AUTO-AUDITORÃ A DE RIGOR]
- Â¿Se respondiÃ³ a la pregunta original con precisiÃ³n? SÃ­
- Â¿Se detectaron inconsistencias o alucinaciones? No
- Puntaje EpistÃ©mico Toltecayotl: 95/100

### [ESE - ESQUEMA DE SALIDA ESTRUCTURADA]
```json
{
  "integridad": {
    "hash_de_fuente": "hash omitido:omitido",
    "fidelidad_de_extraccion": 1.0
  },
  "metadatos_epistemicos": {
    "conceptos_primarios": ["Jira", "CCM", "Trazabilidad"],
    "puntaje_de_relevancia": 90,
    "nivel_caveman_aplicado": "L2"
  }
}
```

---
**Referencias Globales:**
[LID]: log_sesiones_trabajo_registradas.md
[GOV]: AGENTS.md
[AUD]: matriz_trazabilidad.md

_Última actualización: `2026-05-15`._
