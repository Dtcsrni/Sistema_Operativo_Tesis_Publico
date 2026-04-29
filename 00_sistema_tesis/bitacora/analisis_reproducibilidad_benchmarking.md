# Análisis de Estándares de Reproducibilidad en Benchmarking de IA

Este documento analiza las mejores prácticas de la industria y la academia para garantizar que los resultados de pruebas en sistemas de IA sean reproducibles, audibles y libres de "alucinaciones" documentales.

## 1. Referentes de la Industria y Academia

### A. MLPerf (MLCommons)
Es el estándar de facto. Su metodología para garantizar reproducibilidad se basa en:
- **Submission Packages:** No basta con el número; se debe entregar el código exacto, los archivos de configuración (`dockerfiles`, `yaml`) y los logs de salida sin procesar.
- **Auditabilidad:** Un comité de auditoría revisa los logs en busca de anomalías estadísticas que sugieran manipulación o errores de medición.
- **Hardware Metadata:** Registro exhaustivo de la frecuencia de reloj, temperatura, versión del kernel y versiones de los drivers (ej. RKNN version).

### B. Artifact Evaluation (NeurIPS / MLSys)
Utilizan una **Reproducibility Checklist** que incluye:
- **Dependencias:** Especificación exacta de versiones (`requirements.txt`, `poetry.lock`).
- **Semillas Aleatorias:** Garantizar que los procesos estocásticos sean deterministas si se desea repetir la prueba exactamente.
- **Environment Captures:** Captura automática de variables de entorno y estado del sistema antes de la prueba.

## 2. Comparativa con SIOT (Estado Actual)

| Característica | Estándar Ideal | Implementación SIOT (PEV-01) | Estado |
| :--- | :--- | :--- | :--- |
| **Logs Crudos** | Requerido (JSONL/CSV) | `standardized_run.jsonl` | **CUMPLIDO** |
| **Metadatos HW** | Requerido (Versión, Temp) | Captura en `get_system_telemetry()` | **CUMPLIDO** |
| **Integridad** | Deseable (Hashes) | Canon de Eventos con SHA-256 | **SUPERADO** |
| **Código Auditado** | Requerido (Git Hash) | Vinculación de eventos a commits | **CUMPLIDO** |
| **Visualización** | Complementaria | Capturas generadas (Dashboard) | **AUXILIAR** |

## 3. Recomendaciones para la Tesis

Para fortalecer la sección de "Validación Científica", se sugiere adoptar el formato de **"Hojas de Datos de Evidencia"** que incluyan:
1.  **Enlace al Log Crudo:** El evaluador debe poder ver la varianza latido a latido.
2.  **Script de Re-ejecución:** Proporcionar un comando único (`python run_scientific_benchmark.py`) que genere el mismo formato de salida.
3.  **Hash de Validación:** Incluir el SHA-256 del archivo de resultados en el cuerpo de la tesis, vinculándolo al Ledger de este repositorio.

## 4. Conclusión
El uso de imágenes generadas es útil para la comunicación visual, pero la **reproducibilidad científica** de SIOT reside en la cadena de custodia de los archivos `.jsonl` protegidos por el sistema de gobernanza del repositorio.

---
[LID]: 00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md
[GOV]: 00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md
[AUD]: historial interno no público/security_report_2026-04-28_0334.json

_Última actualización: `2026-04-29`._
