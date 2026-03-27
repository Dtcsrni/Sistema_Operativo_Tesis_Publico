# Reporte de Ingestión Canónica IoT

## 1. Resumen ejecutivo
- Paquete: `sistema_operativo_tesis_iot__descargable_unico_verificado__v10.zip`
- Versión de paquete detectada: `v10`
- Fecha de ingestión: `2026-03-26T22:45:56`
- Hash SHA-256 del paquete: `sha256:efa6ba4519703edf88507e6d4815e975d157fa5fca921c5c87f144ae9cb25329`
- Tamaño total del paquete (bytes): `204053`
- Cantidad de archivos en el ZIP: `15`
- Estado de Overleaf actual: **borrador provisional no canónico**.

## 2. Árbol de carpetas resultante
```text
00_sistema_tesis/
  01_contexto_canonico/
    sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md
    sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_maquina__v09.jsonl
    sistema_operativo_tesis_iot__registro_estructurado_del_contexto__v09.sqlite
  02_evidencia/
    sistema_operativo_tesis_iot__columna_vertebral_de_evidencia__v09.tsv
    sistema_operativo_tesis_iot__justificacion_de_inclusion_por_archivo__v09.tsv
  03_metadatos/
    sistema_operativo_tesis_iot__catalogo_general_de_artefactos__v09.json
    sistema_operativo_tesis_iot__convencion_de_nombres__v09.json
  04_politicas_y_gobernanza/
    sistema_operativo_tesis_iot__guia_de_ingestion__v09.md
    sistema_operativo_tesis_iot__politica_de_estatus_del_overleaf_actual__v09.md
    sistema_operativo_tesis_iot__politica_de_valor_documental__v09.md
  05_registros_de_ingestion/
    indice_maestro_ingestion_contexto_iot.csv
    reporte_ingestion_20260326_224556.md
  06_historico_de_paquetes/
```

