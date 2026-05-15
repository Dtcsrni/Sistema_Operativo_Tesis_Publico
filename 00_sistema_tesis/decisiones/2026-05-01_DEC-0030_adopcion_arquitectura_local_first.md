<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0030 | 2026-05-01 | v1.0 | Propuesta -->

# DEC-0030: Adopción de Arquitectura Local-First y Soberanía Epistémica

**Estado:** Propuesta
**Fecha:** 2026-05-01
**Autor:** Tesista (Asistido por Codex)
**Vínculo:** PET-866d6720b9c2

## Contexto
Tras la evaluación técnica registrada en el paquete PET-866d6720b9c2, se ha determinado que la dependencia de sistemas externos "Web Assisted" (especialmente ChatGPT Plus vía navegador) introduce riesgos inaceptables de inestabilidad y falta de trazabilidad (bloqueos anti-bot). Para garantizar la soberanía de los datos y la resiliencia del sistema de tesis, es necesario migrar a una arquitectura **Local-First**.

## Decisión
Se formaliza el cambio estratégico hacia una infraestructura soberana basada en los siguientes pilares:

### 1. Desactivación de Nube por Defecto
El Sistema Operativo de Tesis operará con `OPENCLAW_CLOUD_ENABLED="0"` y `OPENCLAW_CHATGPT_PLUS_ENABLED="0"` para todos los procesos de generación de canon, auditoría y síntesis académica.

### 2. Stack Tecnológico Local-First
- **Plano de Control**: OpenClaw (Orquestador de tareas y sesiones).
- **Capa de Gobernanza**: Serena MCP (Recuperación de contexto, preflight de seguridad y cumplimiento metodológico).
- **Motor de Inferencia**: Ollama (Docker Compose local con deepseek-r1:7b como modelo principal).
- **Ejecución Técnica**: Codex (Agente especializado en edición de código y ejecución de tickets bajo supervisión).

### 3. Jerarquía y Perfiles de Modelos Locales
Se establece el siguiente ranking de uso para optimizar el presupuesto de cómputo:

| Perfil | Modelo Recomendado | Uso Principal |
| :--- | :--- | :--- |
| **Académico / Síntesis** | `mistral-nemo:12b` | Redacción de tesis, análisis conceptual, revisión técnica. |
| **Código / Ejecución** | `qwen2.5-coder:14b` | Generación de tickets para Codex, debugging complejo. |
| **Comandos / Clasificación** | `qwen3:4b` | Tareas rápidas, ruteo de Telegram, auditorías simples. |

### 4. Gate Humano Mandatorio
Ningún modelo local o agente (incluyendo Codex) podrá realizar mutaciones directas en el canon (`00_sistema_tesis/canon/`, `decisiones/`, `bitacora/`) sin un Step ID de validación humana y la ejecución previa de `build_all.py`.

## Consecuencias
- **Positivas**: Soberanía total de datos, operatividad offline, eliminación de latencias externas e inestabilidad de APIs de terceros.
- **Negativas**: Mayor exigencia de hardware local (NPU/GPU) y tiempos de generación ligeramente superiores en modelos de gran escala.

## Validación Humana Requerida
- [ ] Aprobación de la política Local-First y ranking de modelos.
  - [ ] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- [ ] Implementación de los guardrails de entorno en `config/env/`.
  - [ ] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

## Estado técnico actual

- La política local-first ya quedó reflejada en la configuración operativa del workspace con desactivación de nube por defecto.
- Los guardrails de entorno requieren todavía aprobación humana para su cierre formal; no se marcarán como validados sin Step ID.
- El ajuste de `config/env/openclaw.env` dejó la ejecución local de Compose alineada con el modo de trabajo soberano sin exponer secretos.

[LID]: log_sesiones_trabajo_registradas.md
[GOV]: ../../07_scripts/guardrails.py
[AUD]: ../../07_scripts/build_all.py

_Última actualización: `2026-05-15`._
