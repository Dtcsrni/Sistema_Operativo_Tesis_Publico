# Glosario, terminologia y convenciones del sistema

## Proposito

Este glosario define el lenguaje oficial del Sistema Operativo de la Tesis.

Su objetivo es evitar ambiguedades entre:

- trazabilidad y evidencia;
- evento canonico y artefacto derivado;
- planeacion y ejecucion;
- nomenclatura documental e ingestión de evidencia;
- lectura privada y lectura publica.

## Regla de lectura

Cada entrada de este glosario indica:

- que significa el termino;
- como se usa;
- donde vive su fuente de verdad o modulo asociado;
- que no significa o con que no debe confundirse;
- un ejemplo concreto.

## Familias de identificadores

### `VAL_STEP_{nnn}`

- **Definicion:** identificador visible de una validacion humana o instruccion humana critica registrada en el canon.
- **Uso operativo:** vincular decisiones, implementaciones o cambios sustantivos a consentimiento humano verificable.
- **Fuente de verdad / modulo:** `00_sistema_tesis/canon/events.jsonl` como evento de tipo `human_validation`; proyecciones en ledger y matriz.
- **Que no significa:** no es una tarea, no es un commit, no es una evidencia por si mismo y no equivale a “verdad cientifica demostrada”.
- **Ejemplo:** `[validacion_humana_interna]` identifica la validacion humana que autorizo cerrar pendientes secundarios de la reestructura documental.

#### Desglose de `[validacion_humana_interna]`

- `VAL`: familia de validacion.
- `STEP`: paso humano trazable dentro de la cadena de soberania.
- `530`: secuencia visible del registro.
- **Funcion en el sistema:** dejar rastro canonico de una autorizacion, instruccion o validacion humana.
- **Relacion con evidencia:** a partir del umbral activo, debe enlazarse a `source_event_id`.
- **Fuente de verdad de confirmacion:** `human_validation.confirmation_text` dentro del evento canonico.

### `EVT_{nnnn}`

- **Definicion:** identificador de evento canonico general.
- **Uso operativo:** registrar eventos que no son `VAL-STEP`, por ejemplo evidencia fuente de conversacion, actividad de agente o firmas de artefacto.
- **Fuente de verdad / modulo:** `00_sistema_tesis/canon/events.jsonl`.
- **Que no significa:** no implica validacion humana por si mismo.
- **Ejemplo:** `[evento_interno]` registra una fuente de conversacion corroborable.

### `DEC-{nnnn}`

- **Definicion:** identificador de una decision formal del sistema o de la tesis.
- **Uso operativo:** fijar arquitectura, metodo, politicas o reglas relevantes.
- **Fuente de verdad / modulo:** `00_sistema_tesis/decisiones/`.
- **Que no significa:** no es una conversacion ni una tarea.
- **Ejemplo:** `DEC-0018` formaliza la evidencia fuente de conversacion para confirmacion verbal.

### `T-{nnn}`

- **Definicion:** identificador de una tarea del backlog.
- **Uso operativo:** planear trabajo concreto con prioridad, dependencia e hipotesis vinculadas.
- **Fuente de verdad / modulo:** `01_planeacion/backlog.csv`.
- **Que no significa:** no equivale a entregable ni a bloque.
- **Ejemplo:** `T-011` formaliza componentes, flujos y modos de degradacion de la arquitectura propuesta.

### `R-{nnn}`

- **Definicion:** identificador de un riesgo.
- **Uso operativo:** seguir amenazas al proyecto y su mitigacion.
- **Fuente de verdad / modulo:** `01_planeacion/riesgos.csv`.
- **Que no significa:** no es un fallo ocurrido; es una condicion de riesgo registrada.
- **Ejemplo:** `R-004` alude a la sobrecarga operativa por exceso de documentacion.

### `ENT-{nnn}`

- **Definicion:** identificador de un entregable.
- **Uso operativo:** representar una salida mayor del sistema o de la tesis.
- **Fuente de verdad / modulo:** `01_planeacion/entregables.csv`.
- **Que no significa:** no describe el trabajo fino necesario para llegar a esa salida.
- **Ejemplo:** `ENT-003` corresponde a la definicion del caso de estudio y supuestos de intermitencia.

### `B{n}`

- **Definicion:** identificador de bloque macro.
- **Uso operativo:** ordenar el proyecto por etapas mayores dependientes.
- **Fuente de verdad / modulo:** `00_sistema_tesis/config/bloques.yaml`.
- **Que no significa:** no es una tarea individual.
- **Ejemplo:** `B2` corresponde a diseño de arquitectura y formulacion de hipotesis.

### `F{n}`

