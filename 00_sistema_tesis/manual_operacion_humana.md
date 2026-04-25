# Manual de Operación Humana

Este manual es la ruta operativa del tesista. Explica cómo usar el sistema; la explicación conceptual del por qué existe y cómo se organiza vive en `README_INICIO.md` y en `00_sistema_tesis/documentacion_sistema/`.

La IA es opcional: acelera trabajo, pero no es requisito para retomar, registrar, auditar ni publicar.

## Superficies

- **Superficie privada:** canon, backlog, decisiones, bitácora, auditoría, evidencia y configuración completa.
- **Superficie pública:** clon filtrado y bundle público curado derivados desde la base privada.
- **IA opcional:** si no hay IA disponible, el sistema sigue siendo legible y operable mediante Markdown, CSV, YAML y CLI.

## Nodos operativos

- **Escritorio primario (`desktop_workspace`):** Visual Studio Code en el PC como estación principal de autoría, diseño, análisis, construcción documental y mantenimiento del repositorio soberano.
- **Nodo edge (`orange_pi_edge`):** Orange Pi para `edge_iot`, observabilidad local, diagnóstico técnico, pruebas en campo y control del stack IoT.
- **Integración oficial:** `git_sync` más artefactos, contratos de datos y evidencia edge explícita.
- **No es flujo normal:** editar la arquitectura principal desde Orange Pi ni depender de un workspace remoto montado por red.

## Ruta mínima de operación

### Retomar

1. Leer `README_INICIO.md`.
2. Ejecutar `python 07_scripts/tesis.py status`.
3. Ejecutar `python 07_scripts/tesis.py source status --check`.
4. Ejecutar `python 07_scripts/tesis.py next`.
5. Si hace falta un diagnóstico más fino, ejecutar `python 07_scripts/tesis.py doctor`.
6. Si `doctor` muestra un `Python shell` distinto al `Python preferido repo`, seguir usando los wrappers oficiales; ellos fuerzan la `.venv` del proyecto.

### Flujo normal escritorio -> Orange Pi

1. Trabajar el cambio principal en el escritorio.
2. Ejecutar `python 07_scripts/build_all.py` en el workspace soberano antes de promoverlo.
3. Sincronizar hacia la Orange Pi por Git y, cuando aplique, por artefactos o contratos explícitos.
4. En Orange Pi operar, diagnosticar o validar `edge_iot` y recuperar logs, métricas o evidencia técnica.
5. Devolver al escritorio cualquier hallazgo relevante para su registro formal en decisión, bitácora o backlog.
6. Usar [docs/03_operacion/flujo-escritorio-orange-pi.md](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/docs/03_operacion/flujo-escritorio-orange-pi.md) como procedimiento operativo base entre ambos nodos.
7. Elegir el perfil de sincronización edge según el cambio: `repo-only`, `repo+postcheck` o `repo+restart-edge`.

### Registrar cambio o decisión

1. Editar primero la fuente canónica correspondiente.
2. Si cambia arquitectura, método, evidencia o gobernanza, registrar decisión en `00_sistema_tesis/decisiones/`.
3. Si cambia trabajo diario, seguimiento o cierre de sesión, registrar la bitácora o el backlog.
4. Si la validación humana crea un `VAL-STEP` nuevo a partir de validación humana interna no pública, registrar primero la evidencia fuente con `python 07_scripts/tesis.py source register ...` o `source auto-register`.
5. Enlazar el `source_event_id` resultante al `VAL-STEP` y verificarlo con `python 07_scripts/tesis.py source verify --step-id STEP_ID_REAL`.
6. Ejecutar `python 07_scripts/build_all.py`.
7. Si habrá exposición pública, regenerar además `python 07_scripts/tesis.py publish --build`.

### Auditar

1. Ejecutar `python 07_scripts/tesis.py doctor`.
2. Ejecutar `python 07_scripts/tesis.py source status --check`.
3. Ejecutar `python 07_scripts/tesis.py audit --check`.
4. Ejecutar `python 07_scripts/build_all.py` antes de cerrar trabajo o proponer cambios.
5. Revisar wiki y dashboard generados si se necesita lectura rápida humana.
6. El snapshot de tokens es opcional y local por defecto; no requiere `OPENAI_ADMIN_KEY` mientras no exista presupuesto para API externa.

### Preparar despliegue en Orange Pi

1. Revisar `docs/02_arquitectura/arquitectura-general.md` y `docs/02_arquitectura/topologia-de-almacenamiento.md`.
2. Validar descargas e imagen base desde `bootstrap/host/`.
3. Ejecutar por fases `bootstrap/orangepi/` en lugar de depender de un script monolítico.
4. Correr `bash bootstrap/orangepi/90_postcheck.sh` al finalizar.
5. Tratar `/srv/tesis/repo` como clon operativo local de despliegue y supervisión, no como repositorio principal de autoría.
6. Registrar cualquier desviación real de hardware, almacenamiento o servicios en bitácora/decisión.
7. Para actualizar el clon operativo desde el escritorio, preferir `bash /srv/tesis/repo/ops/actualizacion/sync_repo_desde_desktop.sh repo+postcheck`; ese perfil también limpia ruido edge-volatil que no aporta al runtime (`.pytest_cache`, `__pycache__`, bytecode, backups y staging privado).
8. Usar `repo-only` si solo se alineará el clon local, y `repo+restart-edge` si el cambio exige reiniciar `edge-iot-worker.service`.
9. Acceder por SSH al host `tesis-edge` con el usuario dedicado `tesisai` y la llave definida en `ORANGEPI_KEY_PATH`; no usar contraseña.

