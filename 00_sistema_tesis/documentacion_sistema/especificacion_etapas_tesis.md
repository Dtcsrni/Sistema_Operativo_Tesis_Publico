# Especificaciones y Criterios de Aceptación por Etapa (B0 a B10)

Este documento define de forma canónica y cuantitativa las especificaciones de diseño, criterios de aceptación, variables e hipótesis del proyecto de Tesis de Maestría.

---

## B0: Gobierno y Base Operativa

### Objetivo
Establecer la infraestructura de control, aislamiento de procesos, hardening de seguridad y trazabilidad inmutable del sistema (PC Hub y Orange Pi Edge).

### Criterios de Aceptación
1. **Aislamiento de Dominios:** Conformidad absoluta con `manifests/domain_runtime_isolation.yaml`.
2. **Hardening de Servicios:** La unidad Systemd de Edge (`siot-edge.service`) debe correr bajo el usuario `edge_ops` y grupo `docker`, con `NoNewPrivileges=yes` y `PrivateTmp=yes`.
3. **Trazabilidad Inmutable:** Cada cambio técnico o decisión sustantiva debe contar con un validación humana interna no pública y estar registrado con su hash SHA-256 en el Ledger (`log_sesiones_trabajo_registradas.md`).

---

## B1: Contextualización del Entorno Urbano (Pachuca de Soto)

### Objetivo
Modelar la intermitencia urbana de Pachuca de Soto, Hidalgo, caracterizando la topografía, perfiles de elevación y zonas de sombra de radiofrecuencia para activos móviles.

### Criterios de Aceptación
1. **Zonas de Estudio:** Delimitación física de al menos 3 rutas urbanas con topografía irregular en Pachuca de Soto (centro histórico, zona plateada, y lomas de Pachuca).
2. **Modelado de Intermitencia:** Definición matemática de intervalos de desconexión y perfiles de atenuación urbana.
3. **Canal de Propagación:** Caracterización de pérdidas en trayecto urbano a 915 MHz.

---

## B2: Diseño y Formulación de Hipótesis

### Objetivo
Definir de forma explícita las variables independientes y dependientes del sistema de comunicación LoRa híbrido P2P-MQTT, y establecer las hipótesis formales a validar.

### Variables del Sistema
*   **Variables Independientes (Controlables):**
    *   *Spreading Factor (SF):* Rango de 7 a 12.
    *   *Bandwidth (BW):* 125 kHz, 250 kHz, 500 kHz.
    *   *Coding Rate (CR):* 4/5, 4/6, 4/7, 4/8.
    *   *Intervalo de Transmisión (Duty Cycle):* 10s, 30s, 60s.
*   **Variables Dependientes (Observables):**
    *   *Packet Delivery Ratio (PDR):* Razón entre paquetes recibidos y transmitidos.
    *   *Latencia Extremo a Extremo (ms):* Tiempo total de tránsito del sensor al backend.
    *   *Consumo de Corriente (mA):* Perfil de consumo energético del nodo móvil.

### Hipótesis Formales
*   **H1:** Un incremento del SF de 7 a 10 mejora el PDR en al menos un 15% en zonas con sombra de radiofrecuencia (NLOS) en Pachuca.
*   **H2:** El uso de un BW de 250 kHz en lugar de 125 kHz reduce la latencia en al menos un 40% a costa de una pérdida menor al 5% en PDR bajo condiciones de línea de vista (LOS).
*   **H3:** Un Coding Rate de 4/8 mitiga pérdidas de tramas causadas por interferencia electromagnética urbana, manteniendo el PDR arriba del 85% en trayectos congestionados.
*   **H4:** La combinación adaptativa de parámetros (SF/BW) dependiente del RSSI dinámico reduce el consumo de batería del nodo sensor móvil en al menos un 25% comparado con configuraciones estáticas máximas (SF12/BW125kHz).
*   **H5:** El middleware MQTT implementado en la Orange Pi resuelve la intermitencia local mediante buffers de almacenamiento, garantizando un PDR de datos persistidos del 100% tras la restauración de conectividad a internet.
*   **H6:** La latencia extremo a extremo media se mantiene por debajo de 500 ms en redes LoRa P2P directas en distancias urbanas menores a 3 km.

---

## B3: Simulación de Red LoRa en Pachuca

### Objetivo
Evaluar teóricamente la viabilidad de cobertura y PDR esperado en las rutas delimitadas en Pachuca mediante herramientas de simulación de RF (ej. NS-3 o Matlab).

