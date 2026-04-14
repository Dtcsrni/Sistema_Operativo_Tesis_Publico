# OpenClaw Control Plane Local

## Propósito
`openclaw` opera como plano de control asistivo de `tesis-os`. No sustituye el canon ni los scripts oficiales del sistema de tesis.

## Subsistemas
- `control-plane`: CLI local, API del workspace y panel web.
- `policy-engine`: ruteo por dominio, riesgo, sensibilidad y costo.
- `evidence-engine`: persistencia local auditable con hashes SHA-256.
- `provider-gateway`: adaptadores para local, web asistida y APIs formales.
- `hardware-broker`: lectura controlada del host y de las capacidades de Orange Pi.

## Límites duros
- `openclaw` no valida por sí mismo decisiones ni validación humana interna no pública.
- `openclaw` no publica directamente a superficies públicas.
- `edge` y `administrativo` quedan local-first y sin nube por defecto.
- El fallo de `openclaw` no detiene `tesis-os`.

## Persistencia
- Estado operativo local: SQLite.
- Fuente de verdad canónica: archivos versionados del repositorio.
- Evidencia: registros locales hashables y exportables para integración posterior al ledger en modo draft.
- Namespace operativo Orange Pi: `/var/lib/herramientas/openclaw`, `/var/cache/herramientas/openclaw`, `/var/log/openclaw`.
- Entorno efectivo de despliegue: `/etc/tesis-os/openclaw.env`.
- Secretos por dominio: `/etc/tesis-os/domains/<dominio>.env`.

## Interfaz inicial
- CLI: `doctor`, `tarea nueva`, `tarea enrutar`, `ejecutar --simulacion`, `aprobar`, `auditar`, `sesion cerrar`, `proveedor estado`.
- Web local: tablero de tareas, aprobaciones, costos, trazabilidad y estado del host.
- CLI académica: `academico estado-del-arte`, `academico metodologia`, `academico redaccion`, `academico exportar-propuesta`.
- CLI de despliegue local: `proveedor medir`, `pasarela preflight`, `pasarela estado`.
- CLI de secretos y presupuesto: `secretos estado`, `presupuesto estado`, `presupuesto simular`.

## Proveedores v1
- Línea 1: `local` y `ollama_local`.
- Línea 2 experimental: `rknn_llm_experimental`.
- Nube API formal: `groq_api`, `gemini_api`, `openai_api`.
- Web asistida supervisada: `gemini_web_assisted`, `chatgpt_plus_web_assisted`.
- Las sesiones web asistidas se clasifican como `human_supervised_web_session` y no como automatización ciega.

## Secretos por dominio
- `personal`: solo local, sin nube.
- `profesional`: `groq_api` y `openai_api` bajo presupuesto controlado.
- `academico`: `groq_api`, `gemini_api`, `openai_api` y carriles web asistidos supervisados.
- `edge` y `administrativo`: sin nube por default.
- El `secret-resolver` solo busca rutas conocidas y nunca imprime valores.

## Presupuesto y degradación
- El presupuesto global sigue en `00_sistema_tesis/config/token_budget.json`.
- `openclaw` agrega política por dominio y ledger local complementario por proveedor.
- Si se agota el dominio, la nube se degrada a local/offline/manual aunque exista remanente global.
- Si se agota el global, toda nube queda bloqueada.

## Despliegue Orange Pi 5 Plus
- Baseline objetivo: Orange Pi 5 Plus `8 GB` con Debian 12 oficial.
- Identidad de servicio: `tesis:tesis`.
- Runtime principal local: `Ollama`.
- Ruta NPU secundaria: `RKLLM`/`RKNN-LLM` instalada desde bootstrap pero marcada como experimental.
- `openclaw` no reemplaza el sistema base; si el gateway, Ollama o la vía NPU fallan, `tesis-os` debe seguir operando.

## Casos de uso académicos v1
- `estado_del_arte`: triage de literatura, matriz de literatura, matriz de afirmaciones y nota crítica de contraste.
- `metodologia`: ficha de estudio, matriz de exploración, nota metodológica y propuesta de decisión o pendiente.
- `redaccion_tesis`: borrador Markdown trazable y fragmento LaTeX derivado desde la misma estructura de párrafos.

## Contratos académicos
- `AcademicWorkPacket`: paquete común con `mode`, `question`, `scope`, `sources`, `claims`, `outputs` y `traceability_links`.
- `LiteratureRecord`: contrato alineado a la matriz de literatura del repositorio.
- `ClaimRecord`: afirmación clasificada con verificación, fuentes e impacto sobre la tesis.
- `WritingDraft`: borrador paralelo Markdown/LaTeX para secciones de tesis.

## Promoción a validación humana
- `openclaw` puede exportar `openclaw_proposal` al canon.
- `openclaw` puede preparar un paquete técnico de validación con pregunta crítica, `session_id`, `step_id` sugerido y comandos canónicos.
- La promoción final a validación humana interna no pública ocurre únicamente mediante:
  - evidencia fuente registrada (`conversation_source_registered`),
  - coincidencia exacta entre `quoted_text` y `confirmation_text`,
  - ejecución explícita de `tesis.py proposal finalize-openclaw`.

_Última actualización: `2026-04-14`._
