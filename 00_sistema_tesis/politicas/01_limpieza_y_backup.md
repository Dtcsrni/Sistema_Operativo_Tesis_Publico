# Política de limpieza y respaldo

## Objetivo

Mantener el repositorio limpio, legible y trazable sin perder evidencia útil ni comprometer la operación del sistema.

## Alcance

Aplica a archivos temporales, logs de trabajo, backups locales, caches, artefactos generados y superficies derivadas no canónicas.

## Reglas base

1. Conservar solo los 3 backups más recientes por archivo crítico.
2. Nombrar backups con formato `NOMBRE.bak.YYYYMMDD_HHMMSS`.
3. Nombrar archivos históricos archivados con formato `ARCHIVO_YYYY-MM-DD_HHMMSS` para evitar colisiones.
4. Preferir `--dry-run` antes de cualquier eliminación real.
5. No eliminar bitácoras activas, ledger, matriz de trazabilidad, evidencia privada ni decisiones sin revisión humana.
6. Archivar antes de borrar cuando el contenido pueda aportar contexto histórico.

## Clasificación

### Críticos

- `AGENTS.md`
- `README_INICIO.md`
- `MEMORY.md`
- `00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md`
- `00_sistema_tesis/bitacora/matriz_trazabilidad.md`

### Limpieza periódica

- archivos `*.bak.*` fuera del límite de retención
- `build_log.txt`
- `final_audit_v*.txt`
- `temp_payload.json`
- `hash_result.txt`
- `real_hashes.txt`
- `tmp_ledger_entry.txt`
- caches y scratch no canónicos

## Operación

1. Ejecutar `python 07_scripts/auto_cleanup.py --dry-run`.
2. Revisar el reporte.
3. Si el alcance es correcto, repetir con `--apply`.
4. Registrar el resultado en bitácora cuando afecte archivos rastreados.

## Excepciones

- No limpiar evidencia privada activa.
- No tocar archivos protegidos por `<!-- SISTEMA_TESIS:PROTEGIDO -->` sin mecanismo de guardrails correspondiente.
- No confundir archivos de respaldo con documentación vigente si están explícitamente referenciados por el sistema.

_Última actualización: `2026-05-15`._
