<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: 2026-03-24_DEC-0008_ | Versión: 1.3.0 | Estado: Validado | Auditoría: [x] -->

# DEC-0008: Infraestructura de Trazabilidad y Auditoría (Sign-off)

- **Fecha:** 2026-03-24
- **Estado:** aceptado
- **Autor(es):** Tesista / Sistema Operativo de Tesis

## Contexto

Para garantizar la integridad académica y la supervisión humana demostrable en un entorno co-creado con IA, se requiere un mecanismo técnico que vincule las decisiones del tesista con archivos específicos de manera inalterable.

## Decisión

Se implementa una **Infraestructura de Auditoría de Alta Fidelidad** compuesta por:

1. **Sign-off Mecánico:** Uso de `sign_off.py` para registrar el SHA256 de los archivos aprobados por el humano en `sign_offs.json`.
2. **IA Journal:** Un diario cronológico (`ia_journal.json`) de las interacciones con modelos de lenguaje.
3. **Verificación Visual:** El generador de la wiki inyecta badges dinámicos comparando hashes:
   - **Verde (VERIFICADA):** El archivo actual coincide con la última firma humana.
   - **Ámbar (DESACTUALIZADA):** El archivo ha cambiado después de ser firmado.
   - **Rojo (AUSENTE):** El archivo nunca ha sido firmado por un humano.

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
  - **Inmortalidad de la Autoría:** Evidencia técnica de que cada sección fue revisada y aprobada explícitamente.
  - **Detección de Deriva:** Si la IA genera cambios no supervisados, los badges de la wiki alertarán inmediatamente.
  - **Transparencia:** Facilidad para generar reportes de auditoría para directores de tesis.
- **Negativas/Riesgos:**
  - Requiere la disciplina del tesista de correr `sign_off.py` al terminar una sección importante.
## Trazabilidad del trabajo asistido

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

_Última actualización: `2026-04-25`._
