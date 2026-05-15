---
title: "ISSUE-0044: Plan Integral de Limpieza y Mejora del Repositorio"
date: 2026-05-01
category: maintenance
status: closed
reporter: "Codex"
---

# ISSUE-0044: Plan Integral de Limpieza y Mejora del Repositorio

**Estado operativo:** Completado y Validado (validación humana interna no pública)
**Prioridad:** MEDIA-ALTA
**Vinculación:** DEC-0022 (Vigente)

## Contexto
El repositorio ha acumulado una cantidad significativa de archivos técnicos redundantes, scripts desorganizados y documentación que requiere una actualización estética y estructural tras la migración a la arquitectura **Toltecayotl**.

## Fases del Plan

1. **Limpieza de Residuos**: Eliminar `.bak`, logs y temporales obsoletos.
2. **Reorganización de Scripts**: Consolidar `07_scripts` en subdirectorios lógicos.
3. **Políticas de Backup**: Automatizar rotación y definir políticas en `AGENTS.md`.
4. **Auditoría de Seguridad**: CVEs y dependencias.
5. **Expansión Wiki**: Navegación y diseño premium.
6. **Diagramación**: Mermaid C4 y flujos GraphRAG.
7. **Trazabilidad**: Completar matriz y validar hashes.

## Tareas Técnicas

- [x] Fase 1: Identificar y eliminar archivos basura.
- [x] Fase 2: Mover scripts a `07_scripts/{benchmarks,audit,ops,utils}`.
- [x] Fase 3: Crear `rotate_backups.py`.
- [x] Fase 4: Ejecutar `pip-audit`.
- [x] Fase 5: Actualizar Wiki.
- [x] Fase 6: Generar diagramas.
- [x] Fase 7: Validación final.

## Avance de ejecución (2026-05-01)

- Fase 1 validada por corrida de `python 07_scripts/ops/auto_cleanup.py --json` sin hallazgos pendientes (`0` ítems).
- Fase 2 confirmada por estructura operativa activa en `07_scripts/README.md` y subdirectorios `07_scripts/audit`, `07_scripts/benchmarks`, `07_scripts/ops`, `07_scripts/utils`.
- Fase 3 confirmada con `07_scripts/ops/rotate_backups.py` y política de retención documentada en `AGENTS.md` (sección de retención/rotación).
- Fase 4 completada: `python -m pip_audit` detectó CVEs en `pip 25.0.1`; se aplicó remediación con `python -m pip install --upgrade pip` a `26.1` y reauditoría posterior sin vulnerabilidades conocidas.
- Fase 5 completada: Wiki modernizada con Glassmorphism y navegación avanzada.
- Fase 6 completada: Diagramas C4 y flujos GraphRAG integrados en `arquitectura.md`.
- Fase 7 completada: Auditoría de integridad de ledger reparada y validada (`build_all.py` OK).

## Criterio de aceptación humana
- [x] El Tesista autoriza el inicio del plan con validación humana interna no pública.
- [x] El Tesista valida la continuidad para Fases 5-7 con validación humana interna no pública.

_Última actualización: `2026-05-15`._
