# OpenClaw Mission Control - Integración Toltecayotl

## Estado

✅ Mission Control (Next.js + SQLite) instalado y corriendo en `http://localhost:4000`
✅ Base de datos inicializada con esquemas v1-v20
✅ Endpoint `/api/events` disponible para telemetría
✅ `toltecayotl_orchestrator.py` configurado para enviar eventos

## Arquitectura

```
Mission Control (SQLite)
      ↑
      │ POST /api/events
      │
toltecayotl_orchestrator.py
      ↑
      │ agentes Edge/PC/Bot
```

## URL Telemetría

**Producción (local dev):**
```
http://localhost:4000/api/events
```

**Variable de entorno (opcional):**
```bash
set MISSION_CONTROL_URL=http://localhost:4000/api/events
```

## Formato de Eventos

POST a `/api/events` con payload:
```json
{
  "type": "agent.token|agent.finish",
  "message": "Descripción del evento",
  "agent_id": "opcional_uuid",
  "task_id": "opcional_uuid",
  "metadata": {
    "agent_name": "Triage|Reasoning|etc",
    "text": "token recibido",
    "duration": "segundos",
    "ts": "timestamp"
  }
}
```

## Pruebas

### 1. Verificar servidor corriendo
```powershell
curl http://localhost:4000/api/events -Method GET
```

### 2. Crear evento manual
```powershell
curl -X POST http://localhost:4000/api/events `
  -ContentType "application/json" `
  -Body '{"type":"agent.token","message":"Test event","metadata":{"agent":"test"}}'
```

### 3. Ejecutar orquestador (simula telemetría)
```bash
cd 07_scripts/toltecayotl
python toltecayotl_orchestrator.py
```

## Documentación Adicional

- [README.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/04_implementacion/control_mission/README.md) - Setup general
- [docs/AGENT_PROTOCOL.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/04_implementacion/control_mission/docs/AGENT_PROTOCOL.md) - Protocolo de agentes
- [docs/REALTIME_SPEC.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/04_implementacion/control_mission/docs/REALTIME_SPEC.md) - Especificación real-time

_Última actualización: `2026-05-15`._
