!!! danger "Validación Humana: AUSENTE"
    No se ha registrado firma de supervisión para este artefacto en `sign_offs.yaml`.

# Bloques

Bloques macro del sistema y sus criterios de salida.

- **Tesista:** `Erick Renato Vega Ceron`
- **Fecha:** `[fecha_hora_redactada]`
- **Estado:** `OK`
- **Fuentes:** `00_sistema_tesis/config/bloques.yaml`
- **Aviso:** Esta wiki es un artefacto generado. Edita las fuentes canónicas y vuelve a construir.

## Grafo de Dependencias

```mermaid
graph LR
  style B0 fill:#ff9,stroke:#333
  B0 --> B1
  B0 --> B2
  B1 --> B2
  B2 --> B3
  B2 --> B4
  B3 --> B4
  B2 --> B5
  B3 --> B5
  B4 --> B5
  B4 --> B6
  B5 --> B6
  B4 --> B7
  B6 --> B7
  B1 --> B8
  B2 --> B8
  B3 --> B8
  B4 --> B8
  B6 --> B8
  B7 --> B8
  B0 --> B9
  B7 --> B9
  B8 --> B9
  B8 --> B10
  B9 --> B10
```

## Bloques del sistema

|ID|Nombre|Estado|Prioridad|Dependencias|Criterio de salida|
|---|---|---|---|---|---|
|B0|Gobierno del sistema de tesis y base operativa|activo|critica|ninguna|Existe una base operativa funcional con validadores, dashboard generado, plantillas y README de retoma rápida.|
|B1|Delimitación del problema y contexto de Pachuca|no_iniciado|alta|B0|Existe una definición trazable del caso de estudio y de los supuestos urbanos/intermitentes que alimentan diseño y simulación.|
|B2|Diseño de arquitectura y formulación de hipótesis|no_iniciado|critica|B0, B1|La arquitectura objetivo, la línea base, los flujos críticos y las hipótesis quedan definidos con métricas y criterios de soporte.|
|B3|Modelo de control y métricas de desempeño|no_iniciado|alta|B2|Se cuenta con definición operacional de métricas, escenarios y umbrales de comparación para simulación y experimento.|
|B4|Simulación y escenarios de intermitencia|no_iniciado|critica|B2, B3|La simulación reproduce escenarios definidos, genera métricas comparables y deja trazabilidad de parámetros y semillas.|
|B5|Implementación de prototipo y canal de continuidad|no_iniciado|alta|B2, B3, B4|Existe un prototipo verificable con instrumentación suficiente para comparar comportamiento con la simulación.|
|B6|Validación experimental|no_iniciado|critica|B4, B5|Se cuenta con evidencia experimental trazable, repetible y suficiente para contrastar resultados simulados y soportar o rechazar hipótesis.|
|B7|Análisis integrado y discusión|no_iniciado|alta|B4, B6|Queda una narrativa coherente de soporte, límites y transferencia de resultados con trazabilidad a evidencias primarias.|
|B8|Redacción de tesis y ensamblaje documental|no_iniciado|alta|B1, B2, B3, B4, B6, B7|Existe un manuscrito completo, consistente y alineado con aportaciones, limitaciones y evidencia disponible.|
|B9|Reproducibilidad y versión sanitizada pública|no_iniciado|media|B0, B7, B8|Se cuenta con una ruta reproducible para publicar materiales sanitizados sin romper la canonicidad privada del repositorio.|
|B10|Cierre, defensa y transferencia|no_iniciado|media|B8, B9|La tesis, la defensa y los artefactos de cierre quedan completos, versionados y listos para consulta futura.|

