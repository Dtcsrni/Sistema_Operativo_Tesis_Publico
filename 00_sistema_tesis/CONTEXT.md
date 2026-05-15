# CONTEXT.md — Glosario de Dominio del Sistema Operativo de Tesis

> Archivo de vocabulario canónico del proyecto para agentes de IA.
> Fuente de verdad para skills `grill-with-docs`, `improve-codebase-architecture`, `tdd`, `to-prd` y `zoom-out`.
> Actualizar inline cuando se resuelva un término durante una sesión de trabajo.

---

## Proyecto

### Sistema_Operativo_Tesis_Posgrado
Repositorio canónico rector de la tesis de Maestría en Internet de las Cosas. Contiene scripts, bitácora, contexto canónico, decisiones y toda infraestructura agéntica.

### Tesista Soberano
Erick Renato Vega Ceron. Única persona con autoridad para validar decisiones (VAL-STEP) y marcar tareas como completadas.

### Tesis
Investigación de maestría sobre arquitectura IoT urbana basada en LoRa híbrida P2P–MQTT para monitoreo de activos móviles en ciudades intermedias (referencia: Pachuca de Soto, Hidalgo).

---

## Dominio IoT / LoRa

### LoRa híbrida P2P-MQTT
Arquitectura de comunicaciones preferida del proyecto. Combina enlace directo punto-a-punto LoRa (sin infraestructura LoRaWAN) con reenvío al broker MQTT en el gateway. Línea más defendible para la tesis.

### Nodo Sensor
Dispositivo IoT de campo que recolecta datos (GPS, telemetría) y los transmite vía LoRa. Hardware referencia: Heltec WSL V3 con SX1262.

### Gateway / Relay
Nodo intermedio que recibe tramas LoRa y las reenvía al backend vía MQTT. Puede ser un Orange Pi 5 Plus o equivalente.

### PDR (Packet Delivery Ratio)
Variable dependiente principal. Razón entre paquetes recibidos correctamente y paquetes enviados totales. Métrica central de calidad de la red LoRa.

### Latencia extremo a extremo
Tiempo desde la generación del dato en el nodo hasta su ingesta en el backend. Variable dependiente secundaria.

### Autonomía energética
Tiempo de operación del nodo con batería. Condicionado por duty-cycle, potencia TX y capacidad LiPo.

### SF / BW / CR
Spreading Factor, Bandwidth y Coding Rate de LoRa. Variables independientes que afectan PDR, latencia y consumo. Su configuración es parte del diseño experimental.

### RSSI / SNR
Received Signal Strength Indicator / Signal-to-Noise Ratio. Métricas radio de calidad de enlace LoRa.

---

## Infraestructura Operativa

### OpenClaw
Capa de asistencia IA del proyecto (nombre en código). Incluye el sistema de agentes, skills, serena MCP, pipelines de benchmark y scripts en `07_scripts/`.

### Orange Pi 5 Plus
Hardware edge del proyecto. SBC con SoC Rockchip RK3588. Actúa como nodo de control para inferencia NPU y como gateway IoT en algunos escenarios.

### RK3588 / NPU
System-on-Chip de la Orange Pi 5 Plus. Cuenta con NPU (Neural Processing Unit) de 6 TOPS usada para inferencia de modelos LLM cuantizados (RKLLM).

### RKLLM
Framework de Rockchip para ejecutar modelos LLM en la NPU del RK3588. Requiere compilación de modelos en formato RKLLM con cuantización (W8A8, W4A16, etc.).

### PC (Nodo de Control)
Equipo de escritorio principal del Tesista. Usado para compilación RKLLM, benchmarks comparativos (GPU CUDA) y trabajo agéntico local.

### Motor Epistémico de Inferencia "Toltecayotl"
Núcleo GraphRAG y repositorio de sabiduría del proyecto (antes Atzin Scientific Engine).

### Cápsula de Conocimiento Trazable
Fragmento de información asimilada en Toltecayotl (chunk), validado por el tesista y firmado criptográficamente para evitar alucinaciones.

### Asimilador Documental de Datos
Herramienta de ingesta manual por CLI para extraer, firmar y cargar conocimiento al Motor Toltecayotl.

