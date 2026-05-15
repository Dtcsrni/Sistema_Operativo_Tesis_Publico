# sirena_555_flipflop

Proyecto KiCad para una práctica didáctica de Diseño Digital: una sirena visual/auditiva sencilla basada en un NE555 astable como reloj, un 74HC74 configurado como divisor por 2 con `D = /Q`, dos LEDs alternados y un buzzer activo con transistor NPN.

El repositorio se usa aqui como prueba del sistema de generacion precisa de diagramas electricos, simulacion y validacion electrica.

## Diagrama funcional

```text
NE555 astable -> CLK -> 74HC74 (D = /Q) -> Q y /Q
                       |                     |
                       |                     +-> LED azul
                       +-> LED rojo          +-> buzzer activo via Q1
```

## Funcionamiento esperado

- El NE555 genera un reloj lento en `CLK`.
- `CLK` entra al primer flip-flop del 74HC74.
- La entrada `D` se realimenta desde `/Q`.
- `Q` y `/Q` alternan en cada flanco de reloj.
- `Q` activa el buzzer por medio de `Q1`.
- `/Q` enciende el LED rojo.
- `Q` enciende el LED azul.

## Ecuaciones del 555

Modo normal:

```text
RA = 10 kΩ
RB = 100 kΩ
C  = 10 µF

f ≈ 1.44 / ((RA + 2RB) C)
  ≈ 1.44 / ((10k + 2·100k) · 10µF)
  ≈ 0.686 Hz
```

Modo rápido con `SW1`:

```text
RB_eq = (100k · 47k) / (100k + 47k) ≈ 31.97 kΩ

f_rapida ≈ 1.44 / ((10k + 2·31.97k) · 10µF)
         ≈ 1.95 Hz
```

## Tabla de funcionamiento

| Q | /Q | LED_AZUL | LED_ROJO | BUZZER |
|---|---|---|---|---|
| 0 | 1 | OFF | ON | OFF |
| 1 | 0 | ON | OFF | ON |

## Archivos generados

- `README.md`
- `circuito.yaml`
- `netlist_pedagogica.csv`
- `BOM.csv`
- `verificacion_manual.md`
- `kicad/sirena_555_flipflop.kicad_pro`
- `kicad/sirena_555_flipflop.kicad_sch`
- `kicad/sirena.kicad_sym`
- `kicad/sym-lib-table`
- `export/reporte_erc.txt`
- `export/reporte_erc.json`
- `export/sirena_555_flipflop.net`
- `export/reporte_verificacion.md`
- `export/sirena_555_flipflop.pdf`
- `export/sirena_555_flipflop.svg`

## Instrucciones en KiCad

1. Abrir `kicad/sirena_555_flipflop.kicad_pro`.
2. Abrir `kicad/sirena_555_flipflop.kicad_sch`.
3. Ejecutar `Inspect -> Electrical Rules Checker`.
4. Exportar PDF y SVG desde `File -> Export`.

## Comandos de KiCad CLI

```powershell
kicad-cli --version
kicad-cli sch erc kicad/sirena_555_flipflop.kicad_sch --output export/reporte_erc.txt
kicad-cli sch export pdf kicad/sirena_555_flipflop.kicad_sch --output export/sirena_555_flipflop.pdf --black-and-white
kicad-cli sch export svg kicad/sirena_555_flipflop.kicad_sch --output export/ --black-and-white
```

## Notas didacticas

- `D = /Q` convierte al 74HC74 en un divisor por 2.
- `SW1` agrega `R3 = 47 kΩ` en paralelo con `R2` y acelera el reloj.
- El buzzer activo no se conecta directo al flip-flop; se conmuta por `Q1`.
- Los LEDs siempre tienen resistencia serie.

## Lecciones aprendidas para KiCad 10

- ERC limpio no garantiza que el diagrama sea didacticamente correcto; se agrego auditoria visual-estatica para comprobar wires continuos en redes criticas.
- No mezclar `lib_id` oficiales con geometria embebida no oficial: KiCad puede comparar contra la libreria oficial y producir netlists falsas o advertencias `lib_symbol_mismatch`.
- Los simbolos locales deben registrarse con una libreria de proyecto (`kicad/sym-lib-table` + `kicad/sirena.kicad_sym`) para evitar `lib_symbol_issues`.
- Las rutas visibles deben evitar pasar por pines o etiquetas de otras redes; el fallo anterior corto `DIS_NODE` con `+5V` al cruzar el pin izquierdo de R1.
- Serena HTTP (`serena-local`) esta sano segun `check_serena_access.py`, pero esta conversacion no expone herramientas Serena nativas; se trabajo por filesystem y se registro el bloqueo de runtime.

## Estado actual

Estado tecnico: `EXPORTADO_SIN_APROBACION_HUMANA`.

- ERC KiCad CLI: 0 errores, 0 advertencias.
- Netlist KiCad S-expression: comparada contra contrato esperado sin faltantes.
- Wires criticos visibles: `CLK`, `Q`, `/Q`, `DIS_NODE`, `TIMING_NODE`, `BASE_Q1`, `CTRL_NODE`, `BUZZER_NEG`, `FAST_NODE`, `LED_RED_NODE`, `LED_BLUE_NODE`.
- PDF/SVG exportados y no vacios.
- No se marca aprobacion humana autonoma.

_Última actualización: `2026-05-15`._
