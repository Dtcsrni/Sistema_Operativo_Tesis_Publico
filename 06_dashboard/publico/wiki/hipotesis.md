# Hipótesis

Hipótesis activas, criterios de soporte, evidencia y relación con bloques.

- **Tesista:** `Erick Renato Vega Ceron`
- **Fecha:** `[fecha_hora_redactada]`
- **Estado:** `OK`
- **Fuentes:** `00_sistema_tesis/config/hipotesis.yaml`, `00_sistema_tesis/config/bloques.yaml`
- **Aviso:** Esta wiki es un artefacto generado. Edita las fuentes canónicas y vuelve a construir.

## Navegación de esta página

- [Volver al índice](index.md).
- Página anterior en la ruta base: [Planeación](planeacion.md).
- Página siguiente en la ruta base: [Bloques](bloques.md).
- Relacionada: [Planeación](planeacion.md).
- Relacionada: [Bloques](bloques.md).
- Relacionada: [Experimentos](experimentos.md).

## Origen canónico y artefactos relacionados

### Cómo rastrear esta página hasta su origen canónico

1. Esta página derivada: [`06_dashboard/wiki/hipotesis.md`](hipotesis.md).
2. Revisa la lista de fuentes canónicas que alimentan su contenido.
3. Si necesitas la versión visual derivada, consulta el HTML hermano generado.
4. Si necesitas divulgación o evaluación externa, consulta el artefacto público sanitizado equivalente.
5. Si necesitas cambiar el contenido, edita la fuente canónica y reconstruye; no edites esta salida a mano.

### Fuentes canónicas declaradas

|Fuente canónica|Tipo|Existe|
|---|---|---|
|[`00_sistema_tesis/config/hipotesis.yaml`](../NOTA_SEGURIDAD_Y_ACCESO.md)|archivo|sí|
|[`00_sistema_tesis/config/bloques.yaml`](../NOTA_SEGURIDAD_Y_ACCESO.md)|archivo|sí|

### Artefactos derivados relacionados

- Markdown interno: [`06_dashboard/wiki/hipotesis.md`](hipotesis.md)
- HTML interno: [`06_dashboard/generado/wiki/hipotesis.html`](../wiki_html/hipotesis.html)
- Markdown público sanitizado: [`06_dashboard/publico/wiki/hipotesis.md`](hipotesis.md)
- HTML público sanitizado: [`06_dashboard/publico/wiki_html/hipotesis.html`](../wiki_html/hipotesis.html)

## Qué resuelve este subsistema

- Convierte el objetivo general de la tesis en afirmaciones contrastables.
- Vincula cada hipótesis con bloques de trabajo, criterios de soporte y futura evidencia.
- Evita que la narrativa técnica crezca sin criterios explícitos de validación o rechazo.

## Lectura rápida

- Hipótesis activas: `7`
- Hipótesis de prioridad crítica: `2`
- Esta página describe hipótesis vigentes, no resultados ya confirmados.

## Mapa de Hipótesis

```mermaid
graph TD
  HG --> B2
  HG --> B3
  style HG fill:#f9f,stroke:#333,stroke-width:2px
  H1 --> B2
  H1 --> B4
  style H1 fill:#f9f,stroke:#333,stroke-width:2px
  H2 --> B2
  H2 --> B4
  style H2 fill:#f9f,stroke:#333,stroke-width:2px
  H3 --> B2
  H3 --> B3
  style H3 fill:#f9f,stroke:#333,stroke-width:2px
  H4 --> B3
  H4 --> B4
  style H4 fill:#f9f,stroke:#333,stroke-width:2px
  H5 --> B4
  H5 --> B5
  style H5 fill:#f9f,stroke:#333,stroke-width:2px
  H6 --> B1
  H6 --> B2
  style H6 fill:#f9f,stroke:#333,stroke-width:2px
```

## Hipótesis activas

|ID|Nombre|Prioridad|Estado|Bloques|Criterio de soporte|
|---|---|---|---|---|---|
|HG|Superioridad integrada de arquitectura resiliente|critica|activa|B2, B3, B4, B5, B6, B7|Se considera soportada si la arquitectura propuesta supera consistentemente a la línea base en continuidad útil y control bajo escenarios intermitentes definidos, sin costos operativos desproporcionados.|
|H1|Buffer adaptativo reduce pérdida útil|alta|activa|B2, B4, B5, B6|Soportada si mejora la entrega útil y mantiene la edad de información dentro de umbrales definidos para variables críticas.|
|H2|Topología híbrida mejora resiliencia|alta|activa|B2, B4, B5, B6, B7|Soportada si la topología híbrida conserva más funciones esenciales y recupera antes que la línea base centralizada.|
|H3|Priorización contextual protege variables críticas|critica|activa|B2, B3, B4, B5, B6|Soportada si reduce latencia y pérdida de variables críticas bajo carga/intermitencia con impacto aceptable en tráfico secundario.|
|H4|Control degradable mantiene estabilidad útil|alta|activa|B3, B4, B5, B6, B7|Soportada si el modo degradado mantiene variables dentro de una banda operativa segura más tiempo que la línea base.|
|H5|Transferencia simulación a experimento es consistente|alta|activa|B4, B5, B6, B7|Soportada si las tendencias principales se conservan y la desviación entre simulación y experimento permanece dentro del margen acordado.|
|H6|Perfil urbano de Pachuca aporta valor de diseño|media|activa|B1, B2, B4, B6, B7|Soportada si el contexto local modifica de manera explícita y trazable parámetros, escenarios o decisiones respecto de una formulación genérica.|

