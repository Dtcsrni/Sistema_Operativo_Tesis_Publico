# Verificacion de DOI y Metadata

Campos minimos: titulo, autores, anio, DOI, URL, fuente, estado de verificacion.

Si el DOI no se confirma, la referencia no se usa para afirmaciones fuertes.

## Estados

- `doi_verificado_crossref`: Crossref REST resolvio metadatos del DOI.
- `url_verificada`: no hubo DOI confirmado, pero la URL respondio.
- `no_verificada`: registro local sin verificacion en red.
- `no_verificable`: faltan DOI/URL/hash local o la verificacion fallo.

## Crossref polite pool

- Configurar `OPENCLAW_CROSSREF_MAILTO=<correo>` para que las consultas DOI usen el polite pool de Crossref.
- OpenClaw registra el fallo de Crossref como nota de verificacion; no inventa metadatos.
- El DOI se normaliza a `10.xxxx/...` y el render APA usa `https://doi.org/<doi>`.

## Reglas de rechazo

- No usar una referencia `no_verificable` para hechos fuertes.
- No aceptar citas inventadas, titulos sin DOI/URL/hash, ni PDFs locales sin hash.
- No mezclar evidencia privada con verificadores externos sin redaccion previa.

_Última actualización: `2026-04-29`._
