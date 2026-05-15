# Esquema de Registro de Referencia

Campos minimos: `reference_id`, `titulo`, `autores`, `fuente`, `tipo_fuente`, `anio`, `doi`, `url`, `nivel_jerarquia`, `metadatos_verificados`, `observaciones`.

## OpenClaw `ReferenceRecord` v1

- `reference_id`: identificador `REF-*`.
- `source_type`: `article`, `book`, `dataset`, `report`, `pdf`, `web` u otro tipo controlado.
- `title`, `authors`, `year`, `publisher`, `container_title`.
- `doi`: DOI normalizado sin prefijo URL.
- `url`: URL final o URL declarada.
- `evidence_level`: nivel metodologico asignado por el investigador.
- `verification_status`: `doi_verificado_crossref`, `url_verificada`, `no_verificada` o `no_verificable`.
- `verification_notes`: lista de errores o evidencia de verificacion.
- `apa_reference`: render APA 7 operativo.
- `source_hash`: SHA-256 del payload normalizado del registro.
- `local_path`: ruta local opcional de PDF/dataset.
- `claims`: afirmaciones vinculadas.
- `tags`: temas o palabras clave.
- `metadata`: metadatos externos crudos, por ejemplo Crossref.
- `created_at`: timestamp ISO-8601.

La fuente de verdad primaria es JSONL append-only; SQLite es espejo operativo para busqueda y dashboard.

_Última actualización: `2026-05-15`._