### Sincronización de Acervo Operativo
Mecanismo de replicación de Cápsulas desde la base maestra (PC) hacia el almacenamiento local del Edge (Orange Pi) para inferencia offline.

### Respaldo Bibliográfico
Exigencia operativa para que toda inferencia generada a partir de Toltecayotl incluya citas verificables en formato APA basadas en los metadatos de la Cápsula.

### Sistema de Telemetría Remota (DEC-0037)
### Integración con Jira (DEC-0042)
Extensión del CCM para la sincronización de tareas con issues externos de Jira. Permite la trazabilidad bidireccional entre la gobernanza agéntica interna y los sistemas corporativos de gestión de proyectos. Incluye soporte para vinculación de issues, visualización de estados en tiempo real y badges de sincronización.
Función básica obligatoria para supervisión de procesos largos (>30s) vía Telegram. Implementa el estándar "Total Awareness": latido de actividad (Typing/Spinner), métricas de carga (CPU/RAM/Disco), trazabilidad (VAL-STEP/PID) y log de auditoría. En la arquitectura actual, Telegram es un canal **Push-Only (Solo Monitoreo)**; la interacción bidireccional está desactivada.

---

## Gobernanza y Trazabilidad

### Ledger (Libro Mayor)
Registro inmutable de instrucciones humanas críticas, decisiones y validaciones. Ubicado en `00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md`. Cada entrada protegida por delimitadores `<<< >>>` y Hash SHA-256.

### Step ID / VAL-STEP
Identificador único de paso de validación humana (ej. validación humana interna no pública). Requerido para cerrar cualquier tarea principal o decisión técnica sustantiva. Solo el Tesista asigna Step IDs.

### DEC-XXXX
Decisión técnica del proyecto. Equivale a un ADR (Architecture Decision Record). Almacenadas en `00_sistema_tesis/decisiones/`. Formato: `YYYY-MM-DD_DEC-XXXX_<slug>.md`.

### Matriz de Trazabilidad
Documento que registra la correspondencia entre instrucciones, decisiones, evidencias y Step IDs. En `00_sistema_tesis/bitacora/matriz_trazabilidad.md`.

### LID / GOV / AUD
Referencias globales de trazabilidad usadas en documentos de autoauditoría:
- `[LID]` → Ledger ID / entrada en el Libro Mayor
- `[GOV]` → referencia de gobernanza (DEC-XXXX)
- `[AUD]` → referencia de auditoría interna

### build_all.py
Script principal de auditoría del sistema. Valida integridad estructural del repositorio. Debe ejecutarse antes de proponer cambios a infraestructura o publicación.

---

## Agentes y Skills

### Serena MCP
Capa de contexto compacto y gobernanza para agentes. Servidor local Python en `07_scripts/serena_mcp.py`. Expuesto por HTTP en `http://127.0.0.1:8765/mcp` (perfil `serena-local`). Modo primario para agentes en VS Code.

### Caveman
Modo de comunicación ultra-compacto (~75% menos tokens). Activado con "caveman mode". Ver skill `caveman`.

### Pipeline de Benchmark
Conjunto de scripts (`run_edge_npu_benchmark.py`, `run_pc_benchmark.py`) que ejecutan inferencia comparativa entre Edge NPU (Orange Pi) y PC (CUDA) y producen reportes JSON certificados.

### Fase Reflexiva
Capacidad del sistema OpenClaw para autoanalizar su propio output antes de entregarlo. Implementada en el pipeline de inferencia RKLLM.

### Routing Adaptativo
Mecanismo de selección dinámica de backend de inferencia (NPU vs CPU vs GPU) según disponibilidad y presupuesto de tokens.

---

## Contexto Canonical

### 01_contexto_canonico
Directorio con el contexto estructurado v09 del proyecto (`.md`, `.jsonl`, `.sqlite`). Fuente de verdad del dominio IoT de la tesis.

### pendientes/
Directorio de issues locales del sistema de triage (`00_sistema_tesis/pendientes/`). Gestionado por el skill `triage`.

_Última actualización: `2026-05-15`._
