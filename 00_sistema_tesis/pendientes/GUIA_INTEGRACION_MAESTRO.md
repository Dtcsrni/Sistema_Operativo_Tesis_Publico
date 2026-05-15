<!-- GUÍA DE INTEGRACIÓN: OPENCLAW MAESTRO MOE INTEGRADO -->

# Guía de Integración Maestro MoE

**Fecha:** 2026-05-05  
**Estado:** Implementado detrás de feature flag

## Flujo Integrado

1. Telegram recibe texto y entra por `process_channel_text(...)`.
2. Si `OPENCLAW_MAESTRO_ENABLED=1`, se calcula `MaestroRouteDecision`.
3. La decisión se guarda en SQLite mediante `OpenClawStore.save_maestro_route_decision(...)`.
4. La decisión se cachea por hash del mensaje para que `_chat_request_profile(...)` la use antes del ruteo de modelo.
5. `dispatch_command(...)`, APR, Step ID, cache, síntesis y fallback existentes siguen operando.
6. La respuesta incluye `maestro_route` y queda ligada a la sesión.

## Configuración

Default recomendado hasta cierre de pruebas:

```ini
OPENCLAW_MAESTRO_ENABLED=0
OPENCLAW_MAESTRO_SESSION_TTL=3600
OPENCLAW_MAESTRO_CHAT_FAST_P95_MS=12000
OPENCLAW_MAESTRO_TECH_P95_MS=30000
OPENCLAW_MAESTRO_RESEARCH_P95_MS=90000
OPENCLAW_MAESTRO_EDGE_OPS_P95_MS=15000
```

## Pruebas

Comandos de validación técnica:

```bash
pytest -q tests/test_openclaw_sources_and_routing.py
python3 07_scripts/benchmarks/run_maestro_moe_benchmark.py --iterations 3
python3 07_scripts/audit/verify_benchmark_artifacts.py
python3 07_scripts/audit/verify_benchmark_precision.py
python3 07_scripts/build_all.py
```

## Operación Edge

La Orange Pi permanece como asistente científico secundario operativo: estado, continuidad, telemetría, comandos seguros y fallback local. La NPU no entra en la cadena normal mientras `runtime/edge_iot/benchmarks/index.json` no sea evidencia científica válida.

## Cierre Humano

Maestro no valida autónomamente. La activación por defecto y cualquier cierre canónico requieren Step ID humano y registro trazable en ledger/matriz.

_Última actualización: `2026-05-15`._
