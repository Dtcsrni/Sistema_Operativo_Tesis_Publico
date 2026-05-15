# Long Process Monitor Skill (Total Awareness Standard)

Usa esta skill para ejecutar tareas críticas de larga duración (benchmarks, builds, ingesta) bajo el estándar de máxima visibilidad y trazabilidad del Sistema Operativo de Tesis.

## Cuándo usar
- Compilaciones NPU/RKLLM (Procesos intensivos).
- Benchmarking de modelos (Telemetría de recursos).
- Sincronización de acervos (Transferencia de datos).
- Ingesta masiva de literatura en Toltecayotl.

## Protocolo de Sanitización (DEC-0038)

Antes de iniciar cualquier tarea crítica en hosts con recursos limitados (<32GB RAM), el agente DEBE:
1.  Ejecutar `python3 07_scripts/ops/clean_node.py` (en el runtime del repositorio: Docker Compose en PC o Edge).
2.  Solicitar confirmación al usuario para detener servicios pesados (Docker, Ollama, etc.).
3.  Reportar la memoria liberada en la notificación inicial de Telegram.

## Requisitos de Calidad "Total Awareness" (DEC-0037)

Toda implementación DEBE cumplir con la visualización de los siguientes 5 pilares de telemetría:

1. **🏷 Gobernanza Integrada:** Vincular el proceso con el `VAL-STEP` activo y mostrar el `PID` del sistema.
2. **📟 Telemetría Visual de Carga:** Uso de barras textuales (`■■■□□`) para CPU y RAM.
3. **💾 Gestión de Almacenamiento:** Reportar el espacio en disco libre en el nodo de ejecución.
4. **🚀 Animación de Trayectoria:** Barra de progreso con icono móvil y mapa de flujo de fases (`📥 ┈ 🛠 ┈ 🛰 ┈ 🎯`).
5. **🔄 Latido de Actividad (Heartbeat):** Spinner rotativo, marca de tiempo de última actualización (HH:MM:SS) y estado de chat **"Escribiendo..."** persistente.

## Cómo usar (Patrón Premium)

```python
import os
from runtime.openclaw.openclaw_local.progress import AdvancedProgressMonitor

# chat_id obtenido de OPENCLAW_TELEGRAM_CHAT_ID (config/env/openclaw.env)
chat_id = "..." 

title = "Compilación DeepSeek-R1"
with AdvancedProgressMonitor(chat_id, title, total_items=100) as monitor:
    # 1. Notificación inicial con metadatos de gobernanza
    monitor.update(
        current=0, 
        host="WSL-Ubuntu (PC)", 
        val_step="validación humana interna no pública"
    )
    
    # 2. Actualizaciones granulares
    for i in range(100):
        # ... lógica de negocio ...
        monitor.update(
            current=i+1, 
            details=f"Procesando bloque {i}...", 
            host="Docker-Compose (PC)",
            val_step="validación humana interna no pública"
        )
```

## Características Técnicas
- **Hilo de Fondo:** Actualiza automáticamente el spinner, métricas de CPU/RAM y marca de tiempo cada 15s.
- **Auditoría Forense:** Cada interacción se registra en `telegram_audit.log` con el snippet del contenido enviado.
- **Resiliencia:** Manejo automático de excepciones y cierre de mensaje con estado final (✅/❌).

## Mantenimiento
Para ajustar la estética de los iconos o el algoritmo de ETA, modificar directamente [`runtime/openclaw/openclaw_local/progress.py`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/_agents/runtime/openclaw/openclaw_local/progress.py).

_Última actualización: `2026-05-15`._
