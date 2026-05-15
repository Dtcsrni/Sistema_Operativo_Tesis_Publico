# Verificacion manual

## Checklist de conectividad

- [x] U1 pin 8 a +5V
- [x] U1 pin 1 a GND
- [x] U1 pin 2 y pin 6 unidos en TIMING_NODE
- [x] U1 pin 3 conectado a CLK
- [x] U2 pin 3 conectado a CLK
- [x] U2 pin 2 conectado a /Q
- [x] U2 pin 5 produce Q
- [x] U2 pin 6 produce /Q
- [x] LED rojo conectado a /Q mediante R4
- [x] LED azul conectado a Q mediante R5
- [x] Buzzer manejado por transistor NPN
- [x] R7 pull-down en base del transistor
- [x] SW1-R3 en paralelo con R2

## Redes esperadas

| Red | Elementos esperados |
|---|---|
| +5V | U1 pin 4 y 8, U2 pins 1/4/10/13/14, R1.1, BZ1+, C3.1, C4.1, C5.1 |
| GND | U1 pin 1, U2 pin 7/11/12, C1.2, C2.2, C3.2, C4.2, C5.2, D1.K, D2.K, Q1.E, R7.2 |
| CLK | U1 pin 3, U2 pin 3 |
| DIS_NODE | U1 pin 7, R1.2, R2.1, SW1.1 |
| TIMING_NODE | U1 pin 2 y 6, R2.2, R3.2, C1.1 |
| /Q | U2 pin 2 y 6, R4.1 |
| Q | U2 pin 5, R5.1, R6.1 |
| BASE_Q1 | R6.2, Q1.B, R7.1 |
| CTRL_NODE | U1 pin 5, C2.1 |
| BUZZER_NEG | Q1.C, BZ1.2 |

## Observaciones

- El esquema fue regenerado con libreria local `Sirena` registrada en `kicad/sym-lib-table`.
- Las redes criticas usan wires continuos, no solo stubs con etiquetas.
- ERC KiCad CLI final: 0 errores, 0 advertencias.
- Netlist exportada comparada contra contrato esperado: sin faltantes.
- PDF y SVG exportados y no vacios.
- La leccion tecnica registrada es que ERC limpio no garantiza por si solo un diagrama visual correcto; por eso se agrego auditoria visual-estatica de wires.

## Resultado manual

EXPORTADO_SIN_APROBACION_HUMANA

_Última actualización: `2026-05-15`._