## 3. Tabla de ingestión
| archivo | ruta_origen | ruta_destino | rol | prioridad | hash_sha256 | estado_verificacion |
| --- | --- | --- | --- | --- | --- | --- |
| sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md | 00_sistema_tesis/01_contexto_canonico/sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_humana__v09.md | Vista legible primaria del contexto canónico | P0 | sha256:bd051c019d1aea90df01a763868d521dc27e8a7ed2fb9e0816d25c5666050610 | verificado |
| sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_maquina__v09.jsonl | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_maquina__v09.jsonl | 00_sistema_tesis/01_contexto_canonico/sistema_operativo_tesis_iot__archivo_de_contexto_canonico__lectura_maquina__v09.jsonl | Vista máquina del contexto canónico | P0 | sha256:2aa6d79707d6a551845edac87afde09d78db3e46458d69a6658c7c9e0dc67c42 | verificado |
| sistema_operativo_tesis_iot__registro_estructurado_del_contexto__v09.sqlite | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__registro_estructurado_del_contexto__v09.sqlite | 00_sistema_tesis/01_contexto_canonico/sistema_operativo_tesis_iot__registro_estructurado_del_contexto__v09.sqlite | Base estructurada principal del contexto | P0 | sha256:46b3bae6a983cae0f6334eabc695a94a71b509c96facba8870382338b7560f25 | verificado |
| sistema_operativo_tesis_iot__catalogo_general_de_artefactos__v09.json | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__catalogo_general_de_artefactos__v09.json | 00_sistema_tesis/03_metadatos/sistema_operativo_tesis_iot__catalogo_general_de_artefactos__v09.json | Catálogo general de inventario | P1 | sha256:f8bb1c8aa58d4348e4e403d4731e4af89a85dcbd2eae2e804831e46099939de0 | verificado |
| sistema_operativo_tesis_iot__columna_vertebral_de_evidencia__v09.tsv | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__columna_vertebral_de_evidencia__v09.tsv | 00_sistema_tesis/02_evidencia/sistema_operativo_tesis_iot__columna_vertebral_de_evidencia__v09.tsv | Columna vertebral de evidencia para defensa | P1 | sha256:f561a19dff753e7b96a9f61fef46bafecdac947d8d4bc05c498c22d4f918170b | verificado |
| sistema_operativo_tesis_iot__convencion_de_nombres__v09.json | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__convencion_de_nombres__v09.json | 00_sistema_tesis/03_metadatos/sistema_operativo_tesis_iot__convencion_de_nombres__v09.json | Convención de nombres y normalización | P1 | sha256:1632f985de4f8bb0ccf03f6bac0d4361e3f9f371aba93ee1511e154038c02a7c | verificado |
| sistema_operativo_tesis_iot__guia_de_ingestion__v09.md | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__guia_de_ingestion__v09.md | 00_sistema_tesis/04_politicas_y_gobernanza/sistema_operativo_tesis_iot__guia_de_ingestion__v09.md | Guía operativa de ingestión | P1 | sha256:feb274cb0ce2deb29c7c685f1d4ffffab601953640865cd5cca380e829796d48 | verificado |
| sistema_operativo_tesis_iot__justificacion_de_inclusion_por_archivo__v09.tsv | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__justificacion_de_inclusion_por_archivo__v09.tsv | 00_sistema_tesis/02_evidencia/sistema_operativo_tesis_iot__justificacion_de_inclusion_por_archivo__v09.tsv | Justificación de inclusión por archivo | P1 | sha256:3ed39c40acc5401e28eafa8bc19ab9c9cb7d7ab19fccfdec52177d2a558f4581 | verificado |
| sistema_operativo_tesis_iot__politica_de_valor_documental__v09.md | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__politica_de_valor_documental__v09.md | 00_sistema_tesis/04_politicas_y_gobernanza/sistema_operativo_tesis_iot__politica_de_valor_documental__v09.md | Política de valor documental | P1 | sha256:a20ae8b3d36c377c8b44d0340575e7439d08e0a0e318a566aa2850752dc9c7fb | verificado |
| sistema_operativo_tesis_iot__politica_de_estatus_del_overleaf_actual__v09.md | V:\Sistema_Operativo_Tesis_Posgrado\00_sistema_tesis\evidencia_privada\staging_ingestion\20260326_224556\sistema_operativo_tesis_iot__descargable_unico_verificado__v10\sistema_operativo_tesis_iot__politica_de_estatus_del_overleaf_actual__v09.md | 00_sistema_tesis/04_politicas_y_gobernanza/sistema_operativo_tesis_iot__politica_de_estatus_del_overleaf_actual__v09.md | Política de estatus de Overleaf actual (borrador no canónico) | P1 | sha256:9e079a0aa3609b6bfb825fbf82534ba9b2830b495d3a7de8fe647057007dcea7 | verificado |

## 4. Hallazgos y riesgos
### Errores encontrados
- Ninguno.

### Advertencias
- Se detectaron archivos adicionales no contemplados en el plan: SHA256SUMS.txt, VERIFICACION_DEL_PAQUETE.md, sistema_operativo_tesis_iot__justificacion_de_inclusion_por_archivo__v09.jsonl, sistema_operativo_tesis_iot__mapa_de_nombres_anteriores_a_nombres_actuales__v09.tsv, sistema_operativo_tesis_iot__resumen_del_paquete__v09.json
- Consistencia registrada: contenedor ZIP v10 con artefactos internos v09 (advertencia no fatal).

### Decisiones tomadas
- Se respetaron nombres originales de artefactos (sin renombrado).
- Se realizó extracción en staging aislado antes de cualquier copia operativa.
- Se clasificó Overleaf actual como borrador provisional no canónico.
- ZIP fuente archivado en histórico: 00_sistema_tesis/06_historico_de_paquetes/2026-03-26_v10/sistema_operativo_tesis_iot__descargable_unico_verificado__v10.zip

## 5. Siguientes pasos priorizados
1. Crear branch/commit firmado del lote de ingestión y revisar diff semántico de cero cambios en contenido canónico.
2. Ejecutar validación cruzada entre `.md`, `.jsonl` y `.sqlite` para detectar divergencias internas de contexto.
3. Vincular el contexto canónico recién ingerido al flujo de redacción nueva del manuscrito desde cero.
4. Integrar referencias de evidencia experimental futuras contra `02_evidencia/` y el índice maestro.
5. Definir pipeline de sincronización futura con Overleaf, manteniendo estatus de borrador no canónico hasta nueva decisión formal.
