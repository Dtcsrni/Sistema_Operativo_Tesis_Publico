# Protocolo de Operación del Stack: Mission Control

Este protocolo define la inicialización, mantenimiento y optimización del stack de orquestación agéntica.

## 1. Inicialización (Bootstrap)

Para levantar el stack por primera vez o tras un reset:
1. Asegurar que `.env` existe en la raíz de `04_implementacion/control_mission/`.
2. Ejecutar:
   ```bash
   docker-compose up -d --build
   ```
3. Verificar salud:
   ```bash
   docker inspect --format='{{json .State.Health}}' mission-control
   ```

## 2. Estados de Consumo (Resiliencia Epistémica)

El stack soporta dos modos operativos para equilibrar rendimiento y ahorro de recursos:

### A. MODO ACTIVO (Performance)
- **Uso**: Durante sesiones de investigación intensiva o depuración.
- **Configuración**: `PLANNING_POLL_INTERVAL_MS=2000`
- **Comando**: `python scripts/stack_manager.py mode active`

### B. MODO ECO (Pasivo)
- **Uso**: Periodos de inactividad, noche o espera de procesos largos.
- **Configuración**: `PLANNING_POLL_INTERVAL_MS=15000` (15 segundos)
- **Impacto**: Reduce ciclos de CPU del contenedor en un ~70% al minimizar las peticiones a la DB y al Gateway.
- **Comando**: `python scripts/stack_manager.py mode eco`

## 3. Resiliencia y Recuperación

- **Reinicio Automático**: Docker está configurado con `unless-stopped`. Si el proceso de Next.js falla por OOM o error interno, el healthcheck disparará un reinicio tras 3 fallos.
- **Backups de DB**: Los volúmenes persisten en `mission-control-data`. Se recomienda ejecutar `python scripts/backup_db.py` semanalmente.
- **Límites de Recursos**: El stack está topado a **512MB de RAM** y **0.5 CPU cores**. Si el consumo sube, Docker aplicará throttling en lugar de permitir que el stack sature el host.

---
## 4. Retroalimentación Visual (Hardware LED)

El nodo Edge (Orange Pi 5 Plus) utiliza sus LEDs integrados para proporcionar telemetría visual en tiempo real sin necesidad de un monitor:

### LEYENDA DE SEÑALES
| Color | Patrón | Significado | Estado del Sistema |
|---|---|---|---|
| 🟢 Verde | **Pulso Lento** (0.2Hz) | Modo ECO / IDLE | Bajo consumo, sin tareas activas. |
| 🟢 Verde | **Latido** (1Hz) | Sistema OK | Operativo, carga de CPU mínima. |
| 🟢 Verde | **Parpadeo Variable** | Carga de CPU | La frecuencia aumenta con la carga de trabajo. |
| 🔵 Azul | **Parpadeo Rápido** | Inferencia NPU | Procesando modelos de lenguaje o visión (RKLLM). |
| 🟢+🔵 Mixto | **Estroboscopio** | ALERTA CRÍTICA | Temperatura > 75°C o saturación de recursos. |

### CONSIDERACIONES TÉCNICAS
- El control se realiza mediante el driver `orange_pi_led.py` interactuando con `/sys/class/leds/`.
- El servicio `siot-hw-monitor` debe ejecutarse con privilegios para acceder a `/sys/kernel/debug/rknpu/load`.

---
**GID:** [GID-MC-PROTO-2026]
**Status:** IMPLEMENTADO (v2.1 LED-Enhanced)

_Última actualización: `2026-05-15`._
