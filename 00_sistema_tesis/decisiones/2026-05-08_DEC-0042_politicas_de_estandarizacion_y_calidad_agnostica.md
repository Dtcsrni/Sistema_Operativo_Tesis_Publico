<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0042 | 2026-05-08 | v1 | draft -->
# DEC-0042: Políticas de Estandarización y Calidad Agnóstica (FRE/PVC)

## Contexto
Para garantizar que la calidad de la respuesta no dependa exclusivamente de la potencia del modelo, el sistema debe imponer estructuras y procesos que obliguen a cualquier modelo (local o nube) a operar con rigor científico y bajo una nomenclatura técnica en español mexicano.

## Decisión
Se establecen tres pilares de estandarización soberana: el **Formato de Respuesta Epistémica (FRE)**, el **Protocolo de Verificación Cruzada (PVC)** y el **Esquema de Salida Estructurada (ESE)**.

## 1. Formato de Respuesta Epistémica (FRE)
Toda respuesta de dominio `academico` o `profesional` deberá seguir obligatoriamente este formato en español:

```markdown
### [RAZONAMIENTO]
- Análisis paso a paso del problema o consulta.
- Identificación de variables críticas y dependencias técnicas.

### [EVIDENCIA Y TRAZABILIDAD]
- Hallazgos extraídos de la base de conocimiento (con citas [ID] o [Hash]).
- Clasificación de confianza por afirmación: [ALTO/MEDIO/BAJO].

### [SÍNTESIS CIENTÍFICA]
- Respuesta directa, redactada con rigor y estilo académico mexicano.
- Integración de la evidencia con el conocimiento previo del Tesista.

### [AUTO-AUDITORÍA DE RIGOR]
- ¿Se respondió a la pregunta original con precisión? [Sí/No]
- ¿Se detectaron inconsistencias o alucinaciones? [Sí/No]
- Puntaje Epistémico Toltecayotl (Auto-evaluado): 0-100.
```

## 2. Protocolo de Verificación Cruzada (PVC)
Para tareas de riesgo ALTO o CRÍTICO (ej. cambios en la infraestructura o protocolos de ingesta), el sistema ejecutará:
1.  **Generación de Premisas**: El modelo lista los hechos y testimonios en los que basa su respuesta.
2.  **Validación de Hechos**: Se contrastan las premisas contra los archivos fuente del repositorio.
3.  **Refactorización Correctiva**: Si una premisa es falsa o inexacta, el modelo debe regenerar la respuesta completa.

## 3. Esquema de Salida Estructurada (ESE)
Las tareas de extracción y análisis DEBEN producir un bloque JSON al final de la respuesta para facilitar la validación automatizada por el **Motor de Calidad Toltecayotl (MCT)**:

```json
{
  "integridad": {
    "hash_de_fuente": "hash omitido
    "fidelidad_de_extraccion": 0.0-1.0
  },
  "metadatos_epistemicos": {
    "conceptos_primarios": [],
    "puntaje_de_relevancia": 0-100
  }
}
```

## 4. Política de "Memoria Cero" para Datos Críticos
- Queda prohibido responder sobre contenidos de archivos del repositorio basándose en la "memoria" del modelo (conocimiento previo al entrenamiento).
- El modelo **DEBE** realizar una lectura real (`read_file`, `grep`, `fetch_compact`) en cada sesión antes de afirmar cualquier dato sobre la infraestructura o el canon.

## 5. Implementación en `persona.py`
Se actualizarán los perfiles `academic` y `scientific` para inyectar estas instrucciones de formato de forma nativa en el bloque de sistema.

## Consecuencias
- **Calidad Uniforme**: El rigor científico se desplaza del modelo al protocolo.
- **Trazabilidad**: Las respuestas se vuelven autoportantes y auditables por el MCA.
- **Soberanía Lingüística**: Se elimina la dependencia de acrónimos en inglés para la gobernanza del sistema.

---
**Referencias Globales:**
[LID]: log_sesiones_trabajo_registradas.md
[GOV]: AGENTS.md
[AUD]: matriz_trazabilidad.md

_Última actualización: `2026-05-15`._
