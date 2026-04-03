<!-- SISTEMA_TESIS:PROTEGIDO -->

# DEC-0021 Publicacion desde Downstream Publico Sanitizado

- Fecha: 2026-03-27
- Estado: aceptada
- Alcance: publicacion | seguridad | gobernanza Git

## Contexto
La exposicion externa no debe depender permanentemente del repo privado canonico ni de una rama de trabajo temporal.

## Decision
Fijar como objetivo operativo que el sitio y la exposicion externa salgan del repo publico derivado, manteniendo el repo privado como upstream soberano. Mientras se completa la migracion en GitHub, la configuracion local y documental debe apuntar a `main` como rama objetivo.

## Consecuencias
- Positivas: reduce riesgo de filtracion y alinea publicacion con sanitizacion.
- Negativas: requiere una accion administrativa posterior para normalizar rama por defecto y Pages en GitHub.

## Referencias

- [DEC-0015](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-24_DEC-0015_protocolo_de_sanitización_para_exposición_pública.md)
- [DEC-0017](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-26_DEC-0017_operacion_humana_dual_y_superficies_privada_publica.md)

[LID]: [ruta_local_redactada]
[GOV]: [ruta_local_redactada]
[AUD]: [ruta_local_redactada]
