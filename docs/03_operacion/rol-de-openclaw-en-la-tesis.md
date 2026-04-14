# Rol de OpenClaw en la Tesis

OpenClaw se posiciona como herramienta de apoyo y objeto de evaluacion secundaria. No es nucleo indispensable de la tesis ni del pipeline IoT base.

## Obligaciones
- El sistema debe instalarse y operar sin OpenClaw.
- Debe existir baseline sin OpenClaw.
- Su integracion debe ser modular, reversible y desacoplada.
- El despliegue en Orange Pi debe separar claramente `tesis-os` base, `openclaw`, `Ollama` y la vía NPU experimental.
- `Ollama` es el runtime local principal; la vía Rockchip NPU se instala como carril secundario y no entra al ruteo normal sin benchmark exitoso y decisión explícita.
- `openclaw` no puede convertirse en puente HTTP entre dominios.
- `openclaw` solo intercambia artefactos con otros dominios por rutas y comandos explícitos.

_Última actualización: `2026-04-14`._
