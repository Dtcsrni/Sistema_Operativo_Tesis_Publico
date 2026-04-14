# Arquitectura Objetivo B0 Desktop-First

## Objetivo
Cerrar B0 a nivel de arquitectura, contratos y pruebas desde escritorio, dejando a Orange Pi como gate operativo externo.

## Resultado esperado
- Separacion de dominios congelada en manifests y documentacion.
- Arquitectura interna del sistema de tesis formalizada.
- Suite de conformidad ejecutable en local y CI.
- Politicas de backup, observabilidad y publicacion coherentes entre si.

## Gates externos
- Validacion real de aislamiento de runtime y red en Orange Pi.
- Restore por dominio ejecutado en host real.
- Benchmark fisico de `edge_iot`.
- Checklist final Go/No-Go de Orange Pi.

## Regla de cierre
- `ENT-014` y `ENT-015` pueden cerrarse desde escritorio si la conformidad local pasa.
- `ENT-013` solo puede quedar listo para validacion mientras los gates externos permanezcan pendientes.
- `T-050` se interpreta como cierre arquitectonico B0 desde escritorio, no como certificacion fisica del edge.

_Última actualización: `2026-04-14`._
