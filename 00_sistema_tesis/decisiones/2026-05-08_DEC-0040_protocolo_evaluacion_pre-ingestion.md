<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0040 | 2026-05-08 | v1 | draft -->
# DEC-0040: Protocolo de Evaluación Pre-Ingestión Bibliográfica

**Fecha:** 2026-05-08
**Estado:** VIGENTE
**Prioridad:** CRÍTICA
**ID de Trazabilidad:** [GOV-2026-05-08-ING-STRICT]

## 1. Contexto y Problema
Para garantizar que el motor Toltecayotl no se contamine con información irrelevante o de baja calidad, es necesario un proceso de curaduría humana estricto. La ingesta automatizada, aunque eficiente (Docling/MarkItDown), debe estar subordinada al juicio del Tesista Principal.

## 2. Decisión Operativa
Toda ingesta bibliográfica deberá seguir obligatoriamente un proceso de 5 fases antes de ser considerada "Conocimiento Canónico". **Queda terminantemente prohibida la ingesta masiva o por lotes (batch); cada documento debe ser analizado, discutido y aprobado de forma individual y secuencial.**

### Fases del Protocolo:

0. **Fase de Triaje y Clasificación Estructural (IA)**:
   - Identificación automática del tipo de documento (Académico, Hardware, Clase, etc.).
   - Organización en directorios de procesamiento (`03_datos/procesados/XX_...`).
   - Registro del movimiento en el Ledger para trazabilidad de procedencia.

1. **Fase de Extracción y Reporte (IA)**:
   - Extracción de alta fidelidad (Docling).
   - Generación automática de un **Informe de Pertinencia Bibliográfica (IPB)**.
   
2. **Fase de Discusión y Análisis (Colaborativa)**:
   - El agente presenta el IPB al Tesista.
   - Discusión sección por sección del documento.
   - Análisis de aportes específicos al problema, hipótesis o diseño experimental.

3. **Fase de Comparación Epistémica**:
   - Contrastar la nueva información con lo ya existente en el motor Toltecayotl para evitar redundancias o identificar contradicciones.

4. **Fase de Validación y Aprobación (Humana)**:
   - El Tesista otorga un **Step ID (validación humana interna no pública)** para autorizar la ingesta final.
   - Si no se aprueba, se documentan las razones del rechazo.

5. **Fase de Destino Final**:
   - **APROBADO**: Asimilación en `01_contexto_canonico` y generación de cápsulas.
   - **RECHAZADO**: Almacenamiento en `03_datos/procesados/historico_rechazado/` con log de motivos.

## 3. Estructura del Informe de Pertinencia Bibliográfica (IPB)
El IPB debe ser óptimo y eficiente, conteniendo:
- **Metadatos de Rigor Académico**:
    - **Fuente**: Revista/Conferencia (incluir Cuartil SJR/JCR o Rank CORE si aplica).
    - **Autores e Institución**: Identificación del prestigio académico.
    - **Impacto**: Conteo de citas (estimado) y relevancia en el campo.
- **Resumen Ejecutivo**: ¿Qué es este documento?
- **Mapa de Aportes**: Vinculación directa con secciones de la tesis.
- **Análisis Crítico**: Fortalezas, debilidades y sesgos detectados.
- **Recomendación de Ingesta**: Grado de prioridad (P0-P3).

### 3.1 Soporte Tecnológico (IA)
- **Motor Primario**: Gemini 3 Flash (vía Vertex AI).
- **Razón**: Máxima ventana de contexto para documentos extensos y superioridad en razonamiento analítico frente a modelos locales, garantizando la validez del IPB.
- **Control de Costos**: Integración obligatoria con `CostLimiter` para evitar desviaciones presupuestarias.

## 4. Consecuencias
- Mayor calidad y densidad de utilidad del acervo bibliográfico.
- Trazabilidad total de por qué una fuente fue incluida o descartada.
- Prevención de "infoxicación" en el sistema RAG Toltecayotl.

---
**Firmado:**
Sistema Agéntico OpenClaw (en representación del Tesista)
2026-05-08

---
**Referencias Globales:**
[LID]: log_sesiones_trabajo_registradas.md
[GOV]: AGENTS.md
[AUD]: matriz_trazabilidad.md

_Última actualización: `2026-05-15`._
