# KPIs SMART para Departamentos Agénticos de Investigación

Este documento establece los Indicadores Clave de Rendimiento (KPIs) con objetivos SMART (Específicos, Medibles, Alcanzables, Relevantes y con Plazo) para gobernar el comportamiento y evaluar la calidad de los agentes del orquestador en misiones de investigación.

---

## KPI-CUR-01: Tasa de Calidad de Fuentes (Curaduría)

*   **Objetivo:** Garantizar la validez y el rigor científico de la literatura recolectada.
*   **Métrica:** Porcentaje de artículos recuperados que cuentan con un Identificador de Objeto Digital (DOI) verificado y pertenecen a revistas o actas de congresos indexados peer-reviewed (excluyendo preprints).
*   **Meta SMART:** $\ge 90\%$ de las fuentes bibliográficas de cada misión deben estar validadas con DOI y publicadas (no preprints) para finales del ciclo de iteración actual.
*   **Fórmula:**
    $$\text{Tasa de Calidad} = \left( \frac{\text{Artículos con DOI verificado}}{\text{Artículos totales incorporados}} \right) \times 100$$

---

## KPI-ANA-02: Tasa de Consistencia Epistémica (Análisis)

*   **Objetivo:** Erradicar por completo la alucinación de claims científicos y asegurar alineación conceptual.
*   **Métrica:** Relación de afirmaciones o claims de los agentes que corresponden de forma unívoca a un extracto literal referenciado del artículo origen y validados frente al glosario canónico (`CONTEXT.md`).
*   **Meta SMART:** $100\%$ de los claims científicos incorporados en el borrador deben estar referenciados a una cita válida y coherente con el glosario, registrando 0 alucinaciones en todas las misiones.
*   **Fórmula:**
    $$\text{Consistencia Epistémica} = \left( \frac{\text{Claims citados y verificados}}{\text{Claims generados en borrador}} \right) \times 100$$

---

## KPI-RED-03: Eficiencia de Formato y Compilabilidad (Redacción)

*   **Objetivo:** Lograr una integración fluida e inmediata de los resultados en el manuscrito de tesis.
*   **Métrica:** Ausencia de errores de sintaxis LaTeX y corrección en las referencias en formato BibTeX.
*   **Meta SMART:** $100\%$ de los archivos de sección `.tex` generados y sus correspondientes registros en `.bib` deben compilar sin advertencias ni errores de referencias rotas en el compilador de LaTeX local.
*   **Fórmula:**
    $$\text{Eficiencia de Formato} = \left( \frac{\text{Archivos compilados con éxito}}{\text{Archivos generados totales}} \right) \times 100$$

---

## KPI-ECO-04: Presupuesto de Tokens y Eficiencia de Costo (Economía)

*   **Objetivo:** Optimizar el consumo de recursos de cómputo local y costos de red API cloud.
*   **Métrica:** Consumo total de tokens de entrada/salida y costo financiero acumulado por cada misión.
*   **Meta SMART:** Límite máximo de $100,000$ tokens consumidos en inferencia local (`mistral-nemo:12b` en PC) y máximo $15,000$ tokens en APIs de respaldo cloud (ej. Gemini), resultando en un costo monetario inferior a $\$0.05$ USD por misión de investigación para finales de mes.
*   **Fórmula:**
    $$\text{Costo Misión} = \text{Tokens Cloud} \times \text{Tarifa Cloud} \le \$0.05 \text{ USD}$$

_Última actualización: `2026-06-01`._
