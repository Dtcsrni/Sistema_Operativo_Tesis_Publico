<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0012_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# Decisión Arq: Gestión de Referencias (DEC-0012)

## Contexto
Una tesis de posgrado requiere un manejo riguroso de fuentes. La desconexión entre el texto y la bibliografía genera errores y pérdida de tiempo.

## Decisión
Implementar un sistema de **Bibliografía Automatizada** basado en estándares académicos:

1. **Fuente de Verdad:** `00_sistema_tesis/config/referencias.bib` (Formato BibTeX).
   - **Recomendación:** Usar **Zotero** con el plugin **Better BibTeX (BBT)**. Configura BBT para "Auto-export" hacia este archivo.
2. **Almacén de PDFs:** `04_datos/referencias/` usando el nombre de la `citekey` (ej. `wilkinson2016fair.pdf`).
3. **Sintaxis en Wiki:** Uso de tags `[@citekey]` en el contenido Markdown.
4. **Automatización:** El `build_wiki.py` extraerá las citas, buscará los metadatos en el `.bib` y generará una sección final de "Referencias Bibliográficas" en cada página.

## Alternativas consideradas

1. Alternativa A
2. Alternativa B
3. Alternativa elegida

## Criterio de elección

Retroactivo: Decisión tomada durante la fase de infraestructura inicial.

## Métricas de Éxito

- [x] Validación operativa de la infraestructura.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Consistencia en auditorías automáticas.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] Firma digital GPG del tesista.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Validación de integridad estructural.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

  - **Soporte:** [Retroactivo | Step ID]
  - **Modo:** [Retroactivo | Confirmación Verbal]
  - **Fecha de Validación:** 2026-03-24
  - **Integridad:** `sha256:N/A` 
  - **Fingerprint:** `sha256:Retroactivo` 
  - **Nivel de Auditoría:** Bajo
## Consecuencias
- **Positivas:** Trazabilidad total, formato consistente, ahorro de tiempo en redacción.
- **Negativas:** Requiere mantener el archivo `.bib` actualizado (se recomienda usar Zotero para exportarlo).
## Trazabilidad de IA

- **Proveedor:** Google (DeepMind)
- **Modelo/Versión:** Gemini 1.5 Pro / Advanced Agentic Coding v1.0
- **Agente/Rol:** Antigravity (Assistant)
- **Nivel de Razonamiento:** alto
- **Prompts/Contexto clave:** Normalización de repositorio.

## Impacto en Presupuesto de Razonamiento

- **Consumo:** Bajo (Retroactivo)
- **Justificación:** Normalización de formato de trazabilidad.

## Implementación o seguimiento

- [x] Implementación completada en Fase B0.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

N/A

[LID]: file:///v:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/bitacora/log_conversaciones_ia.md
[GOV]: file:///v:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/ia_gobernanza.yaml
[AUD]: file:///v:/Sistema_Operativo_Tesis_Posgrado/07_scripts/build_all.py
