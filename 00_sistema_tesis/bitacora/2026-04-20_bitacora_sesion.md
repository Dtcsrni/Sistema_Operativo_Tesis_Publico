# Bitácora de sesión 2026-04-20

- **ID de Sesión:** codex-local-20260420-trazabilidad-total-v1
- **Cadena de Confianza (Anterior):** `sha256/39c56c2bf0dd686da8bf29d0ce4d3126fea26c3bc65bad80583fa0cf6cc74945`
- **Bloque principal:** B0
- **Tipo de sesión:** validación | implementación | administración

## Infraestructura de Sesión
- **OS:** Windows 11
- **Python:** 3.14.3
- **Herramientas Clave:** Codex, Bash local, `build_all.py`, `new_session.py`, Git, SSH al edge

## Objetivo de la sesión
Cerrar la trazabilidad de esta conversación completa y dejar consistente el nodo edge con la política operativa real: cuentas admin, hardening SSH, runtime de observabilidad y snapshot local de tokens sin API externa.

## Tareas del día
- [x] Regularizar permisos operativos en `tesis-edge` para `ErickV` y `tesisai`.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Cerrar el hardening SSH: `root` bloqueado, `orangepi` deshabilitado y `AllowUsers` restringido.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Completar el runtime del edge y la observabilidad local.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Cambiar la política de snapshot de tokens a modo local sin depender de API externa.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Trabajo realizado
- Se dejó `ErickV` como usuario administrativo efectivo en el edge, con sudo sin contraseña y grupos de mantenimiento.
- Se habilitó `tesisai` como usuario de mantenimiento con sudo, `adm` y `systemd-journal`.
- Se confirmó que `root` no conserva acceso SSH usable y que `orangepi` quedó bloqueado como cuenta operativa.
- Se estabilizaron los servicios del edge y los namespaces de log necesarios para evitar fallos de arranque por rutas inexistentes.
- Se ajustó el snapshot de tokens para operar en modo `local_only`, sin `OPENAI_ADMIN_KEY`.
- Se completó la trazabilidad de esta conversación con referencia canónica y cobertura documental.

## Evidencia Técnica e Integridad
- **Commits:** N/A en esta sesión
- **Archivos Clave:** `bootstrap/orangepi/10_primer-arranque.sh`, `bootstrap/orangepi/51_hardening-edge-iot.sh`, `bootstrap/orangepi/74_instalar-observabilidad.sh`, `bootstrap/orangepi/80_configurar-workspace-tesis.sh`, `07_scripts/build_token_usage_snapshot.py`, `07_scripts/build_dashboard.py`, `00_sistema_tesis/manual_operacion_humana.md`, `00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md`, `00_sistema_tesis/bitacora/matriz_trazabilidad.md`, `00_sistema_tesis/bitacora/2026-04-20_bitacora_sesion.md`
- **Validación del Sistema:** [x] Auditoría `build_all.py` aprobada.
  - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Trabajo asistido con IA y gobernanza
- **Proveedor de asistencia:** proveedor de IA no publicado
- **Modelo/Versión de asistencia:** modelo de IA no publicado
- **Objetivo:** cerrar la trazabilidad y normalizar el edge con política local-first y control operativo explícito.
- **Nivel de Razonamiento:** alto
- **Alineación Ética:**
    - [x] Transparencia (NIST RMF)
      - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
    - [x] Soberanía Humana (UNESCO)
      - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
    - [x] Responsabilidad (ISO 42001)
      - Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

### Validación de Soberanía (Handshake)
- **Pregunta Crítica:** ¿Autorizas dejar completamente trazada esta conversación y consolidar el estado operativo real del edge, incluyendo hardening, permisos y política local de tokens?
- **Respuesta Erick Vega:** "vale, completa la política de trazabilidad para esta conversación completa"
- **Criterio de Aceptación:** [x] Validado con validación humana interna no pública.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** validación humana interna no pública
  - **Texto exacto de confirmación verbal:** "siempre debemos de trazar todas las acciones que producen cambios, o que son relevantes, conforme la política de trazabilidad+"
  - **Hash de confirmación verbal:** `hash omitido:omitido`
  - **Fuente de verdad de confirmación:** `00_sistema_tesis/canon/events.jsonl :: validación humana interna no pública :: human_validation.confirmation_text`
  - **Hash (Contenido):** `hash omitido:omitido`
  - **Fingerprint:** `hash omitido:omitido`
  - **Nivel de Riesgo:** ALTO
  - **Modo:** Confirmación Verbal
  - **Pregunta crítica o disparador:** Instrucción humana directa para cerrar trazabilidad completa de la conversación

## Economía de uso
- Presupuesto vs Avance: se priorizó cerrar primero el bloque operativo que bloqueaba el edge y después fijar la trazabilidad documental.
- Qué se evitó: depender de API externa para snapshot de tokens o dejar el edge con cuentas ambiguas.
- Qué ameritaría subir razonamiento en la siguiente sesión: publicación formal del estado cerrado y, si hace falta, commit/push de esta regularización.

## Siguiente paso concreto
Mantener el estado del edge y la trazabilidad sincronizados con el repo, sin reintroducir dependencias externas innecesarias.

[LID]: log_sesiones_trabajo_registradas.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../07_scripts/build_all.py

_Última actualización: `2026-04-25`._
