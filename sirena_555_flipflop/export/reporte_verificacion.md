# Reporte de verificacion electrica

## 1. Version de KiCad detectada

- `kicad-cli`: 10.0.2
- Ruta: ` ruta local no pública  Files\KiCad\10.0\bin\kicad-cli.exe`

## 2. Comandos ejecutados

- ` ruta local no pública  Files\KiCad\10.0\bin\kicad-cli.exe sch erc  ruta local no pública  --output  ruta local no pública `
- ` ruta local no pública  Files\KiCad\10.0\bin\kicad-cli.exe sch erc  ruta local no pública  --format json --output  ruta local no pública `
- ` ruta local no pública  Files\KiCad\10.0\bin\kicad-cli.exe sch export netlist  ruta local no pública  --format kicadsexpr --output  ruta local no pública `
- ` ruta local no pública  Files\KiCad\10.0\bin\kicad-cli.exe sch export pdf  ruta local no pública  --output  ruta local no pública  --black-and-white`
- ` ruta local no pública  Files\KiCad\10.0\bin\kicad-cli.exe sch export svg  ruta local no pública  --output  ruta local no pública  --black-and-white`

## 3. Resultado de ERC

- Errores: 0
- Advertencias: 0

## 4. Verificacion de netlist

- Exportacion netlist KiCad S-expression ejecutada.
- Nets obligatorias buscadas: `+5V`, `GND`, `CLK`, `Q`, `/Q`, `TIMING_NODE`, `DIS_NODE`, `BASE_Q1`, `CTRL_NODE`.
- Netlist comparada contra matriz esperada: sin faltantes ni nodos extra.

## 4.1 Auditoria visual-estatica de wires

- Redes criticas conectadas por wires continuos.

## 5. Exportaciones

- PDF/SVG regenerados desde el esquematico actual.
- sirena_555_flipflop.pdf: 87617 bytes
- sirena_555_flipflop.svg: 550961 bytes
- Sin fallas de exportacion.

## 6. Estado tecnico

- `EXPORTADO_SIN_APROBACION_HUMANA`

## 7. Notas

- Circuito tecnicamente correcto por ERC/netlist, pendiente de validacion humana.

## 8. Advertencias justificadas

- Sin advertencias ERC.

## 9. Lecciones aprendidas

- La coordenada local `y` de simbolos KiCad debe invertirse al proyectarla a hoja.
- Los simbolos embebidos deben incluirse en `lib_symbols`; si no, ERC puede degradar pines a tipo desconocido.
- ERC limpio no sustituye la comparacion funcional de netlist: etiquetas distintas pueden aislar una etapa sin error critico.
- ERC limpio no garantiza un diagrama visual didactico: se requiere verificar continuidad grafica de wires para las redes criticas.
- No mezclar `lib_id` oficiales con cuerpos embebidos no oficiales; produce advertencias `lib_symbol_mismatch` y puede alterar la conectividad efectiva.
- Una libreria local de proyecto (`sym-lib-table` + `.kicad_sym`) elimina `lib_symbol_issues` sin sacrificar reproducibilidad.

## 10. Diagnostico del fallo anterior

- El generador anterior usaba `pin -> stub -> label` como sustituto de cableado visible.
- Varias conexiones principales existian en netlist por etiquetas, pero no como wires continuos legibles.
- Al intentar usar `lib_id` oficiales con geometria local se introdujeron advertencias de simbolo y nets falsas.

## 11. Correcciones aplicadas

- Registro local `Sirena` con `kicad/sym-lib-table` y `kicad/sirena.kicad_sym`.
- Ruteo ortogonal explicito para `CLK`, `Q`, `/Q`, `DIS_NODE`, `TIMING_NODE`, `BASE_Q1`, `CTRL_NODE`, `BUZZER_NEG`, `FAST_NODE`, `LED_RED_NODE` y `LED_BLUE_NODE`.
- Comparacion contractual de netlist KiCad S-expression contra matriz esperada.
- Gate visual-estatico para rechazar redes criticas resueltas solo por labels.

## 12. Serena / entorno agéntico

- `check_serena_access.py --json` reporto `serena-local` HTTP sano en `http://127.0.0.1:8765/mcp`.
- Esta conversacion no expone herramientas Serena nativas; el trabajo se ejecuto por filesystem y comandos locales.

_Última actualización: `2026-05-15`._
