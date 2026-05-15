# Mission Control - Setup para Tesis Posgrado

## Estado Actual

✅ **Servidor corriendo**: `http://localhost:4000`  
✅ **Base de datos**: SQLite (782KB, 20 migraciones)  
✅ **Telemetría integrada**: Toltecayotl ↔ Mission Control  
✅ **Eventos almacenados**: 3+ pruebas exitosas (201 Created)

## Arrancar Servidor

```powershell
docker compose up -d --build
```

El servidor estará disponible en `http://localhost:4000`

## Enviar Telemetría

### Opción 1: Script Python (Recomendado)

```powershell
# Enviar eventos de prueba
python 07_scripts/test_mission_control.py
```

### Opción 2: Ejecutar Orquestador Toltecayotl

```bash
# Simula agentes Edge/PC/Bot enviando telemetría en tiempo real
cd 07_scripts/toltecayotl
python toltecayotl_orchestrator.py
```

Los eventos aparecerán en:
- Endpoint: `POST http://localhost:4000/api/events` (201)
- BD: Tabla `events` en `mission-control.db`

### Opción 3: cURL Manual

```powershell
# Crear evento manualmente
curl -X POST http://localhost:4000/api/events `
  -ContentType "application/json" `
  -Body @'
{
  "type": "agent.token",
  "message": "[Triage] Processing request",
  "metadata": {
    "agent_name": "Triage",
    "text": "clasificando...",
    "ts": 1714734900
  }
}
'@
```

## Endpoints Disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/events` | Listar eventos (últimos 50) |
| POST | `/api/events` | Crear evento (telemetría) |
| GET | `/api/agents` | Listar agentes |
| GET | `/api/tasks` | Listar tareas |
| POST | `/api/agents/discover` | Auto-descubrir agentes |

## Estructura de Telemetría

```json
{
  "type": "agent.token|agent.finish|agent.error",
  "message": "Descripción legible",
  "agent_id": "uuid_opcional",
  "task_id": "uuid_opcional",
  "metadata": {
    "agent_name": "Triage|Reasoning|etc",
    "text": "contenido del evento",
    "duration": 2.5,
    "ts": 1714734900.123
  }
}
```

## Variables de Entorno

| Variable | Valor Por Defecto | Descripción |
|----------|------------------|-------------|
| `PORT` | 4000 | Puerto del servidor |
| `DATABASE_PATH` | `mission-control.db` | Ruta BD SQLite |
| `MISSION_CONTROL_URL` | `http://localhost:4000/api/events` | Endpoint telemetría |

## Documentación Adicional

- [INTEGRATION.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/04_implementacion/control_mission/INTEGRATION.md) - Detalles técnicos
- [README.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/04_implementacion/control_mission/README.md) - Setup original (Autensa)
- [docs/AGENT_PROTOCOL.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/04_implementacion/control_mission/docs/AGENT_PROTOCOL.md) - Protocolo de agentes
- [docs/REALTIME_SPEC.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/04_implementacion/control_mission/docs/REALTIME_SPEC.md) - Especificación real-time

## Troubleshooting

**Error: `PORT` no reconocido**
- Solución: Editar `package.json` línea 5 (ya corregido)

**Conexión rechazada a localhost:4000**
- Verificar: `docker compose ps` muestra `mission-control` healthy
- Verificar puerto: `netstat -ano | findstr :4000`

**Eventos no aparecen en UI**
- Los eventos se guardan en BD aunque el UI no los muestre (SSE local limitation)
- Verificar en BD: `sqlite3 mission-control.db "SELECT * FROM events LIMIT 5;"`

_Última actualización: `2026-05-15`._