- **Definicion:** identificador de fase o tramo del roadmap.
- **Uso operativo:** resumir periodos temporales del avance global.
- **Fuente de verdad / modulo:** `01_planeacion/roadmap.csv`.
- **Que no significa:** no sustituye bloques ni tareas.
- **Ejemplo:** `F3` corresponde a prototipo e instrumentacion experimental.

## Referencias globales y etiquetas

### `LID`

- **Definicion:** referencia global al ledger o libro mayor de conversaciones/validaciones.
- **Uso operativo:** enlazar integridad de trazabilidad documental.
- **Fuente de verdad / modulo:** referencias globales en decisiones y bitacoras.
- **Que no significa:** no es un ID unico de evento.
- **Ejemplo:** `[LID]` apunta al ledger del sistema.

### `GOV`

- **Definicion:** referencia global a la politica de gobernanza de IA y reglas del sistema.
- **Uso operativo:** enlazar pre-checks eticos y de gobernanza.
- **Fuente de verdad / modulo:** `ia_gobernanza.yaml`.
- **Que no significa:** no es una decision individual.
- **Ejemplo:** `[GOV]` respalda el chequeo etico en plantillas.

### `AUD`

- **Definicion:** referencia global al flujo de auditoria integral.
- **Uso operativo:** enlazar verificabilidad del sistema antes de cierre o entrega.
- **Fuente de verdad / modulo:** `build_all.py`.
- **Que no significa:** no es una evidencia por si sola; es la ruta de verificacion.
- **Ejemplo:** `[AUD]` se usa en pre-checks documentales.

### `source_event_id`

- **Definicion:** campo que enlaza una validacion humana con un evento de evidencia fuente de conversacion.
- **Uso operativo:** corroborar que un `VAL-STEP` se apoya en transcripcion y metadatos de sesion.
- **Fuente de verdad / modulo:** evento `human_validation` y evento `conversation_source_registered`.
- **Que no significa:** no reemplaza el texto de confirmacion verbal; solo lo enlaza a su evidencia.
- **Ejemplo:** `source_event_id = [evento_interno]`.

### `human_validation.confirmation_text`

- **Definicion:** campo canonico que conserva el texto exacto de la confirmacion o instruccion humana.
- **Uso operativo:** servir como fuente de verdad de confirmacion verbal.
- **Fuente de verdad / modulo:** evento `human_validation` en el canon.
- **Que no significa:** no es una interpretacion del agente; debe reflejar el texto humano exacto.
- **Ejemplo:** `"si, hazlo"`.

## Conceptos operativos del sistema

### Canon

- **Definicion:** base de verdad estructurada del sistema.
- **Uso operativo:** almacenar eventos, estado y relaciones primarias.
- **Fuente de verdad / modulo:** `00_sistema_tesis/canon/`.
- **Que no significa:** no es la wiki, ni el dashboard, ni el bundle publico.
- **Ejemplo:** `events.jsonl` pertenece al canon.

### Proyeccion derivada

- **Definicion:** salida reconstruida desde el canon o desde fuentes canonicas.
- **Uso operativo:** ofrecer vistas legibles sin editar manualmente la salida.
- **Fuente de verdad / modulo:** scripts de materializacion y generacion.
- **Que no significa:** no puede convertirse en fuente primaria.
- **Ejemplo:** `log_conversaciones_ia.md` y `matriz_trazabilidad.md` son proyecciones del canon.

### Artefacto derivado

- **Definicion:** archivo generado desde fuentes canonicas.
- **Uso operativo:** presentar informacion en forma legible, navegable o publicable.
- **Fuente de verdad / modulo:** `07_scripts/`.
- **Que no significa:** no debe editarse a mano.
- **Ejemplo:** `README.md`, `06_dashboard/wiki/`, `06_dashboard/publico/`.

### Superficie privada

- **Definicion:** capa canonica completa del sistema.
- **Uso operativo:** operar, registrar, auditar y conservar evidencia integra.
- **Fuente de verdad / modulo:** repositorio privado soberano.
- **Que no significa:** no es publicable sin sanitizacion.
- **Ejemplo:** canon, ledger, evidencia privada y bitacora interna.

### Superficie publica

- **Definicion:** capa derivada, filtrada y sanitizada para lectura externa.
- **Uso operativo:** exploracion y evaluacion tecnica.
- **Fuente de verdad / modulo:** `06_dashboard/publico/`.
- **Que no significa:** no es el canon.
- **Ejemplo:** wiki publica y `README_publico.md`.

### Enforcement

