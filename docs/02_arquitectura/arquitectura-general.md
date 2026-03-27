# Arquitectura General

## Proposito
El repositorio privado es la fuente de verdad operacional del Sistema Operativo de Tesis. Su funcion es gobernar instalacion, operacion, seguridad, trazabilidad, soporte cientifico y despliegue sobre Orange Pi 5 Plus.

## Capas
- Canon soberano: `00_sistema_tesis/`.
- Planeacion: `01_planeacion/`.
- Implementacion y experimentacion: `02_experimentos/`, `04_implementacion/`, `05_tesis_latex/`.
- Documentacion operativa estructurada: `docs/`.
- Contratos y manifiestos: `data_contracts/`, `manifests/`.
- Automatizacion y bootstrap: `07_scripts/`, `bootstrap/`, `ops/`.
- Integracion opcional OpenClaw: `runtime/openclaw/`.
- Superficie derivada: `06_dashboard/` y repo publico sanitizado.

## Reglas
- El sistema base debe operar sin OpenClaw.
- Toda exposicion externa sale del downstream publico sanitizado.
- Hardware, edge, tesis y administracion se separan por dominio.

## Validacion
- `python 07_scripts/validate_structure.py`
- `python 07_scripts/tesis.py doctor --check`
- `python 07_scripts/build_all.py`
