<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0029 | 2026-05-01 | v1.8 | Propuesta -->

# DEC-0029: Estandarización del Formato de Ingestión Paquete Epistémico Toltecayotl (PET)

**Estado:** Propuesta (v1.6)
**Fecha:** 2026-05-01
**Autor:** Tesista (Asistido por Codex)
**Vínculo:** ISSUE-0043

## Contexto
El sistema requiere un método de registro de conocimiento que garantice la **máxima fidelidad**, **trazabilidad criptográfica** y **ausencia de alucinaciones**. Se adopta una nomenclatura **100% autodescriptiva en español mexicano** para asegurar que el sistema sea intuitivo para el Tesista y otros investigadores, manteniendo el nombre **Toltecayotl** como el motor central.

## Decisión
Se establece el formato **Paquete Epistémico Toltecayotl (PET)** como el estándar mandatorio para el registro de conocimiento. El **Ingestor Toltecayotl** es el componente responsable del procesamiento y registro.

### 1. Especificación del Esquema PET (Paquete Epistémico)
Cada fragmento de sabiduría se registra en formato JSONL con los siguientes campos autodescriptivos:

| Campo | Descripción Técnica |
| :--- | :--- |
| **`id_del_fragmento`** | Identificador único (`sha256` del contenido). |
| **`contenido_original`** | Texto íntegro del documento (Inmunidad a alucinaciones). |
| **`autoridad_del_dato`** | Quién emite el dato: `Tesista`, `IA`, `Documento_Externo`, `Hardware_Spec`. |
| **`grado_de_certeza`** | Nivel de confianza: `Hecho`, `Requisito`, `Hipótesis`, `Propuesta`. |
| **`fundamento_del_dato`** | Justificación (Link/Hash/URI/URL/Filepath). |
| **`metadatos_de_procedencia`** | Ubicación exacta (archivo, página, párrafo, posición). |
| **`auditoria_de_ingesta`** | Datos de registro (fecha, versión del ingestor, estado). |
| **`contexto_de_agente_externo`** | Datos de sistemas externos como ChatGPT (modelo, sesión). |

### 2. Ingestor Toltecayotl (Herramienta de Registro)
El script [**`ingestor_toltecayotl.py`**](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/06_dashboard/publico/NOTA_SEGURIDAD_Y_ACCESO.md) es la herramienta oficial para transformar documentos y síntesis en archivos PET.
- **Soporte de Agentes**: Permite atribuir el conocimiento a modelos de IA específicos para mantener la integridad de la síntesis científica.

### 3. Protocolo de Citación y Verificación Exhaustiva
Para eliminar la dependencia del texto generado (síntesis) y evitar alucinaciones:
- **Nexo Obligatorio**: Toda afirmación en la síntesis debe incluir una cita al fragmento original mediante su ID: `[REF:id_del_fragmento]`.
- **Verificación Cruzada**: El motor Toltecayotl ignorará cualquier dato en la síntesis que no coincida semántica o literalmente con un fragmento en el `contenido_original` (Texto Nelli).
- **Prioridad de Verdad**: En caso de discrepancia, el `contenido_original` siempre prevalece sobre la síntesis agéntica.

### 4. Guardrails de Integridad
- **Validación Automática**: El sistema verifica el hash de cada fragmento antes de procesarlo.
- **Cita Obligatoria**: Toda inferencia debe referenciar el `hash_del_documento_fuente` y sus metadatos de procedencia.
- **Auditoría de Citas**: Se implementará un validador que verifique la existencia física de cada ID citado en la síntesis dentro del mismo paquete PET o en la Amoxcalli.

## Consecuencias
- **Positivas**: Máxima intuición operativa, alineación con estándares de ciencia de datos en español, trazabilidad inexpugnable.
- **Negativas**: Campos de metadatos ligeramente más largos.

## Validación Humana Requerida
- [ ] Aprobación del esquema final **Autodescriptivo (PET v1.6)**.
  - [ ] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [ ] Step ID para la primera ingesta masiva oficial.
  - [ ] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

[LID]: log_sesiones_trabajo_registradas.md
[GOV]: ../../07_scripts/guardrails.py
[AUD]: ../../07_scripts/build_all.py

_Última actualización: `2026-05-15`._
