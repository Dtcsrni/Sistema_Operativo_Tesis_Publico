# Resumen de investigación PET v2.2

## 1. Núcleo de decisión

La lectura integrada del estado del arte indica que el proyecto debe formularse como una investigación sobre **resiliencia, entrega útil de telemetría crítica y eficiencia energética en redes IoT urbanas intermitentes**, no como una simple integración tecnológica de LoRa y MQTT. [REF:7a09f3f84d92e67d99c9be3c5a378850b063b5ce39a4543549275e48cc4a3f33]

La formulación recomendada es:

> **Arquitectura IoT resiliente basada en LoRa P2P/mesh, MQTT y edge computing para telemetría priorizada en entornos urbanos intermitentes.**

Variante aplicada:

> **Arquitectura IoT resiliente para telemetría priorizada de transporte urbano mediante LoRa P2P/mesh, MQTT y edge computing en ciudades intermedias mexicanas.**

## 2. Problema científico principal

El problema de fondo es que las redes LoRa urbanas sufren zonas ciegas, variabilidad ambiental, eficiencia desigual de gateways y cobertura marginal costosa. CityWAN demuestra que incluso una red urbana amplia con 100 gateways y 19,821 nodos presenta cuellos de botella de cobertura, eficiencia y confiabilidad. [REF:162a03a763f17f6b29e143bc04ea36978dd0ed05ceec95e913bdd75cde7af382]

La literatura también reporta que, en redes LoRa densas, la contención e interferencia en bandas no licenciadas incrementan los mensajes descartados; aunque la configuración óptima de parámetros de radio puede mejorar confiabilidad y consumo energético, esto no resuelve por sí solo las zonas sombra ni la intermitencia urbana. [REF:5d84ac9054dc8bbb67294afac72dd0abca9e1d33368da7d3b9291d9de999b860]

## 3. Brecha del estado del arte

La brecha más defendible se concentra en la combinación de cuatro dimensiones:

1. **LoRa P2P/mesh** para extender cobertura y reducir dependencia de gateway único. [REF:89932f52836b06782a9ed3cda6aa1152e47537a1780acc6dc5550fa354c83ed9]
2. **Políticas de ruteo conscientes de energía, enlace y topología**. [REF:10394454cf7308af875990e175a2bb89f3a0507c17015ff977433b1b70d97382]
3. **MQTT/edge como integración y amortiguador de red**, no solo como broker. [REF:f94ce1edcf948b154387f83b8793a3cf78b49ad4d00f3ac15eb3928fa11301a3]
4. **Priorización semántica de telemetría crítica**, para entregar primero el dato de mayor valor operativo. [REF:499b69f18e703fa053ad8ce9bdc3c87198bd3b5e735ea9c716daefd99eba7d2b]

La literatura de LoRa mesh/multi-hop sigue considerando abiertos los problemas de conciencia energética, acceso concurrente, restricciones de duty cycle, protocolos de ruteo y seguridad. [REF:10394454cf7308af875990e175a2bb89f3a0507c17015ff977433b1b70d97382]

## 4. Hipótesis de trabajo

### Hipótesis general

Una arquitectura IoT basada en LoRa P2P/mesh, gateway edge, MQTT y priorización semántica mejora la entrega útil de datos críticos y la eficiencia energética frente a una arquitectura LoRa–MQTT convencional de un solo salto, bajo condiciones urbanas intermitentes. [REF:7a09f3f84d92e67d99c9be3c5a378850b063b5ce39a4543549275e48cc4a3f33]

### Hipótesis operacional H1

\[
WDR_C > WDR_A, WDR_B
\]

donde C es la propuesta, A es LoRa→Gateway→MQTT sin relay y B es LoRa P2P/store-and-forward sin priorización. La métrica WDR mide entrega ponderada por criticidad. [REF:2eb7bc70af7856cd81a43d2a38f4c0327d6f6c9badd9d9af562f4657ac5f3018]

### Hipótesis operacional H2

\[
\eta_C > \eta_A, \eta_B
\]

donde \(\eta\) mide mensajes críticos entregados por Wh consumido. [REF:1a8166617ab59fa3d9d8745ca0a50913a91680364c6184c28c581af53a23d5d5]

### Hipótesis operacional H3

\[
AoI_C < AoI_A, AoI_B
\]

para mensajes críticos, donde AoI es edad de la información.

## 5. Variables

