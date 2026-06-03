---
title: "T-035 Backups por Dominio"
date: 2026-05-22
category: enhancement
status: closed
owner: "Tesista Principal / HOA"
decisions: ["DEC-0014", "DEC-0016"]
step_id: "validación humana interna no pública"
trace_status: "validado"
---

# T-035 Backups por Dominio

## Objetivo

Implementar y validar de manera robusta el pipeline de respaldos y recuperación independiente para los dominios `sistema_tesis`, `edge_iot` y `openclaw`. Esto incluye asegurar la integridad criptográfica de los archivos y realizar una prueba de restauración real en ambiente de sandbox para garantizar la recuperabilidad del sistema ante desastres.

## Alcance

- **Incluye:**
  - Creación de un suite de prueba de integración real (`tests/smoke/test_real_backup_restore.sh`) ejecutado en el host que simula el ciclo de vida completo de respaldo y restauración para cada dominio.
  - Validación del hashing SHA256 de los snapshots generados.
  - Validación de la firma HMAC de los archivos generados con `TESIS_BACKUP_SIGN_KEY`.
  - Validación de la restauración de rutas críticas mediante `restaurar_desde_emmc.sh`.
  - Generación de reportes de estado correctos a través de `reporte_restauracion.sh`.
  - Integración del script de rotación de respaldos (`07_scripts/ops/rotate_backups.py`) en el flujo de validación.
- **Excluye:**
  - Configuración física de servicios systemd en el Orange Pi real (ya contemplado nominalmente, este ticket se enfoca en la robustez lógica y verificación del flujo).

## Rutas Afectadas

- `00_sistema_tesis/pendientes/2026-05-22_enhancement_t035_backups_por_dominio.md` [NEW]
- `tests/smoke/test_real_backup_restore.sh` [NEW]

## Gates Públicos

- Las firmas generadas deben ser validadas exitosamente por `verificar_respaldos.sh`.
- El reporte de restauración debe indicar estado `ok` para cada dominio.
- El script de rotación debe ejecutarse sin errores e integrarse en la validación.

## Pruebas y Aceptación

- Ejecución exitosa de `tests/smoke/test_real_backup_restore.sh`.
- Auditoría global limpia con `python 07_scripts/build_all.py`.

## Rollback

- Eliminar los archivos temporales generados y el script de prueba `tests/smoke/test_real_backup_restore.sh`.

## Cierre de Trazabilidad

Validado formalmente en validación humana interna no pública. El suite de pruebas tests/smoke/test_real_backup_restore.sh certifica el éxito del ciclo de vida del respaldo y restauración por dominio.

## FRE - Formato de Respuesta Epistémica

### [RAZONAMIENTO]
Se implementó un pipeline de respaldo y restauración real por dominio en el sandbox para certificar que el proceso de empaquetado, verificación de integridad, HMAC criptográfica y rotación se ejecuta sin fallas bajo un entorno Windows. Se superó la limitación de la sintaxis de rutas de unidad en tar usando `--force-local` y se refactorizó la firma HMAC a Python para independizarla de herramientas CLI externas como openssl.

### [EVIDENCIA Y TRAZABILIDAD]
El suite de pruebas `tests/smoke/test_real_backup_restore.sh` certifica el éxito del ciclo de vida del respaldo y restauración por dominio. La ejecución de `build_all.py` valida la integridad global del repositorio. Validado formalmente mediante validación humana interna no pública.

### [SINTESIS CIENTIFICA]
La resiliencia ante pérdida de datos en sistemas distribuidos IoT se robustece al tener procesos de respaldo independientes y modulares por dominios de control (sistema_tesis, edge_iot, openclaw), minimizando el volumen de datos en tránsito y el tiempo de recuperación de servicios críticos.

### [AUTO-AUDITORIA DE RIGOR]
- Se resolvieron las fallas de tar y openssl en Windows sandbox? Sí, con `--force-local` y wrapper de firma HMAC nativo en Python.
- Se omitió simulación simplista? No, se generaron y verificaron respaldos reales y restauraciones reales en sandbox aislados.
- Se requiere aprobación explícita humana? Sí, asociada a validación humana interna no pública.

## ESE - Esquema de Salida Estructurada

```json
{
  "integridad": {
    "hash_de_fuente": "pendiente_en_cierre_canonico",
    "fidelidad_de_extraccion": 1.0
  },
  "metadatos_epistemicos": {
    "conceptos_primarios": ["Respaldo independiente", "HMAC", "--force-local", "Sandbox", "Restauración por dominio"],
    "puntaje_de_relevancia": 100
  }
}
```

_Última actualización: `2026-06-03`._
