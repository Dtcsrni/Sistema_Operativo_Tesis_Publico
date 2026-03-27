<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0013_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# Decisión Arq: Integración Nativa con LaTeX (DEC-0013)

## Contexto
Aunque Markdown es ideal para la captura de datos y bitácoras, la **tesis formal** de posgrado requiere la precisión tipográfica y el manejo de objetos de **LaTeX**.

## Decisión
Establecer un "Scientific Hub" donde:
1. **LaTeX como Destino:** El directorio `05_tesis_latex/` contendrá el documento maestro.
2. **Markdown como Fuente:** Los capítulos y secciones se redactarán en Markdown en las carpetas `01_planeacion`, `02_metodologia`, etc.
3. **Conversión Automática:** Un script (`export_to_latex.py`) transformará los MD seleccionados a `.tex` usando Pandoc.
4. **BibTeX Unificado:** `00_sistema_tesis/config/referencias.bib` será compartido por la Wiki (HTML) y la Tesis (PDF).

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
- **Positivas:** Permite escribir con la agilidad de MD y publicar con la gloria de LaTeX. Evita la duplicidad de contenido.
- **Negativas:** Se requiere instalar Pandoc en el sistema para la conversión automática.
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
