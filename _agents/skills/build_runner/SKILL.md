---
name: build_runner
description: >
  Sistema de build modular e incremental del proyecto SIOT/OpenClaw.
  Reemplaza el build_all.py monolítico con un motor que soporta
  ejecucion incremental (cache SHA-256), filtrado por grupo/tag/label,
  dry-run, fail-fast y perfilado detallado de cada paso.
  Usa esta skill antes de modificar o ejecutar el sistema de build.
version: "2.0"
applies_to:
  - vscode_agents
  - antigravity
  - ci_cd
agnostic: true
---

# Skill: build_runner

## Ubicacion de archivos

```
07_scripts/
  build_all.py              <- Entry point CLI principal
  build_runner/
    __init__.py
    registry.py             <- Catalogo de TODOS los pasos (editar aqui para añadir/quitar)
    cache.py                <- Cache incremental SHA-256 por fingerprint de archivos
    runner.py               <- Motor de ejecucion, StepReport, perfiles JSON
```

## Comandos esenciales

```powershell
# Build completo (incremental: omite pasos sin cambios)
python 07_scripts/build_all.py

# Ver que se ejecutaria SIN ejecutar nada
python 07_scripts/build_all.py --dry-run

# Listar todos los pasos con grupos, tags y estado de cache
python 07_scripts/build_all.py --list

# Solo pasos del grupo 'openclaw' (mas rapido en desarrollo)
python 07_scripts/build_all.py --group openclaw

# Solo pasos con tag 'audit' (post-edicion de bitacora)
python 07_scripts/build_all.py --tag audit

# Un paso exacto por nombre
python 07_scripts/build_all.py --only "Auditar Ledger IA"

# Forzar re-ejecucion aunque no haya cambios
python 07_scripts/build_all.py --group canon --force

# Detener en el primer fallo real (no soft_fail)
python 07_scripts/build_all.py --fail-fast

# Limpiar cache incremental completa
python 07_scripts/build_all.py --clear-cache
```

## Grupos disponibles y su proposito

| Grupo        | Cuando usarlo                                          |
|--------------|--------------------------------------------------------|
| `canon`      | Tras editar archivos en `00_sistema_tesis/canon/`      |
| `integridad` | Tras editar ledger, bitacora, o scripts                |
| `seguridad`  | Tras cambios en runtime/ o 07_scripts/                 |
| `estructura` | Tras cambios en decisiones/ o estructura de directorios|
| `evidencia`  | Tras actualizar benchmarks o conversaciones            |
| `generacion` | Tras editar fuentes de wiki, README o dashboard        |
| `openclaw`   | Tras editar cualquier modulo de openclaw_local/        |
| `backups`    | Auditoria de rotacion (normalmente incluida en full)   |
| `ux`         | Tras cambios en 06_dashboard/                          |
| `publicacion`| Antes de publicar el sitio derivado                    |
| `infra`      | Verificacion de Docker y nodo edge (soft_fail ambos)   |

## Tags utiles para filtrado cruzado

| Tag         | Descripcion                                        |
|-------------|---------------------------------------------------|
| `core`      | Pasos criticos (canon, audit)                     |
| `audit`     | Todas las auditorias                              |
| `integrity` | Verificaciones de integridad del sistema          |
| `security`  | Escaneos y auditorias de seguridad                |
| `generate`  | Pasos que generan artefactos (wiki, dashboard...) |
| `validate`  | Pasos que solo validan (no generan)               |
| `publish`   | Pasos de publicacion publica                      |
| `openclaw`  | Pasos especificos de OpenClaw                     |
| `edge`      | Pasos que verifican el nodo edge                  |
| `benchmark` | Pasos de evidencia de benchmark                   |
| `ledger`    | Verificacion de bitacora y cadena                 |

## Como añadir un nuevo paso al build

Edita `07_scripts/build_runner/registry.py` y añade un `BuildStep` en el grupo apropiado:

```python
BuildStep(
    label="Mi nuevo paso",           # Nombre unico y legible
    script="07_scripts/mi_script.py",
    args=["--mi-arg"],
    group="openclaw",                # Grupo logico
    tags=["openclaw", "validate"],   # Para filtrado
    watch=["runtime/openclaw/**"],   # Globs: si cambian, invalida cache
    soft_fail=False,                 # True = no detiene el build si falla
    budget_s=10.0,                   # Advertencia si tarda mas de esto
),
```

## Cache incremental -- como funciona

1. Al ejecutar un paso, se calcula SHA-256 del contenido de todos los archivos
   que coinciden con los globs en `watch:`.
2. Si el fingerprint es identico al guardado en `.build_cache.json` Y el paso
   termino en `ok`, el paso se omite completamente (0ms).
3. Si algun archivo vigilado cambia → cache miss → paso se re-ejecuta.
4. Pasos sin campo `watch` siempre se ejecutan (no tienen cache).

**Regla de oro:** Si modificas un archivo, el proximo build re-ejecutara
automaticamente todos los pasos que lo vigilan. No hay que invalidar
manualmente salvo casos de depuracion (--force o --clear-cache).

## Perfil JSON de cada build

Cada ejecucion genera dos archivos en `historial interno no público/`:
- `build_all_profile_YYYYMMDD_HHMMSS.json` — historico inmutable
- `build_all_profile_latest.json` — siempre apunta al ultimo build

El perfil incluye: duracion por paso, estado (ok/slow/failed/skipped), cache_hit,
resumen agregado (ejecutados/omitidos/lentos/fallidos).

## Modo de depuracion recomendado

```powershell
# 1. Ver que fallaria sin ejecutar
python 07_scripts/build_all.py --dry-run --fail-fast

# 2. Ejecutar solo el grupo relevante con salida detallada
python 07_scripts/build_all.py --group openclaw --force

# 3. Ejecutar paso exacto aislado
python 07_scripts/build_all.py --only "Auditar Ledger IA" --force

# 4. Ver el perfil del ultimo build
Get-Content historial interno no público/build_all_profile_latest.json | ConvertFrom-Json | Select-Object summary
```

## Integracion con AGENTS.md

- Antes de cerrar cualquier sesion de trabajo, ejecutar `python 07_scripts/build_all.py`
- Para cambios en ledger/bitacora: `python 07_scripts/build_all.py --tag ledger --tag audit`
- Para cambios en OpenClaw: `python 07_scripts/build_all.py --group openclaw`
- El build NO bloquea el flujo de trabajo: pasos `soft_fail=True` (Docker, edge remoto)
  generan advertencia pero no interrumpen.

## Compatibilidad backward

Ejecutar `python 07_scripts/build_all.py` sin argumentos es identico al comportamiento
anterior del script monolitico. Todos los 36 pasos se ejecutan en el mismo orden.

_Última actualización: `2026-04-29`._
