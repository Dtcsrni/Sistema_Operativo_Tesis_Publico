# Gobernanza

Políticas del sistema, soberanía humana, trazabilidad y disciplina de automatización responsable.

- **Tesista:** `Erick Renato Vega Ceron`
- **Fecha:** `2026-04-03`
- **Estado:** `OK`
- **Fuentes:** `00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md`, `00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md`, `00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md`, `00_sistema_tesis/config/sistema_tesis.yaml`, `00_sistema_tesis/config/ia_gobernanza.yaml`, `00_sistema_tesis/config/publicacion.yaml`
- **Aviso:** Esta wiki es un artefacto generado. Edita las fuentes canónicas y vuelve a construir.

## Navegación de esta página

- [Volver al índice](../publico/wiki/index.md).
- Página anterior en la ruta base: [Sistema](../publico/wiki/sistema.md).
- Página siguiente en la ruta base: [Terminología](../publico/wiki/terminologia.md).
- Relacionada: [Sistema](../publico/wiki/sistema.md).
- Relacionada: [Terminología](../publico/wiki/terminologia.md).
- Relacionada: [Bitácora](../publico/wiki/bitacora.md).

## Origen canónico y artefactos relacionados

### Cómo rastrear esta página hasta su origen canónico

1. Esta página derivada: [`06_dashboard/wiki/gobernanza.md`](../publico/wiki/gobernanza.md).
2. Revisa la lista de fuentes canónicas que alimentan su contenido.
3. Si necesitas la versión visual derivada, consulta el HTML hermano generado.
4. Si necesitas divulgación o evaluación externa, consulta el artefacto público sanitizado equivalente.
5. Si necesitas cambiar el contenido, edita la fuente canónica y reconstruye; no edites esta salida a mano.

### Fuentes canónicas declaradas

|Fuente canónica|Tipo|Existe|
|---|---|---|
|[`00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md)|archivo|sí|
|[`00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md)|archivo|sí|
|[`00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md)|archivo|sí|
|[`00_sistema_tesis/config/sistema_tesis.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/sistema_tesis.yaml)|archivo|sí|
|[`00_sistema_tesis/config/ia_gobernanza.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/ia_gobernanza.yaml)|archivo|sí|
|[`00_sistema_tesis/config/publicacion.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/publicacion.yaml)|archivo|sí|

### Artefactos derivados relacionados

- Markdown interno: [`06_dashboard/wiki/gobernanza.md`](../publico/wiki/gobernanza.md)
- HTML interno: [`06_dashboard/generado/wiki/gobernanza.html`](../publico/wiki_html/gobernanza.html)
- Markdown público sanitizado: [`06_dashboard/publico/wiki/gobernanza.md`](../publico/wiki/gobernanza.md)
- HTML público sanitizado: [`06_dashboard/publico/wiki_html/gobernanza.html`](../publico/wiki_html/gobernanza.html)

## Qué resuelve este subsistema

- Evita que la IA o la automatización se presenten como autoridad final.
- Obliga a distinguir entre confirmación humana, evidencia fuerte y artefacto derivado.
- Mantiene visible qué reglas aplican en privado y qué puede explicarse en público.

## Políticas del sistema

- El repositorio canónico es la fuente de verdad del sistema operativo de tesis.
- Los artefactos generados no se editan manualmente; se regeneran desde fuentes.
- La wiki verificable es una guía derivada y trazable; no sustituye a las fuentes canónicas.
- Los bloques macro se gobiernan en bloques.yaml y los subbloques/tareas operativas en backlog.csv.
- Toda decisión de arquitectura, alcance, método o evidencia se registra como decisión o bitácora.
- Los datos raw se preservan inmutables; las transformaciones se documentan y versionan.
- Toda salida asistida por IA debe someterse a revisión humana proporcional al riesgo.
- Todo flujo crítico debe poder ejecutarse por vía manual explícita; la IA es opcional y nunca requisito operativo.
- La operación se separa en superficie canónica no pública canónica y superficie pública sanitizada, ambas regenerables desde fuentes.
- Los cambios en automatización y software deben seguir TDD con evidencia de prueba ejecutada y resultado verificable.
- Los metadatos operativos críticos y la identidad de agentes se definen en configuración versionada o entorno; nunca en scripts o plantillas hardcodeadas.

## Principios de gobernanza de IA

- La IA apoya el trabajo humano; no sustituye juicio metodológico, validación experimental ni autoría responsable.
- Todo flujo crítico del sistema debe tener una vía manual explícita y operable sin depender de IA.
- Toda salida de IA debe tratarse como borrador o insumo hasta su revisión humana proporcional al riesgo.
- El uso de IA debe fortalecer aprendizaje, criterio técnico y capacidad de explicación del tesista.
- El marco es agnóstico a herramientas y proveedores; se gobierna por función, riesgo y evidencia, no por marca.
- Toda salida asistida por IA debe someterse a revisión humana proporcional al riesgo.
- Se impone el protocolo de 'Human-Agent Handshake' (DEC-0014) para toda validación de infraestructura o método.

## Vocabulario de gobernanza y trazabilidad

- `validación humana`: acto humano trazado que autoriza o confirma un cambio relevante.
- `evidencia fuente`: soporte de conversación que respalda un `VAL-STEP` nuevo cuando aplica enforcement.
- `source_event_id`: enlace desde una validación humana hacia la evidencia de conversación registrada.
- `human_validation.confirmation_text`: texto exacto de la confirmación humana en el canon.
- `enforcement`: regla obligatoria que el sistema no trata como sugerencia opcional.


## Política TDD operativa

- Todo cambio en scripts, validadores, generadores y software nuevo debe iniciar con una prueba o contrato verificable que falle antes de implementar la solución.
- No se acepta código nuevo en 04_implementacion sin pruebas asociadas o, si aún no es ejecutable, sin la especificación de prueba que lo gobernará.
- Las automatizaciones documentales deben tener pruebas de estructura, regresión o snapshot suficiente para detectar deriva funcional.
- Toda contribución asistida por IA en código o automatización debe dejar evidencia de prueba ejecutada y del resultado obtenido.

## Flujo TDD obligatorio

- escribir prueba o contrato verificable
- ejecutar prueba y confirmar falla inicial
- implementar el cambio mínimo necesario
- refactorizar conservando comportamiento
- regenerar artefactos derivados
- ejecutar validaciones y pruebas completas
- registrar resultado verificable en bitácora o evidencia de cambio

## Regla de operación humana

- Todo flujo crítico debe tener vía manual explícita y legible para el tesista y terceros humanos.
- La IA es opcional y nunca sustituye validación, criterio metodológico ni publicación responsable.
- La exposición pública solo ocurre mediante sanitización reproducible desde la base privada.
- Bundle público: `06_dashboard/publico`

## Límites de la capa pública

- La parte pública sirve para explorar y evaluar el sistema, no para sustituir el canon no público.
- El ledger detallado, la matriz interna completa, las transcripciones y la evidencia fuente permanecen fuera de la superficie pública.
- La arquitectura IoT se describe hasta el marco canónico vigente; los pendientes abiertos deben mostrarse como pendientes y no como diseño cerrado.

_Última actualización: `2026-04-03`._
