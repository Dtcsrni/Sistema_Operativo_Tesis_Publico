# Flujos operativos

## Flujo 1. Retomar el sistema

Objetivo: volver a entender el estado actual en pocos minutos.

Secuencia:

1. Leer `README_INICIO.md`.
2. Revisar `00_sistema_tesis/manual_operacion_humana.md`.
3. Ejecutar `python 07_scripts/tesis.py status`.
4. Ejecutar `python 07_scripts/tesis.py next`.
5. Si hace falta, ejecutar `python 07_scripts/tesis.py doctor`.

Salida esperada:

- entender que es el sistema;
- identificar bloque activo, siguiente entregable y riesgos;
- saber que modulo o archivo tocar despues.

## Flujo 2. Registrar un cambio o una decision

Objetivo: incorporar trabajo nuevo sin romper soberania ni trazabilidad.

Secuencia:

1. Editar la fuente canonica correcta.
2. Si el cambio afecta arquitectura, metodo, evidencia o gobernanza, registrar decision o bitacora.
3. Si corresponde a una instruccion humana critica, vincularla a `VAL-STEP`.
4. Si el `VAL-STEP` es nuevo y esta por encima del umbral de enforcement, registrar primero la evidencia fuente de conversacion.
5. Regenerar y auditar artefactos derivados.

Salida esperada:

- cambio explicado desde su fuente de verdad;
- soporte humano verificable;
- proyecciones sincronizadas.

## Flujo 3. Auditar el estado del sistema

Objetivo: comprobar integridad, consistencia y operabilidad.

Secuencia:

1. Ejecutar `python 07_scripts/tesis.py audit --check`.
2. Ejecutar `python 07_scripts/tesis.py source status --check`.
3. Ejecutar `python 07_scripts/build_all.py`.
4. Revisar wiki y dashboard generados si se requiere lectura humana rapida.

Salida esperada:

- estado de integridad del sistema;
- estado de evidencia fuente;
- estado de salida publica y artefactos derivados.

## Flujo 4. Publicar la superficie publica

Objetivo: exponer una vista tecnica evaluable sin abrir la base privada.

Secuencia:

1. Confirmar que la base privada ya paso auditorias.
2. Ejecutar `python 07_scripts/tesis.py publish --build`.
3. Revisar `06_dashboard/publico/index.md` y `manifest_publico.json`.
4. Validar que no haya rutas privadas, hashes o referencias internas prohibidas.

Salida esperada:

- bundle publico regenerado;
- narrativa tecnica clara para terceros;
- sanitizacion intacta.

## Flujo 5. Consultar el sistema desde la capa publica

Objetivo: permitir que terceros entiendan y evalúen sin editar ni acceder a lo privado.

Secuencia:

1. Abrir el indice publico.
2. Leer la pagina de sistema para entender proposito, modulos y limites.
3. Recorrer wiki y dashboard para revisar planeacion, gobernanza, estado y cobertura.
4. Usar la informacion para evaluar consistencia, madurez y direccion del proyecto.

Salida esperada:

- comprension tecnica suficiente para evaluacion externa;
- claridad sobre que informacion es publica y que informacion permanece interna.

## Regla transversal

Todo flujo del sistema debe cumplir tres condiciones:

- tener una fuente canonica identificable;
- tener una salida humana legible;
- poder distinguir entre superficie privada y superficie publica.
