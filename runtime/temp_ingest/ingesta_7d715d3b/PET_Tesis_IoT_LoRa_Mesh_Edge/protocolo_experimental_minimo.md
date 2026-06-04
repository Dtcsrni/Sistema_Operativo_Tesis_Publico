# Protocolo experimental mínimo

## Objetivo experimental

Comparar una arquitectura LoRa–MQTT convencional contra una arquitectura LoRa P2P/mesh–MQTT–edge con priorización semántica y ruteo consciente de energía.

## Baselines

- A: LoRa directo a gateway + MQTT sin relay.
- B: LoRa P2P/store-and-forward sin priorización.
- C: Propuesta: LoRa P2P/mesh + edge buffer + priorización semántica + decisión energética.

## Métricas

- Packet Delivery Ratio (PDR)
- Weighted Delivery Ratio (WDR)
- Latencia extremo a extremo
- Age of Information (AoI)
- Consumo energético por mensaje
- Mensajes críticos entregados por Wh
- Cobertura efectiva
- Costo aproximado por nodo y por gateway

## Diseño de pruebas

1. Prueba de laboratorio: control de distancia corta, interferencia baja, batería estable.
2. Prueba de obstáculo: paredes, esquina, vehículo o estructura urbana.
3. Prueba de movilidad baja: nodo desplazándose lentamente o ruta corta.
4. Prueba de backhaul intermitente: gateway edge sin internet temporal.
5. Prueba de congestión: aumento de tasa de mensajes no críticos.

## Registro mínimo por paquete

- timestamp_origen
- timestamp_gateway
- node_id
- message_id
- criticality
- payload_type
- RSSI
- SNR
- battery_voltage
- hop_count
- route_id
- delivered
- retransmissions
- energy_estimate_mJ

## Criterio de éxito

La propuesta C debe superar a A y B en WDR y eficiencia energética útil sin degradar de forma inaceptable la latencia de mensajes críticos.

_Última actualización: `2026-06-03`._
