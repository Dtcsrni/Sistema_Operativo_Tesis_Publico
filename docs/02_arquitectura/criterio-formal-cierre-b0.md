# Criterio Formal de Cierre B0

## Proposito
Definir la evidencia mínima para declarar que el cierre arquitectónico de `B0` es correcto, funcional, seguro, efectivo y eficiente sin confundir el cierre desktop-first con la validación de host real en Orange Pi.

## Checklists

### Arquitectura correcta
- Existe contrato máquina-legible para arquitectura, esquema, CLI y dependencias críticas.
- Las superficies `canon`, `proyecciones`, `auditoria_guardrails`, `publicacion` y `memoria_derivada` están declaradas y validadas.
- Los flujos prohibidos y acoplamientos prohibidos están documentados y verificados.

### Seguridad documental
- El threat model cubre canon no público, bundle publico, evidencia privada y superficies derivadas.
- `MEMORY.md`, `README.md`, wiki y publicación están tratados como derivados.
- La publicación sanitizada bloquea rutas privadas, hashes y validaciones humanas internas.

### Reproducibilidad y conformidad
- `build_all.py` ejecuta materialización, validación, sanitización y checks de operabilidad humana.
- Existen pruebas para contratos de arquitectura, estructura, sincronización y memoria derivada.
- `MEMORY.md` y la publicación pueden regenerarse sin edición manual.

### Eficiencia operativa
- `build_all.py` emite perfil JSON con tiempos por etapa.
- Se detectan etapas lentas contra presupuestos explícitos.
- El cuello de botella de `publish --build` queda visible en la traza operativa si reaparece.

## Gates de aceptación
- Gate desktop-first interno:
  - contratos y docs alineados;
  - pruebas locales y CI mínima en verde;
  - build y publicación sanitizada consistentes;
  - perfil de ejecución disponible.
- Gate host real externo:
  - `T-038` sigue siendo prerrequisito para cierre total de `T-050`;
  - no se considera cierre B0 completo mientras el Go/No Go Orange Pi permanezca pendiente.

## Estado actual esperado tras esta reformalización
- `T-039` a `T-049`: pueden cerrarse si la suite pasa y la documentación queda alineada.
- `T-050`: debe permanecer abierto o en progreso mientras `T-038` siga pendiente por host real.

_Última actualización: `2026-04-25`._
