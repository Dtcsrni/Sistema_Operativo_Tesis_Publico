# DEC-0016: Política de Gestión de Credenciales HuggingFace

**Fecha**: 2026-04-29
**Estado**: APROBADO
**Step ID**: [validación humana interna no pública]

## Contexto
Para la compilación de modelos de vanguardia (ej. Llama 3.2) y su despliegue en el Edge, se requiere acceso autenticado a los repositorios protegidos de HuggingFace.

## Decisión
Se establece el uso de **HuggingFace Access Tokens (Fine-grained)** como estándar de autenticación para el sistema OpenClaw y sus agentes.

1. **Almacenamiento**: El token se almacenará exclusivamente en el archivo `.env` bajo la variable `HF_TOKEN`.
2. **Alcance de Permisos**: El token debe tener permisos de lectura para repositorios públicos y "gated" (protegidos).
3. **Uso en Agentes**: Los scripts de automatización (`compile_rkllm.py`, `get_llama3_rkllm.py`) deben priorizar el uso de esta variable de entorno para evitar prompts interactivos que bloqueen la ejecución agéntica.
4. **Trazabilidad**: Toda descarga de modelos protegidos mediante este token debe quedar registrada en el Ledger de integridad.

## Justificación
Esta política asegura la soberanía del tesista sobre sus recursos de IA mientras permite que los agentes operen de forma autónoma y trazable sin intervención manual constante.

---
**Certificado por**: Antigravity (IA) via Instrucción del Tesista Soberano.

_Última actualización: `2026-04-29`._
