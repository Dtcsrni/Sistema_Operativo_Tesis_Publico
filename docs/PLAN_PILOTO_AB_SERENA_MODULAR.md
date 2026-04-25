# Plan de implementacion y cierre experimental del piloto Serena

Este documento define el arranque tecnico y el cierre documental del piloto Serena.

## Objetivo

Documentar la experimentacion local de Serena para reducir tokens y costo sin degradar cumplimiento de gobernanza, trazabilidad y calidad.

## Estado de la decision

- Serena se conserva como utileria local de linea de comandos.
- Serena se implementa tambien como servidor MCP local por `stdio` para VS Code con Codex.
- El pipeline principal permanece intacto.
- La salida del piloto se usa como evidencia analitica, no como reemplazo de validacion humana.

## Estado actual v1.1

- La ruta CLI sigue siendo la via reproducible para ejecutar el piloto Serena/AB.
- La ruta MCP agrega integracion operativa para contexto compacto, preflight de gobernanza y cambios auditables desde el host.
- El MCP no reemplaza `tesis.py`, `ab_pilot.py` ni la validacion humana.
- La integracion objetivo de esta fase es VS Code + Codex con servidor `serena-local`.

## Alcance inicial

- Implementar utileria local para ejecutar y evaluar Serena.
- Mantener el pipeline principal intacto en esta fase.
- Usar escritura controlada para registrar resultados de evaluacion.
- Documentar la experimentacion y su trazabilidad asociada.

## Artefactos creados

- Script de piloto: 07_scripts/ab_pilot.py
- Pruebas unitarias: 07_scripts/tests/test_ab_pilot.py
- Plantilla de plan (se crea por comando): 00_sistema_tesis/config/ab_pilot_plan.json
- Plantilla CSV (se crea por comando): 00_sistema_tesis/plantillas/ab_pilot_tasks_template.csv
- Reporte JSON (se crea por comando): 00_sistema_tesis/config/ab_pilot_report.json
- Reporte Markdown (se crea por comando): 06_dashboard/generado/ab_pilot_report.md

## Flujo de uso

1. Crear la plantilla CSV o el plan base.
2. Editar `00_sistema_tesis/config/ab_pilot_plan.json` con tareas reales.
3. Ejecutar `python 07_scripts/ab_pilot.py evaluate --plan 00_sistema_tesis/config/ab_pilot_plan.json`.
4. Revisar `00_sistema_tesis/config/ab_pilot_report.json`, `06_dashboard/generado/ab_pilot_report.md` y la traza JSONL.

## Metricas comparadas

- input_tokens
- output_tokens
- total_tokens
- total_cost_usd
- avg_latency_ms
- acceptance_rate
- gate_failures
- rework_rate

## Flujo Serena

El piloto evalua una unica ruta activa: Serena.
El reporte conserva trazabilidad por tarea, agregacion por tipo de tarea y un JSONL de auditoria.

## Criterio de cierre documental

- El piloto queda documentado como experimentacion local reproducible.
- La implementacion actual se considera cerrada para esta iteracion cuando CLI y MCP coexisten sin contradicciones documentales.
- Cualquier expansion futura a modular o hibrido requiere una decision nueva y trazabilidad propia.

## Esquema CSV

La plantilla CSV usa estas columnas:
- baseline_complexity
- manual_minutes
- manual_accepted
- manual_gate_failures
- serena_latency_ms
- serena_accepted
- serena_gate_failures
- serena_rework
- modular_input_tokens
- modular_output_tokens
- modular_cost_usd
- min_acceptance_rate
- max_gate_failures

El evaluador actual recomienda una ruta unica: serena.

## Nota de alcance

- Las columnas `modular_*` y `manual_*` permanecen como referencia del plan extendido, pero no forman parte de la implementacion cerrada en esta iteracion.
- La repetibilidad semanal se conserva mediante la misma plantilla de tareas y la misma traza JSONL.
- La captura automatica al journal de operacion IA queda como siguiente fase, no como requisito de cierre.
- La validacion E2E del MCP se documenta en `00_sistema_tesis/documentacion_sistema/operacion_serena_mcp_codex.md`.

_Última actualización: `2026-04-25`._
