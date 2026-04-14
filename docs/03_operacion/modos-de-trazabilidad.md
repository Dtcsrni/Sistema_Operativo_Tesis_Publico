# Politica de Trazabilidad

La trazabilidad del sistema existe para reconstruir, sin ambiguedad, que se decidio, quien lo valido, con que evidencia, en que contexto y con que resultado.

## Principios

1. Toda afirmacion operativa importante debe poder vincularse a una fuente canónica.
2. Toda validacion humana relevante debe quedar asociada a un validación humana interna no pública verificable.
3. Ninguna salida automatizada sustituye la validacion humana cuando el cambio afecta gobernanza, decision, evidencia o publicacion.
4. La trazabilidad debe permitir reconstruir la secuencia: contexto, decision, implementacion, verificacion y consecuencia.
5. Las superficies derivadas nunca deben editarse como sustituto de la fuente canónica.

## Fuentes de verdad

- **Libro mayor conversacional:** [00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md)
- **Matriz maestra de validaciones:** [00_sistema_tesis/bitacora/matriz_trazabilidad.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/bitacora/matriz_trazabilidad.md)
- **Plantillas de bitacora y decision:** [00_sistema_tesis/plantillas/bitacora_template.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/plantillas/bitacora_template.md), [00_sistema_tesis/plantillas/decision_template.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/plantillas/decision_template.md)
- **Politica de gobernanza IA:** [00_sistema_tesis/config/ia_gobernanza.yaml](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/ia_gobernanza.yaml)
- **Soporte de auditoria:** [07_scripts/build_all.py](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/07_scripts/build_all.py)

## Niveles de trazabilidad

### Basico
Se usa para operaciones rutinarias de bajo riesgo.

Debe registrar:
- comando o accion ejecutada;
- archivo o artefacto afectado;
- fecha y hora;
- resultado observable.

### Alto
Se usa para decisiones, cambios operativos y seguimiento de sesiones.

Debe registrar:
- contexto resumido;
- criterio de seleccion o de cambio;
- Step ID cuando aplique;
- riesgo estimado;
- resultado o estado final;
- rutas de evidencia.

### Cientifico
Se usa para experimentacion, contraste y afirmaciones con valor de tesis.

Debe registrar:
- afirmacion o hipotesis;
- fuente primaria;
- nivel de evidencia;
- criterio de verificacion;
- resultado reproducible;
- limites del alcance.

## Registros minimos por evento

Todo evento trazable debe dejar, como minimo:

- fecha y hora;
- identificador de sesion;
- actor o sistema que produjo el evento;
- descripcion accionable de lo ocurrido;
- evidencia o enlace a artefacto;
- estado de validacion.

Cuando el evento requiera soberania humana, debe incluir ademas:

- validación humana interna no pública;
- pregunta critica o disparador;
- respuesta humana exacta o suficientemente literal;
- hash de la confirmacion verbal si aplica;
- referencia al canon de eventos.

## Reglas operativas

1. Si el cambio afecta gobernanza, bitacora, decision, publicacion o seguridad, el registro debe ser al menos de nivel Alto.
2. Si el cambio introduce una afirmacion experimental o comparativa, el registro debe ser de nivel Cientifico.
3. Si un artefacto es derivado, se documenta su origen canónico y no se reescribe a mano para corregir inconsistencias.
4. Si un evento carece de fuente verificable, se marca como pendiente y no como validado.
5. Si hay validacion humana, el texto exacto de confirmacion debe conservarse sin reinterpretacion.
6. Los resúmenes pueden ser compactos, pero nunca deben borrar la relacion entre contexto, evidencia y resultado.

## Flujo recomendado

1. Definir el contexto y el tipo de sesion.
2. Registrar la pregunta, instruccion o disparador.
3. Vincular la evidencia y el artefacto generado.
4. Marcar el nivel de trazabilidad aplicable.
5. Verificar si existe Step ID y confirmacion humana.
6. Cerrar con resultado, consecuencias y siguiente paso.

## Criterios de calidad

- Reproducibilidad: otra persona debe poder entender que se hizo y por que.
- Integridad: la evidencia debe apuntar a la fuente correcta.
- Trazabilidad: la cadena debe llevar de la salida derivada a su origen.
- Soberania: ninguna decision humana se da por asumida.
- Conservacion: los artefactos derivados no sustituyen a la fuente canónica.

## Relacion con otras piezas del sistema

- Las sesiones y la evidencia humana se reflejan en la bitacora.
- Las decisiones de arquitectura y operacion se reflejan en decisiones.
- La trazabilidad cientifica se materializa en la matriz reproducible de evidencia.
- Las validaciones automatizadas solo respaldan; no reemplazan la decision humana.

## Estado por defecto

- Basico para rutina operativa.
- Alto para cambios y sesiones con impacto.
- Cientifico para experimentacion y tesis.

## Nota final

Esta politica es descriptiva y operativa: define el minimo aceptable para que un evento sea considerado trazable dentro del sistema operativo de tesis.

_Última actualización: `2026-04-13`._
