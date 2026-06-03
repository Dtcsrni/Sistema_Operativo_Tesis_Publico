# Operación del Harness Engineering

## Comandos principales

```powershell
python 07_scripts/harness/cli.py manifest --json
python 07_scripts/harness/cli.py record --source build_all --profile historial interno no público/build_all_profile_latest.json --json
python 07_scripts/harness/cli.py score --json
python 07_scripts/harness/cli.py verify --json
python 07_scripts/harness/cli.py report --public-json
```

## Flujo recomendado para agentes

1. Ejecutar `manifest` para declarar el contrato de trabajo.
2. Ejecutar el flujo real del subsistema: pruebas, build, publicación o misión.
3. Registrar el resultado con `record`.
4. Calcular `score`.
5. Ejecutar `verify` antes de cerrar o proponer validación humana.

## Perfiles ágiles de auditoría

Estos comandos son portables para cualquier agente o IDE con acceso al repositorio:

```powershell
python 07_scripts/build_all.py --profile dev --fail-fast
python 07_scripts/build_all.py --profile changed --dry-run --explain
python 07_scripts/build_all.py --profile smoke --fail-fast
python 07_scripts/build_all.py --profile full --fail-fast
python 07_scripts/build_all.py --profile release
```

- `dev`: ciclo diario de implementación con pruebas rápidas por impacto.
- `changed`: explica y ejecuta pasos afectados por rutas modificadas.
- `smoke`: salud mínima antes de handoff corto.
- `full`: gate completo incremental compatible con el contrato histórico.
- `release`: gate completo estricto; no sustituye validación humana.

## Uso con Mission Control

Las misiones deben referenciar el `run_id` del harness cuando generen entregables o ejecuten gates técnicos. El estado `review` significa que los entregables existen y están listos para revisión humana; no implica validación.

## Uso con OpenClaw y Toltecayotl

OpenClaw aporta proveedor activo, runtime, gateway y modelo. Toltecayotl aporta métricas epistémicas como fidelidad, densidad de evidencia y juez de calidad. El harness solo agrega esas señales; no decide por sí mismo la aceptación académica.

## Publicación

El reporte público debe provenir de `06_dashboard/generado/harness_readiness_public.json`. Si un campo requiere redacción, se reemplaza por `[redacted]` o se omite.

_Última actualización: `2026-06-03`._
