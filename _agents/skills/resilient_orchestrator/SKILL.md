# Skill: Resilient Orchestrator (ARO)

<!-- SISTEMA_TESIS:PROTEGIDO -->

## Propósito
Esta skill define el protocolo de autonomía para la ejecución de pipelines de larga duración en el Sistema Operativo de Tesis. Permite que el sistema se auto-diagnostique ante fallos de hardware o incompatibilidad de software y ejecute estrategias de mitigación automáticas.

## Cuándo usar
- Ejecución de pipelines de compilación de modelos (RKLLM, RKNN).
- Sincronización de grandes volúmenes de datos entre PC y Edge.
- Situaciones donde los límites de RAM (WSL) o Red pueden causar interrupciones.

## Protocolo de Resiliencia (ARO)

### 1. Diagnóstico Obligatorio
Antes de reportar un fallo al tesista, el orquestador DEBE:
- Ejecutar `FaultAnalyzer.check_oom()` para verificar si el kernel mató el proceso.
- Escanear la salida de error en busca de `GGMLQuantizationType` incompatibles o `MemoryError`.

### 2. Matriz de Autocorrección
El sistema tiene autorización para:
- **Pivotar Cuantización:** Si FP16 falla por RAM -> Descargar GGUF Q4_0 y convertir.
- **Sanitización de Emergencia:** Si el diagnóstico indica RAM crítica -> Ejecutar `clean_node.py --force`.
- **Reanudación por Checkpoint:** Consultar siempre `pipeline_state.json` para no repetir fases exitosas.

### 3. Telemetría de Autocorrección
- Usar el ícono `🩹` (Band-aid) en Telegram para notificar que el sistema detectó un error y está aplicando una cura automática.
- Reportar métricas absolutas (GB) para demostrar la efectividad de la nueva estrategia.

## Ejemplo de uso en script
```python
from 07_scripts.ops.fault_analyzer import FaultAnalyzer
# ... lógica de bucle de reintento con cambio de estrategia ...
```

## Referencias
- `DEC-0037`: Política de Total Awareness.
- `INC-0025`: Análisis del límite de RAM en runtime local (histórico: WSL → actual: contenedores Docker).

_Última actualización: `2026-05-15`._
