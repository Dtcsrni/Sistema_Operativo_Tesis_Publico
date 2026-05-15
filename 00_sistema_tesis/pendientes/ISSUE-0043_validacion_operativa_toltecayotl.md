---
title: "ISSUE-0043: Validación Operativa y Sincronización Toltecayotl"
date: 2026-05-01
category: enhancement
status: open
reporter: "Codex"
---

# ISSUE-0043: Validación Operativa y Sincronización Toltecayotl

**Estado operativo:** Pendiente de inicio en próxima sesión
**Prioridad:** ALTA
**Vinculación:** Derivado de ISSUE-0042 (Refactorización exitosa)
**Decisión rectora:** `DEC-0028` (v2)

## Contexto
Tras completar la refactorización identitaria de Atzin a **Toltecayotl**, el sistema es estructuralmente correcto pero requiere validación funcional de extremo a extremo para declararse "Estable v1.0".

## Tareas técnicas pendientes

- [x] **Estandarización de Formato (DEC-0029)**: Formato TEB JSONL con hashing y procedencia.
- [x] **Implementación de Ingestor TEB**: Script `ingest_literature.py` funcional y validado.
- [ ] **Prueba de Ingesta Real**: Ingestar un documento académico PDF complejo y verificar integridad.
- [ ] **Sincronización PC -> Edge**: Exportar acervo TEB e importar en Orange Pi.
- [x] **Actualización de Build Registry**: Añadidos `watch` paths para Toltecayotl en `registry.py`.
- [ ] **Cierre de Fase B0**: Obtener Step ID final.

## Evidencia esperada
1. Reporte de ingesta exitosa en Weaviate.
2. Paquete `.jsonl` de sincronización firmado criptográficamente.
3. Auditoría `build_all.py` 100% verde con las nuevas dependencias (PyYAML).

## Notas de Triage
Este issue actúa como el "puente" para cerrar la fase de infraestructura e iniciar la fase de ingestión masiva de literatura para la tesis.

_Última actualización: `2026-05-15`._
