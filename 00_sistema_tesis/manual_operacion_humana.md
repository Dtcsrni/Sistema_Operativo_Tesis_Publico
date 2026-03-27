# Manual de Operación Humana

Este manual define la ruta de uso humano del sistema operativo de tesis. La IA es opcional: acelera trabajo, pero no es requisito para retomar, auditar, registrar ni publicar.

## Superficies

- **Superficie privada:** canon, backlog, decisiones, bitácora, auditoría, evidencia y configuración completa.
- **Superficie pública:** clon filtrado del repositorio privado (sin superficies restringidas), derivado desde la base privada.
- **IA opcional:** si no hay IA disponible, el sistema sigue siendo legible y operable mediante Markdown, CSV, YAML y CLI.

## Qué revisar siempre

- `00_sistema_tesis/config/sistema_tesis.yaml`
- `01_planeacion/backlog.csv`
- `01_planeacion/riesgos.csv`
- `[matriz_privada]`
- `06_dashboard/wiki/index.md`
- `06_dashboard/generado/index.html`
- `06_dashboard/publico/index.md`

## Retomar en menos de 5 minutos

1. Leer `README_INICIO.md`.
2. Ejecutar `python 07_scripts/tesis.py status`.
3. Ejecutar `python 07_scripts/tesis.py next`.
4. Si hace falta un diagnóstico más fino, ejecutar `python 07_scripts/tesis.py doctor`.

## Registrar cambio o decisión

1. Editar primero la fuente canónica correspondiente.
2. Si cambia arquitectura, método, evidencia o gobernanza, registrar decisión en `00_sistema_tesis/decisiones/`.
3. Si cambia el trabajo diario o el seguimiento, registrar la bitácora o el backlog.
4. Si la validación humana crea un `VAL-STEP` nuevo a partir de `[validacion_humana_interna]`, registrar primero la evidencia fuente con `python 07_scripts/tesis.py source register ...`.
5. Enlazar el `source_event_id` resultante al `VAL-STEP` y verificarlo con `python 07_scripts/tesis.py source verify --step-id STEP_ID_REAL`.
4. Ejecutar `python 07_scripts/build_all.py`.
5. Si habrá exposición pública, regenerar además `python 07_scripts/tesis.py publish --build`.

## Auditar estado del sistema

1. Ejecutar `python 07_scripts/tesis.py doctor`.
2. Ejecutar `python 07_scripts/tesis.py audit --check`.
3. Ejecutar `python 07_scripts/tesis.py source status --check` para revisar evidencia fuente de conversación.
3. Ejecutar `python 07_scripts/build_all.py` antes de cerrar trabajo o proponer cambios.
4. Revisar el dashboard derivado y la wiki verificable si se necesita lectura rápida humana.

## Evidencia fuente de conversación

Use este flujo cuando una confirmación verbal de Codex deba sostener un `VAL-STEP` nuevo.

0. Al abrir sesión con `python 07_scripts/tesis.py session open --session-id ...` se genera automáticamente un scaffold privado en `[evidencia_privada_redactada]/conversaciones_codex/<session_id>/`.
1. Preparar `transcripcion.md` de la conversación.
2. (Opcional) Agregar capturas si se desea evidencia visual adicional.
3. Ejecución automática recomendada: `python 07_scripts/tesis.py source auto-register --session-id ...`.
4. Alternativa manual: `python 07_scripts/tesis.py source register --session-id ... --transcript ... --quote "texto exacto"` (opcionalmente `--screenshots ...`).
5. Conservar el `[evento_interno]` resultante como `source_event_id`.
6. Crear o registrar el `VAL-STEP` enlazando ese `source_event_id`.
7. Ejecutar `python 07_scripts/tesis.py source verify --step-id STEP_ID_REAL`.

Si se requiere regenerar el scaffold manualmente:
- `python 07_scripts/tesis.py source scaffold --session-id ...`

La evidencia fuente vive en `[evidencia_privada_redactada]/conversaciones_codex/`, es privada y no debe publicarse.

## Publicación pública sanitizada

1. Confirmar que el trabajo privado ya pasó `python 07_scripts/build_all.py`.
2. Ejecutar `python 07_scripts/tesis.py publish --build`.
3. Revisar `06_dashboard/publico/index.md` y `06_dashboard/publico/manifest_publico.json`.
4. Nunca corregir a mano el bundle público; si algo está mal, ajustar la fuente privada o la política de sanitización y volver a generar.

## Publicación dual (privado + repo público derivado)

1. Mantener este repositorio como fuente soberana privada.
2. Crear o usar un repositorio GitHub público derivado (ejemplo: `Dtcsrni/Sistema_Operativo_Tesis_Publico`).
3. Confirmar árbol privado limpio (sin cambios sin commit) para conservar sincronía exacta por commit.
4. Ejecutar sincronización derivada en modo clon filtrado:
   - `python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --repo-url http[ruta_local_redactada] --branch main --push`
5. Verificar en el repo público que existan:
   - `index.md`
   - `manifest_publico.json`
   - `_sync_provenance.json`
   - `NOTA_SEGURIDAD_Y_ACCESO.md`
   - `wiki/`
   - `wiki_html/`
   - `dashboard/`
6. Verificar que `NOTA_SEGURIDAD_Y_ACCESO.md` indique política de seguridad y contacto al tesista para solicitudes de detalle no público.
7. Validar que el clon filtrado no incluya rutas privadas (`canon/`, `bitacora/`, `evidencia_privada/`, secretos locales).
8. Validar que ChatGPT use la URL del repositorio derivado público, no la del repo privado soberano.

## Rollback de publicación pública

1. Revertir el último commit en el repositorio público derivado.
2. Corregir la fuente privada o la política de sanitización.
3. Ejecutar de nuevo:
   - `python 07_scripts/build_all.py`
   - `python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --repo-url http[ruta_local_redactada] --branch main --push`
