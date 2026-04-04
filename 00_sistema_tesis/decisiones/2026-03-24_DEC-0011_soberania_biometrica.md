<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0011_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0011: Soberanía Biométrica e Integración de Firma GPG

- **Fecha:** 2026-03-24
- **Estado:** aceptado
- **Autor(es):** Tesista / Sistema Operativo de Tesis (Antigravity)

## Contexto

Para eliminar el riesgo de atribución automática e indebida por la IA agéntica, se requiere un mecanismo que vincule físicamente la voluntad del tesista con cada cambio en el repositorio.

## Decisión

Se implementa el protocolo de **Soberanía Biométrica** mediante:

1. **Firma GPG Obligatoria:** Configuración de `commit.gpgsign true` en el entorno global.
2. **Desbloqueo Biométrico:** Configuración de `pinentry` para delegar la frase de paso al llavero del sistema operativo (Windows Hello en Win11, GNOME Keyring en Linux).
3. **Escudo de Agencia:** La IA carece de acceso a la entrada biométrica/pinentry del sistema, asegurando que el sello **[Verified]** solo pueda ser generado por el humano.

## Alternativas consideradas

1. Alternativa A
2. Alternativa B
3. Alternativa elegida

## Criterio de elección

Retroactivo: Decisión tomada durante la fase de infraestructura inicial.

## Métricas de Éxito

- [x] Validación operativa de la infraestructura.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Consistencia en auditorías automáticas.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Criterio de Aceptación Humana

- [x] Firma digital GPG del tesista.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [x] Validación de integridad estructural.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

  - **Soporte:** [Retroactivo | Step ID]
  - **Modo:** [Retroactivo | Confirmación Verbal]
  - **Fecha de Validación:** 2026-03-24
  - **Integridad:** `Hash omitido por seguridad` 
  - **Fingerprint:** `Hash omitido por seguridad` 
  - **Nivel de Auditoría:** Bajo
## Consecuencias

- **Positivas:**
  - **Autoría Indiscutible:** Cada hito de la tesis tiene una marca de tiempo criptográfica y biométrica.
  - **Transparencia Total:** Los sinodales pueden verificar la autenticidad del trabajo en GitHub.
- **Negativas/Riesgos:**
  - Requiere que el tesista tenga configurado GPG4win/GnuPG correctamente.
  - Mayor fricción operativa (un click/huella por commit), pero con alto valor metodológico.
## Trazabilidad de IA

- **Proveedor:** Google (DeepMind)
- **Modelo/Versión:** Gemini 1.5 Pro / Advanced Agentic Coding v1.0
- **Agente/Rol:** Antigravity (Assistant)
- **Nivel de Razonamiento:** alto
- **Prompts/Contexto clave:** Normalización de repositorio.

## Impacto en Presupuesto de Razonamiento

- **Consumo:** Bajo (Retroactivo)
- **Justificación:** Normalización de formato de trazabilidad.

## Implementación o seguimiento

- [x] Implementación completada en Fase B0.
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Referencias

N/A

[LID]: ruta local no pública
[GOV]: ruta local no pública
[AUD]: ruta local no pública

_Última actualización: `2026-04-04`._
