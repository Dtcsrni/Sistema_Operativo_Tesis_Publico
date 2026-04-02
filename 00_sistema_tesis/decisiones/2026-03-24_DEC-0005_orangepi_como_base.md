<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0005_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0005: Orange Pi 5 Plus como base experimental y operativa

- **Fecha:** 2026-03-24
- **Estado:** aceptado
- **Autor(es):** Tesista / Sistema Operativo de Tesis

## Contexto

El Bloque 0 ha establecido el sistema documental y de gobernanza metodológica en MSYS2/Windows. Sin embargo, los siguientes bloques exigen simulación de red, validación experimental, ejecución de contenedores, y scripts de analítica perimetral. 
El hardware subyacente requiere capacidades de procesamiento intensivo, despliegue eficiente en red local o perimetral, y compatibilidad total con ecosistemas de compilación de datos nativos sin las restricciones de compatibilidad o abstracción que impone Windows u otras arquitecturas monolíticas x86.

## Decisión

Se ha designado a la **Orange Pi 5 Plus (Linux ARM64)** como la **placa base y nodo experimental primario** para todo el ciclo de vida del "Sistema Operativo de Tesis". 

Para facilitar este paso, se ha creado el script `07_scripts/setup_orangepi.sh`, el cual automatiza al 100% la reconstrucción del entorno operativo, instalando dependencias de bajo nivel, entornos virtuales, ganchos de pre-commit y DVC de manera nativa sobre distribuciones Linux basadas en APT (Ubuntu/Debian/Armbian).

## Alternativas consideradas

- Desplegar puramente en máquinas virtuales en la nube (AWS/GCP): Se descartó por costos recurrentes y lejanía física/latencia al momento de integrar la validación experimental de borde (IoT).
- Usar computadoras monolíticas o laptops: Se descartó por el riesgo de "funciona en mi máquina" y dificultad de desplegar hardware pesado en escenarios urbanos a futuro.
## Criterio de elección

Retroactivo: Decisión tomada durante la fase de infraestructura inicial.

## Métricas de Éxito

- [x] Validación operativa de la infraestructura.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Consistencia en auditorías automáticas.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] Firma digital GPG del tesista.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Validación de integridad estructural.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

  - **Soporte:** [Retroactivo | Step ID]
  - **Modo:** [Retroactivo | Confirmación Verbal]
  - **Fecha de Validación:** 2026-03-24
  - **Integridad:** `[hash_redactado]` 
  - **Fingerprint:** `[hash_redactado]` 
  - **Nivel de Auditoría:** Bajo
## Consecuencias

- **Positivas:** 
  - La infraestructura ahora cuenta con un conducto directo de despliegue `one-click` para arquitecturas ARM64.
  - Elimina problemas de fricción con compiladores de tipo C++ o Rust (como los experimentados previamente con DVC en MSYS2).
  - Promueve la reproducibilidad del experimento base en hardware escalable y accesible de tipo Single Board Computer (SBC).
- **Negativas/Riesgos:** 
  - Se debe asegurar de que las pruebas automatizadas y los scripts de generación (como `build_all.py`) se mantengan agnósticos al sistema operativo (utilizando módulos de sistema cruzado como `pathlib`). Esto ya se consideró en el código actual.

## Trazabilidad de IA

- **Proveedor:** Google (DeepMind)
- **Modelo/Versión:** Gemini 1.5 Pro / Advanced Agentic Coding v1.0
- **Agente/Rol:** Antigravity (Assistant)
- **Nivel de Razonamiento:** alto
- **Prompts/Contexto clave:** Normalización de repositorio.

## Impacto en Presupuesto de Razonamiento

- **Consumo:** Bajo (Retroactivo)
- **Justificación:** Normalización de formato de trazabilidad.

## Implementación o seguimiento

- [x] Implementación completada en Fase B0.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

N/A

[LID]: [ruta_local_redactada]
[GOV]: [ruta_local_redactada]
[AUD]: [ruta_local_redactada]
