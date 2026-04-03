<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-26_DEC-0018_ | Versión: 1.0.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0018 Evidencia Fuente de Conversación Codex para Confirmación Verbal

- Fecha: 2026-03-26
- Estado: aceptada
- Alcance: gobernanza | trazabilidad | operación
- Relacionada con bloques: B0, B1
- Relacionada con decisiones: [DEC-0014], [DEC-0015], [DEC-0016], [DEC-0017]

## Contexto

El canon ya preserva el texto exacto de confirmación verbal y su hash. Eso ofrece trazabilidad interna fuerte, pero no prueba por sí solo que la cita provino realmente de la superficie de Codex. Para investigación, tesis y auditoría metodológica, hace falta una segunda capa de evidencia capaz de enlazar la cita canónica con un artefacto fuente privado.

## Decisión

Se adopta un modelo híbrido de evidencia:

1. **Canon en repo:** el `[validacion_humana_interna]` conserva la cita exacta, su hash y el enlace a `source_event_id`.
2. **Fuente privada local:** cada `conversation_source_registered` conserva `transcripción + captura` dentro de `[evidencia_privada_redactada]/conversaciones_codex/`.
3. **Activación gradual:** el enforcement aplica a nuevos `[validacion_humana_interna]` a partir del umbral configurado en `ia_gobernanza.yaml`.
4. **Compatibilidad histórica:** el historial previo se mantiene como `legacy_unverified_source`; no se reescribe ni se invalida.
5. **Publicación segura:** la evidencia fuente privada y sus hashes crudos quedan fuera de la superficie pública sanitizada.

## Alternativas consideradas

1. Confiar solo en el canon interno.
2. Exigir export forense nativo del cliente Codex.
3. **Usar canon + artefacto fuente privado local.**

## Criterio de elección

La alternativa elegida maximiza trazabilidad práctica y verificable sin depender de capacidades forenses no expuestas por Codex. Mantiene una cadena de evidencia útil para revisión metodológica, auditoría interna y defensa de tesis.

## Métricas de Éxito

- [x] Existencia del evento `conversation_source_registered` en el canon.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Existencia de comandos `tesis.py source register|verify|status`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Enforcement automático para `[validacion_humana_interna]` nuevos desde el umbral configurado.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] El tesista autoriza implementar corroboración por fuente de conversación para futuros `[validacion_humana_interna]`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** [[validacion_humana_interna]]
  - **Pregunta crítica o disparador:** Instrucción humana directa registrada sin pregunta previa del agente.
  - **Texto exacto de confirmación verbal:** "PLEASE IMPLEMENT THIS PLAN:"
  - **Hash de confirmación verbal:** `[hash_redactado]:[redactado]`
  - **Fuente de verdad de confirmación:** `00_sistema_tesis/canon/events.jsonl :: [validacion_humana_interna] :: human_validation.confirmation_text`
  - **Nivel de Auditoría:** Alto
  - **Modo:** Confirmación Verbal
  - **Fecha de Validación:** 2026-03-26

## Consecuencias

- **Positivas:** mejora la confiabilidad de la confirmación verbal, habilita verificación local y separa claramente evidencia interna, corroborada y retroactiva.
- **Negativas:** añade trabajo operativo adicional y más artefactos privados que deben mantenerse organizados.
- **Riesgo explícito:** si no se captura la transcripción y la imagen en tiempo, la corroboración fuerte no podrá reconstruirse después.

## Implementación o seguimiento

- [x] Crear el índice privado de fuentes de conversación.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Excluir `evidencia_privada` de Git por default y del bundle público.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Verificar repo/local con `tesis.py source verify` y `tesis.py source status`.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

- [DEC-0014](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md)
- [DEC-0015](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0015_protocolo_de_sanitización_para_exposición_pública.md)
- [DEC-0016](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-26_DEC-0016_canon_unificado_de_eventos_y_proyecciones.md)
- [DEC-0017](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-26_DEC-0017_operacion_humana_dual_y_superficies_privada_publica.md)

[LID]: [ruta_local_redactada]
[GOV]: [ruta_local_redactada]
[AUD]: [ruta_local_redactada]