### Criterios de Aceptación
1. **Modelo de Propagación:** Inclusión de pérdidas por terreno de Pachuca (modelo Okumura-Hata adaptado).
2. **Escenarios Simulado:** Al menos 100 simulaciones variando SF, BW y CR.
3. **Métrica Esperada:** Curvas teóricas de PDR vs Distancia.

---

## B4: Diseño de Hardware y Prototipado

### Objetivo
Construir los nodos físicos de experimentación basados en hardware de referencia del proyecto.

### Criterios de Aceptación
1. **Nodo Sensor Móvil:** Heltec WSL V3 con módulo transceptor SX1262 y receptor GPS integrado, con batería LiPo de 1200 mAh.
2. **Nodo Gateway:** Orange Pi 5 Plus con módulo transceptor LoRa USB o SPI dedicado, configurado en dominio aislado `edge_iot`.
3. **Acreditación Física:** Reporte de inspección visual de LEDs de estado e instrumentación con multímetro de precisión para perfiles de consumo basal.

---

## B5: Desarrollo de Firmware y Middleware

### Objetivo
Escribir el código embebido adaptativo del nodo sensor y el software de orquestación y reenvío MQTT del gateway.

### Criterios de Aceptación
1. **Algoritmo Adaptativo LoRa:** Ajuste dinámico de SF en base a RSSI y SNR recibidos.
2. **Buffer Local en Gateway:** Persistencia en SQLite local ante caídas de conexión WAN.
3. **Middleware MQTT:** Publicación confiable en broker MQTT del PC Hub bajo formato JSON con hash de verificación.

---

## B6: Pruebas Controladas de Laboratorio

### Objetivo
Validar la resiliencia, atenuación y consumo del prototipo físico en un entorno electromagnético controlado (cámara anecoica o atenuadores variables coaxiales).

### Criterios de Aceptación
1. **Curva de Sensibilidad:** Medición del nivel de recepción mínimo (RSSI) para SF7 a SF12.
2. **Perfil de Consumo:** Registro de consumo en modo sleep, transmisión radio y búsqueda GPS.
3. **Test de Stress de Buffer:** Simulación de 24 horas de desconexión WAN en el gateway.

---

## B7: Pruebas de Campo de Activos Móviles

### Objetivo
Realizar campañas de medición en las rutas urbanas reales de Pachuca de Soto usando vehículos terrestres.

### Criterios de Aceptación
1. **Muestras Recolectadas:** Mínimo 1,000 tramas transmitidas por configuración experimental.
2. **Trazabilidad GPS:** Coordenadas espaciales asociadas a cada trama LoRa recibida en el gateway.
3. **Evidencia Cruda:** Archivos JSONL con firma de integridad local guardados en `/mnt/emmc/datasets/`.

---

## B8: Ingesta y Consolidación de Datos

### Objetivo
Procesar las tramas crudas, sanitizar anomalías y cargar el corpus de datos al motor de inferencia local "Toltecayotl".

### Criterios de Aceptación
1. **Validación de Hashes:** 100% de registros deben mantener integridad criptográfica desde el nodo origen.
2. **Catalogación:** Datos indexados por SF, BW, CR, RSSI, SNR, PDR, latencia y ubicación.
3. **Conformidad FAIR:** Datos organizados bajo principios de reusabilidad científica.

---

## B9: Análisis Estadístico y Validación de Hipótesis

### Objetivo
Realizar análisis multivariado para rechazar o aceptar las hipótesis H1 a H6 formuladas en B2.

### Criterios de Aceptación
1. **Modelos Estadísticos:** Regresiones logísticas para PDR y ANOVA para consumo y latencia.
2. **Nivel de Significancia:** $p < 0.05$ como umbral de decisión estadística.
3. **Evidencia Generada:** Reportes estadísticos exportados en formato JSON a `00_sistema_tesis/02_evidencia/`.

---

## B10: Escritura del Manuscrito LaTeX

### Objetivo
Integrar la especificación, metodología, simulaciones, resultados experimentales y conclusiones en el documento principal LaTeX compilable.

### Criterios de Aceptación
1. **Estructura Académica:** Capítulos de Introducción, Estado del Arte, Metodología, Resultados y Conclusión.
2. **Compilabilidad Estricta:** El compilador de LaTeX debe generar el PDF sin errores de sintaxis o referencias rotas.
3. **Veracidad de Citas:** 100% de citas vinculadas a DOIs reales y literatura indexada, verificados por el orquestador agéntico.

_Última actualización: `2026-06-03`._
