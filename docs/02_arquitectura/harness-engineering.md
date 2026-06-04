# Harness Engineering Agnóstico para SIOT

## Propósito

El harness engineering de SIOT es una capa transversal para coordinar, medir y auditar trabajo de agentes de IA diversos sin depender de un proveedor, modelo o runtime específico. Su función es envolver los flujos existentes de `build_all.py`, OpenClaw, Mission Control, Toltecayotl, publicación pública y operación Git con contratos reproducibles.

## Principios de diseño

- **Agnosticismo de agente:** cualquier agente se describe por rol, proveedor, modelo, runtime, herramientas, permisos y clase de privacidad.
- **Local-first:** las trazas y métricas se generan localmente; la proyección pública se sanitiza.
- **Replay verificable:** cada ejecución relevante conserva artefactos, hashes, estado Git y referencias a perfiles de build.
- **Readiness explícito:** el resultado no es una “validación humana”, sino un puntaje técnico de preparación.
- **Observabilidad compatible:** los nombres de eventos se alinean con prácticas GenAI/OpenTelemetry cuando aplica, sin exportar datos sensibles por defecto.

## Componentes

- `07_scripts/harness/core.py`: manifiesto, recorder, score de readiness, sanitización y verificación.
- `07_scripts/harness/cli.py`: entrada operativa para `manifest`, `record`, `score`, `verify` y `report`.
- `historial interno no público/harness_runs.jsonl`: bitácora privada de ejecuciones harness.
- `00_sistema_tesis/config/harness_readiness.json`: readiness privado completo.
- `06_dashboard/generado/harness_readiness_public.json`: readiness público sanitizado.

## Cobertura SIOT

El manifiesto cubre canon, documentación, OpenClaw, Mission Control, Toltecayotl, publicación, CI/CD y Git. Cada subsistema se evalúa por dimensiones comunes: éxito de workflow, cumplimiento de política, trazabilidad, reproducibilidad, seguridad, calidad epistémica y costo/latencia.

## Relación con gobernanza

El harness no sustituye `DEC-0014`, el Ledger ni la Matriz de Trazabilidad. Tampoco puede marcar una tarea como validada. Solo produce evidencia técnica para que el tesista decida si solicita validación humana con Step ID.

## Criterio de aceptación

Una ejecución harness es aceptable si:

1. `python 07_scripts/harness/cli.py verify --json` retorna `ok: true`.
2. `python 07_scripts/build_all.py --group harness --force` finaliza sin fallos.
3. `python 07_scripts/build_all.py` conserva `Fallidos: 0`.
4. El artefacto público no contiene rutas privadas, prompts completos, secretos ni evidencia privada.

_Última actualización: `2026-06-03`._