### Operación permitida en Orange Pi

1. Ejecutar servicios `edge_iot`, healthchecks, watchdogs, observabilidad y pruebas técnicas del stack IoT.
2. Aplicar hotfixes operativos del dominio edge cuando sean necesarios y queden trazados en el repositorio soberano.
3. Recuperar logs, evidencias de runtime, métricas y artefactos locales para su análisis posterior en el escritorio.
4. No usar la Orange Pi como superficie principal de redacción de tesis ni de decisiones arquitectónicas.

### Publicación pública

1. Confirmar que el trabajo privado ya pasó `python 07_scripts/build_all.py`.
2. Ejecutar `python 07_scripts/tesis.py publish --build`.
3. Revisar `06_dashboard/publico/index.md` y `06_dashboard/publico/manifest_publico.json`.
4. Ejecutar `python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --branch main --check` antes de publicar.
5. Instalar hooks locales con `python 07_scripts/install_hooks.py`; desde ahí, cada commit o merge en `main` resincroniza automáticamente el clon local hermano `../Sistema_Operativo_Tesis_Publico`.
6. Publicar el downstream remoto con `python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --repo-url https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico.git --branch main --push`.
7. La actualización automática del repo público remoto ocurre solo desde `main` después de que `verify` termine en verde y requiere `PUBLIC_REPO_PAT` en GitHub Actions.
8. Nunca corregir a mano el bundle público ni usar GitHub Pages del repo privado; si algo está mal, ajustar la fuente privada o la política de sanitización y volver a generar.

## Evidencia fuente de conversación

Use este flujo cuando una confirmación verbal de Codex deba sostener un `VAL-STEP` nuevo.

1. Abrir o preparar sesión de evidencia en `evidencia privada no publicada/conversaciones_codex/<session_id>/`.
2. Preparar `transcripcion.md` de la conversación.
3. Registrar la fuente con `python 07_scripts/tesis.py source auto-register --session-id ...` o `source register`.
4. Conservar el evento interno no público resultante como `source_event_id`.
5. Registrar el `VAL-STEP` enlazando ese `source_event_id`.
6. Ejecutar `python 07_scripts/tesis.py source verify --step-id STEP_ID_REAL`.

Si se requiere scaffold manual:

- `python 07_scripts/tesis.py source scaffold --session-id ...`

La evidencia fuente vive en `evidencia privada no publicada/conversaciones_codex/`, es privada y no debe publicarse.

## Firma humana de artefactos

La firma humana no se autoemite desde IA sin contexto trazable. Si un artefacto requiere renovar supervisión humana, el tesista debe registrar la firma explícitamente o usar la auto-firma controlada con `VAL-STEP` y evidencia fuente válida.

- Comando base: `python 07_scripts/sign_off.py 07_scripts/README.md "Revisado y aprobado por tesista humano." --session-id <session_id>`
- Auto-firma controlada (solo drift en fuentes wiki directas):
  - `python 07_scripts/tesis.py signoff sync --step-id validación humana interna no pública --source-event-id EVT-XXXX --session-id <session_id> --check`
  - `python 07_scripts/tesis.py signoff sync --step-id validación humana interna no pública --source-event-id EVT-XXXX --session-id <session_id>`
- En `pre-push` (hook instalado), exportar antes:
  - `SISTEMA_TESIS_STEP_ID=validación humana interna no pública`
  - `SISTEMA_TESIS_SOURCE_EVENT_ID=EVT-XXXX`
  - `SISTEMA_TESIS_SESSION_ID=<session_id_opcional>`
  - `PUBLIC_REPO_PAT=<token>`
- Con esas variables, `pre-push` ejecuta automáticamente: gate -> auto-firma controlada -> sincronización al repo público derivado.
- Verificación: `python 07_scripts/tesis.py doctor --check`

## Qué revisar siempre

- `00_sistema_tesis/config/sistema_tesis.yaml`
- `01_planeacion/backlog.csv`
- `01_planeacion/riesgos.csv`
- `00_sistema_tesis/bitacora/matriz_trazabilidad.md`
- `06_dashboard/wiki/index.md`
- `06_dashboard/generado/index.html`
- `06_dashboard/publico/index.md`

## Publicación dual (privado + repo público derivado)

1. Mantener este repositorio como fuente soberana privada.
2. Crear o usar un repositorio GitHub público derivado.
3. Confirmar árbol privado limpio para conservar sincronía exacta por commit.
4. Ejecutar sincronización derivada en modo clon filtrado:
   - `python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --repo-url https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico.git --branch main --push`
5. Instalar `python 07_scripts/install_hooks.py` para que el espejo local se mantenga al día automáticamente cuando `main` cambie.
6. Verificar que el repo público incluya `index.md`, `manifest_publico.json`, `_sync_provenance.json`, `NOTA_SEGURIDAD_Y_ACCESO.md`, `wiki/`, `wiki_html/` y `dashboard/`.
7. Validar que el clon filtrado no incluya rutas privadas (`canon/`, `bitacora/`, `evidencia_privada/`, secretos locales).
8. Validar que cualquier consumidor externo use la URL del repositorio derivado público y no la del repo privado soberano.
9. Confirmar que GitHub Pages quede deshabilitado en el repo privado y habilitado solo en el repo público derivado.

## Rollback de publicación pública

1. Revertir el último commit en el repositorio público derivado.
2. Corregir la fuente privada o la política de sanitización.
3. Ejecutar de nuevo:
   - `python 07_scripts/build_all.py`
   - `python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --repo-url https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico.git --branch main --push`

_Última actualización: `2026-04-25`._
