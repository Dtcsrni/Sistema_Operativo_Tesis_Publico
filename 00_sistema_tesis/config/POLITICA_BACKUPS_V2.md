# Política de Backups Mejorada (Git-First)
**Versión 2.0 | 2026-05-13**

<!-- SISTEMA_TESIS:PROTEGIDO -->

## Principios Base

1. **Git es el Backup Principal**: Todo cambio está versionado (`git log`, ramas, stash). Los archivos `.bak` locales son secundarios.
2. **Excepción Controlada**: Solo mantener `.bak` bajo protocolo **PCB (Pre-Change Backup)** para cambios disruptivos en archivos protegidos.
3. **Eficiencia Agresiva**: Límites reducidos (100 archivos, 256MB) vs. anteriores (500 archivos, 1GB).

## Protocolo PCB (Pre-Change Backup)

**Cuándo se activa:**
- Cambio manual en archivo `<!-- SISTEMA_TESIS:PROTEGIDO -->`
- Actualización de políticas o gobernanza
- Cambios en infraestructura crítica (docker-compose, Dockerfile, etc.)

**Acciones automáticas:**
1. Crear backup con timestamp: `archivo.YYYYMMDD_HHMMSS.bak`
2. Registrar en `config/backups/` con prefijo descriptivo
3. Comprimir a `.bak.gz` después de 7 días
4. Retener máximo 3 versiones de cada archivo crítico
5. Purgar automaticamente después de 14 días

## Clasificación de Riesgo

| Riesgo | Retención | Ejemplo |
|--------|-----------|---------|
| **Crítico** | 14 días | `00_sistema_tesis_decisiones_*.md`, `canon_events.jsonl`, Ledger, Matriz |
| **Alto** | 7 días | `00_sistema_tesis_bitacora_*.md`, `config/env/*.env` |
| **Operativo** | 3 días | Scripts de diagnóstico, compilaciones, temporales |

## Automatización (rotate_backups.py)

**Ejecución:**
```bash
# Dry-run (recomendado semanal)
python 07_scripts/ops/rotate_backups.py

# Con cambios (activado por cron/scheduler)
python 07_scripts/ops/rotate_backups.py --apply

# Solo compresión sin purga
python 07_scripts/ops/rotate_backups.py --compress-only
```

**Funcionalidades:**
- ✅ Compresión gzip automática de backups >7 días (-60% espacio aprox.)
- ✅ Deduplicación por SHA-256 (elimina copias idénticas)
- ✅ Priorización inteligente (purga por riesgo: operativo → alto → crítico)
- ✅ Logging detallado en `config/logs/backup_rotation.log`
- ✅ Telemetría a `long_process_monitor` si purga >50MB

## Límites Actuales

```json
{
  "max_files": 100,
  "max_total_size_mb": 256,
  "min_protected_days": 7,
  "compression_trigger_days": 7
}
```

**Exceso de límites:** Se purga automáticamente por antigüedad, priorizando riesgo operativo.

## Limpieza Inicial (cleanup_backup_dir.py)

Ejecutada **2026-05-13**:
- ✅ Eliminados 18 de 23 archivos redundantes (78%)
- ✅ Espacio liberado: ~0.06MB (pequeño pero agresivo en eliminar basura)
- ✅ Mantenidos 5 críticos: 2 decisiones + 1 canon + Ledger + Matriz

**Reglas aplicadas:**
1. Guardar últimos 3 de cada crítico
2. Eliminar completamente: legacy operational, envs redundantes, runtime garbage
3. Preservar: Canon, Decisiones, Ledger, Matriz de Trazabilidad

## Integración con Gobernanza

- **AGENTS.md § 8:** Actualizado con política Git-First
- **backup_rotation_policy.json:** Versión 2.0 con compresión + deduplicación
- **rotate_backups.py:** Mejorado con logging + telemetría
- **cleanup_backup_dir.py:** Script interactivo para limpieza inicial de backups legacy

## Esperado Impacto

| Métrica | Antes | Después |
|---------|-------|---------|
| Archivos en `/config/backups/` | 23 | 5 (limpieza) → 100 (límite) |
| Tamaño típico | ~0.43MB | ~0.25MB (tras compresión) |
| Retención máxima | 180 días (crítico) | 14 días (crítico) |
| Automatización | Manual dry-run | Semanal con telemetría |

## Próximos Pasos

1. **Programar ejecución:** Cron/Windows Scheduler ejecute `rotate_backups.py --apply` semanal
2. **Monitorear logs:** Revisar `config/logs/backup_rotation.log` mensualmente
3. **Documentar PCB:** Trainer a humanos sobre cuándo disparar protocolo PCB
4. **Auditoría trimestral:** Ejecutar `cleanup_backup_dir.py` con revisión humana

---
**Aprobado por:** Política de Gobernanza AGENTS.md § 8  
**Implementación:** 2026-05-13  
**Próxima revisión:** 2026-08-13

_Última actualización: `2026-05-15`._