- **Definicion:** condicion o regla que el sistema obliga a cumplir.
- **Uso operativo:** endurecer trazabilidad, sanitizacion o verificaciones.
- **Fuente de verdad / modulo:** politicas y validadores.
- **Que no significa:** no es una recomendacion opcional.
- **Ejemplo:** exigir `source_event_id` para nuevos `VAL-STEP` desde un umbral.

### Evidencia fuente de conversacion

- **Definicion:** registro corroborable de una conversacion humana que sostiene un `VAL-STEP`.
- **Uso operativo:** dar evidencia fuerte a confirmaciones verbales.
- **Fuente de verdad / modulo:** eventos `conversation_source_registered` y directorio privado de conversaciones.
- **Que no significa:** no es el `VAL-STEP` mismo.
- **Ejemplo:** transcripcion asociada a `[evento_interno]`.

### Sign-off

- **Definicion:** firma o supervision humana sobre un artefacto concreto.
- **Uso operativo:** registrar que un humano reviso y firmo un archivo.
- **Fuente de verdad / modulo:** `sign_offs.json`.
- **Que no significa:** no equivale a cada `VAL-STEP`.
- **Ejemplo:** firma humana de `07_scripts/README.md`.

### Drift

- **Definicion:** diferencia entre una fuente canonica y su salida esperada materializada.
- **Uso operativo:** detectar que un artefacto derivado necesita regenerarse.
- **Fuente de verdad / modulo:** `doctor`, `publish --check`, validadores.
- **Que no significa:** no es necesariamente un error conceptual; puede ser salida pendiente de materializar.
- **Ejemplo:** `bundle público con drift`.

## Terminologia de planeacion

### Bloque

- **Definicion:** unidad macro de avance del proyecto.
- **Uso operativo:** gobernar dependencias mayores.
- **Fuente de verdad / modulo:** `bloques.yaml`.
- **Que no significa:** no es tarea fina.
- **Ejemplo:** `B0`, `B2`.

### Tarea

- **Definicion:** unidad concreta de trabajo del backlog.
- **Uso operativo:** organizar ejecucion.
- **Fuente de verdad / modulo:** `backlog.csv`.
- **Que no significa:** no es entregable final.
- **Ejemplo:** `T-011`.

### Entregable

- **Definicion:** salida mayor trazable del proyecto.
- **Uso operativo:** conectar trabajo con resultados esperados.
- **Fuente de verdad / modulo:** `entregables.csv`.
- **Que no significa:** no explica por si solo todas las tareas necesarias.
- **Ejemplo:** `ENT-004`.

### Fase

- **Definicion:** tramo temporal del roadmap.
- **Uso operativo:** leer calendario agregado.
- **Fuente de verdad / modulo:** `roadmap.csv`.
- **Que no significa:** no sustituye prioridades o dependencias tecnicas.
- **Ejemplo:** `F3`.

## Terminologia de ingestión y evidencia

### Paquete

- **Definicion:** conjunto versionado de artefactos de contexto o evidencia ingresados al sistema.
- **Uso operativo:** agrupar y versionar material recibido.
- **Fuente de verdad / modulo:** registros de ingestion y metadatos del paquete.
- **Que no significa:** no implica que todo el contenido ya sea evidencia cientifica central.
- **Ejemplo:** paquete de contexto canonico IoT `v09` o `v10`.

### Staging

- **Definicion:** area temporal aislada para revisar y verificar un paquete antes de integrarlo.
- **Uso operativo:** comprobar integridad, clasificacion y destino.
- **Fuente de verdad / modulo:** `evidencia_privada/staging_ingestion/`.
- **Que no significa:** no es la ubicacion canonica final.
- **Ejemplo:** staging previo a registrar el indice maestro.

### Indice maestro

- **Definicion:** registro consolidado que enlaza nombre original, ubicacion staging, destino canonico, modulo y hash.
- **Uso operativo:** trazar la entrada de evidencia al sistema.
- **Fuente de verdad / modulo:** `05_registros_de_ingestion/indice_maestro_ingestion_contexto_iot.csv`.
- **Que no significa:** no reemplaza el archivo original ni su lectura interpretativa.
- **Ejemplo:** una fila que mapea `columna_vertebral_de_evidencia__v09.tsv`.

### Evidencia

- **Definicion:** artefacto con valor probatorio o de soporte para la tesis o para la operacion del sistema.
- **Uso operativo:** sustentar decisiones, estado o trazabilidad.
- **Fuente de verdad / modulo:** depende del contexto; puede vivir en evidencia canonica o registros privados.
- **Que no significa:** no todo archivo es evidencia central de la tesis.
- **Ejemplo:** `columna_vertebral_de_evidencia__v09.tsv`.

### Soporte