| Tipo | Variable | Definición operacional |
|---|---|---|
| Independiente | Política de ruteo | Directo, store-and-forward, mesh priorizado |
| Independiente | Criticidad del mensaje | Peso \(C_m\) asignado a cada observación |
| Independiente | Estado energético | Voltaje, porcentaje de batería o Wh disponibles |
| Independiente | Calidad de enlace | RSSI, SNR, PDR estimado |
| Independiente | Número de saltos | Cantidad de relays desde nodo a gateway |
| Dependiente | WDR | Entrega ponderada por criticidad |
| Dependiente | PDR | Paquetes entregados / paquetes generados |
| Dependiente | Latencia | Tiempo generación–recepción |
| Dependiente | AoI | Frescura del dato en gateway/broker |
| Dependiente | Eficiencia energética | Mensajes críticos entregados / Wh |
| Dependiente | Cobertura efectiva | Nodos que logran comunicación útil |

## 6. Modelo de decisión propuesto

Se propone una función de decisión de ruta:

\[
Score_{ruta} = w_1PDR - w_2E_{tx} - w_3AoI - w_4H + w_5C_m
\]

donde \(PDR\) es razón de entrega estimada, \(E_{tx}\) energía de transmisión, \(AoI\) edad de información, \(H\) número de saltos y \(C_m\) criticidad del mensaje. [REF:5682e4f5d3920ad4875dc546ba263ba470cf92d7b768610fa353319fa85ca8e4]

Esta función permite evaluar rutas no solo por distancia o potencia, sino por valor operativo de la información.

## 7. Aporte metodológico

Se recomienda comparar tres líneas base:

| Línea base | Descripción |
|---|---|
| A | LoRa→Gateway→MQTT sin relay |
| B | LoRa P2P/store-and-forward sin priorización |
| C | Propuesta: LoRa P2P/mesh + priorización semántica + energía + edge buffer |

La evaluación debe producir métricas cuantitativas: PDR, WDR, latencia, AoI, consumo energético, cobertura efectiva y costo por nodo/gateway.

## 8. Localización recomendada

El proyecto puede ganar originalidad si se valida en Pachuca de Soto, Hidalgo, como ciudad intermedia mexicana con condiciones urbanas particulares. Los modelos de propagación LoRa no generalizan de forma perfecta entre entornos, y los modelos empíricos pueden perder exactitud fuera de su sitio de calibración. [REF:08b71f7c90aed6b6d2ffe77d2e799ce2bbb723dd8a27954ee0aebaddebfb845f]

## 9. Caso de uso recomendado

El caso de transporte urbano es pertinente porque la digitalización del transporte público en México requiere herramientas para información, pago, monitoreo, integración multimodal, operación, datos y servicio. [REF:b3d1dbea21b9446bc5edeb316729d84066a35c6cd51113e12ceacade370a5520]

La tesis no debe prometer resolver todo el transporte público; debe limitarse a **telemetría priorizada y continuidad de red para monitoreo experimental**.

## 10. Arquitectura recomendada

### Nodo K’anek A1 / nodo sensor LoRa

Basado en Heltec Wireless Stick Lite V3 o equivalente, viable por integrar ESP32-S3, SX1262, Wi-Fi, Bluetooth y LoRa, con bajo consumo profundo. [REF:85830a21d456511b9ee3a1353c2697514048f5546f276a01b3a2c12783f23021]

### Gateway LoRa/MQTT

Puede usarse un gateway Heltec HT-M7603 para LoRaWAN/MQTT privado y cobertura indoor o de relleno de zonas ciegas. [REF:c0d4b97d4f8e10f42a7d47e6ca7c4e2c4074ca022dcab6cc932ed000d4537223]

### Gateway edge / Tezkatli

Orange Pi 5 Plus puede operar como broker MQTT local, analizador, buffer, servidor edge, nodo de integración y plataforma de experimentación por su soporte Linux, Docker, red, interfaces y capacidades de cómputo. [REF:c0d4b97d4f8e10f42a7d47e6ca7c4e2c4074ca022dcab6cc932ed000d4537223]

## 11. Límites de alcance

No se recomienda convertir el trabajo en:

- tesis general de inteligencia artificial;
- tesis general de seguridad IoT;
- plataforma completa de movilidad inteligente;
- modelo integral de transporte público;
- protocolo LoRaWAN estándar completo;
- sistema OTA avanzado multi-nodo como contribución central.

Sí se recomienda mantener:

- inteligencia distribuida por niveles;
- reglas embebidas o TinyML solo si mejoran la decisión;
- seguridad ligera como requisito mínimo;
- medición experimental reproducible;
- comparación contra baselines.

## 12. Conclusión PET

El aporte científicamente más fuerte es demostrar que una arquitectura LoRa P2P/mesh–MQTT–edge con priorización semántica puede mejorar la entrega útil, la continuidad operativa y la eficiencia energética en escenarios urbanos intermitentes. La tesis debe medirse contra baselines y no limitarse a mostrar que “funciona”.

_Última actualización: `2026-06-03`._