- **Definicion:** artefacto auxiliar que ayuda a interpretar, organizar o justificar evidencia principal.
- **Uso operativo:** complementar contexto o clasificacion.
- **Fuente de verdad / modulo:** metadatos y catalogos.
- **Que no significa:** no necesariamente prueba central.
- **Ejemplo:** convencion de nombres o catalogo general de artefactos.

### Politica

- **Definicion:** documento o artefacto que fija reglas de operacion, clasificacion o publicacion.
- **Uso operativo:** gobernar decisiones repetibles.
- **Fuente de verdad / modulo:** decisiones, configuraciones o archivos de politica.
- **Que no significa:** no es evidencia experimental.
- **Ejemplo:** politica de publicacion sanitizada.

### Modulo

- **Definicion:** agrupacion logica de artefactos o funciones dentro del sistema o dentro de la evidencia ingerida.
- **Uso operativo:** clasificar por area semantica.
- **Fuente de verdad / modulo:** narrativa del sistema, catalogos y contexto canonico.
- **Que no significa:** no siempre coincide con directorio fisico.
- **Ejemplo:** `tesis_nucleo`, `arquitectura_iot`, `formacion_contextual`.

### Rol

- **Definicion:** funcion que un artefacto cumple dentro del conjunto de evidencia.
- **Uso operativo:** distinguir si un artefacto es antecedente, borrador vigente, soporte de negocio o implementacion parcial.
- **Fuente de verdad / modulo:** contexto canonico y catalogos de artefactos.
- **Que no significa:** no es una garantia de calidad.
- **Ejemplo:** `antecedente_directo`, `vigente_borrador`, `implementacion_parcial`.

### Tier

- **Definicion:** nivel relativo de prioridad o centralidad dentro del corpus ingerido.
- **Uso operativo:** ayudar a ordenar peso y urgencia de tratamiento.
- **Fuente de verdad / modulo:** contexto canonico y catalogos.
- **Que no significa:** no reemplaza juicio metodologico.
- **Ejemplo:** `tier=A`.

### Status

- **Definicion:** estado clasificado de un artefacto dentro del corpus.
- **Uso operativo:** indicar si algo es antecedente, borrador, implementacion parcial, soporte, etcetera.
- **Fuente de verdad / modulo:** archivo de contexto canonico y catalogos.
- **Que no significa:** no equivale automaticamente a “aprobado”.
- **Ejemplo:** `antecedente_directo`, `borrador_vigente`, `overleaf_parcial`.

### Accion

- **Definicion:** instruccion operativa sugerida para tratar un artefacto ingerido.
- **Uso operativo:** decidir si conservar, depurar, mover o auditar.
- **Fuente de verdad / modulo:** lectura humana del contexto canonico.
- **Que no significa:** no implica que ya fue ejecutada.
- **Ejemplo:** `depurar_y_migrar_al_repo_canonico`.

### Version

- **Definicion:** marcador de revision de un paquete o artefacto.
- **Uso operativo:** distinguir iteraciones de contenido sin perder trazabilidad.
- **Fuente de verdad / modulo:** nombre del archivo y metadatos del paquete.
- **Que no significa:** no garantiza superioridad metodologica.
- **Ejemplo:** `v09`, `v10`.

## Convenciones de nombres de archivos

- **Definicion:** reglas para construir nombres autodescriptivos, legibles y estables.
- **Uso operativo:** facilitar versionado, ingestión y lectura humana.
- **Fuente de verdad / modulo:** `00_sistema_tesis/03_metadatos/sistema_operativo_tesis_iot__convencion_de_nombres__v09.json`.
- **Que no significa:** no obliga a renombrar retrospectivamente todo archivo historico externo.
- **Ejemplo de patron:** `{ambito}__{descripcion_del_contenido}__{forma_o_proposito}__{version}.{extension}`.

### Reglas actuales de nomenclatura

- usar minusculas;
- preferir palabras completas en español;
- separar bloques semanticos con doble guion bajo `__`;
- evitar siglas opacas;
- conservar la version antes de la extension;
- preferir nombres orientados a funcion.

## Diferencias que el sistema no debe confundir

- **Validacion humana** no es lo mismo que **evidencia fuerte**.
- **Evento canonico** no es lo mismo que **proyeccion derivada**.
- **Bloque** no es lo mismo que **tarea**.
- **Entregable** no es lo mismo que **fase**.
- **Evidencia** no es lo mismo que **soporte**.
- **Politica** no es lo mismo que **modulo**.

## Regla publica

En la capa publica pueden explicarse familias y semantica de IDs, por ejemplo `VAL_STEP_{nnn}` o `EVT_{nnnn}`, pero no deben exponerse instancias privadas completas, hashes sensibles ni rutas internas no publicables.
