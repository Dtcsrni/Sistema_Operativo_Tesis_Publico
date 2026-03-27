# README de entrada rápida

![Security Status](06_dashboard/generado/badges/security_status.svg)
![Integrity Status](06_dashboard/generado/badges/integrity.svg)
![Ledger Status](06_dashboard/generado/badges/ledger.svg)

## Qué es este repositorio

Este repositorio es el **Sistema Operativo de la Tesis** para una investigación de posgrado en IoT sobre resiliencia de telemetría y control adaptativo en entornos urbanos intermitentes.

Su objetivo no es delegar la tesis a la IA. Su objetivo es dejar una base **humana, trazable, auditable y explicable** para gobernar:

- decisiones
- hipótesis
- backlog
- riesgos
- experimentos
- datos
- implementación
- redacción
- uso instrumental de IA
- exposición pública sanitizada

## Principio operativo

- **Superficie privada:** canon, backlog, decisiones, bitácora, auditoría y evidencia completa.
- **Superficie pública:** bundle sanitizado en `06_dashboard/publico/`, derivado y no editable a mano.
- **IA opcional:** la IA acelera trabajo, pero no es requisito para operar el sistema.

## Retoma rápida

Si retomas el proyecto después de días o semanas, sigue esta ruta:

1. Lee [`00_sistema_tesis/manual_operacion_humana.md`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/manual_operacion_humana.md).
2. Ejecuta `python 07_scripts/tesis.py status`.
3. Ejecuta `python 07_scripts/tesis.py next`.
4. Si necesitas diagnóstico completo, ejecuta `python 07_scripts/tesis.py doctor`.

## Archivos canónicos principales

- [`00_sistema_tesis/config/sistema_tesis.yaml`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/sistema_tesis.yaml)
- [`00_sistema_tesis/config/hipotesis.yaml`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/hipotesis.yaml)
- [`00_sistema_tesis/config/bloques.yaml`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/bloques.yaml)
- [`00_sistema_tesis/config/ia_gobernanza.yaml`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/ia_gobernanza.yaml)
- [`00_sistema_tesis/config/publicacion.yaml`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/publicacion.yaml)
- [`01_planeacion/backlog.csv`](/V:/Sistema_Operativo_Tesis_Posgrado/01_planeacion/backlog.csv)
- [`01_planeacion/riesgos.csv`](/V:/Sistema_Operativo_Tesis_Posgrado/01_planeacion/riesgos.csv)

## Qué revisar siempre

- [`00_sistema_tesis/manual_operacion_humana.md`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/manual_operacion_humana.md)
- [`00_sistema_tesis/config/sistema_tesis.yaml`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/sistema_tesis.yaml)
- [`01_planeacion/backlog.csv`](/V:/Sistema_Operativo_Tesis_Posgrado/01_planeacion/backlog.csv)
- [`01_planeacion/riesgos.csv`](/V:/Sistema_Operativo_Tesis_Posgrado/01_planeacion/riesgos.csv)
- [`00_sistema_tesis/bitacora/matriz_trazabilidad.md`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/bitacora/matriz_trazabilidad.md)
- [`06_dashboard/wiki/index.md`](/V:/Sistema_Operativo_Tesis_Posgrado/06_dashboard/wiki/index.md)
- [`06_dashboard/generado/index.html`](/V:/Sistema_Operativo_Tesis_Posgrado/06_dashboard/generado/index.html)
- [`06_dashboard/publico/index.md`](/V:/Sistema_Operativo_Tesis_Posgrado/06_dashboard/publico/index.md)

## Comandos útiles

Estado humano y próxima acción:

```powershell
python 07_scripts/tesis.py status
python 07_scripts/tesis.py next
python 07_scripts/tesis.py doctor
```

Validación y auditoría:

```powershell
python 07_scripts/tesis.py audit --check
python 07_scripts/build_all.py
```

Publicación sanitizada:

```powershell
python 07_scripts/tesis.py publish --check
python 07_scripts/tesis.py publish --build
```

Evidencia fuente de conversación:

```powershell
python 07_scripts/tesis.py source register --session-id codex-YYYYMMDD --transcript ruta\\a\\transcripcion.md --screenshots ruta\\a\\captura_001.png --quote "texto exacto"
python 07_scripts/tesis.py source verify --step-id VAL-STEP-XXX
python 07_scripts/tesis.py source status --check
```

## Dónde registrar cada cosa

- **Decisiones de arquitectura, gobernanza o método:** [`00_sistema_tesis/decisiones/`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/decisiones)
- **Bitácora operativa o de sesión:** [`00_sistema_tesis/bitacora/`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/bitacora)
- **Tareas y prioridades:** [`01_planeacion/backlog.csv`](/V:/Sistema_Operativo_Tesis_Posgrado/01_planeacion/backlog.csv)
- **Riesgos y mitigaciones:** [`01_planeacion/riesgos.csv`](/V:/Sistema_Operativo_Tesis_Posgrado/01_planeacion/riesgos.csv)
- **Política pública sanitizada:** [`00_sistema_tesis/config/publicacion.yaml`](/V:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/publicacion.yaml)
- **Evidencia fuente privada de conversación:** `00_sistema_tesis/evidencia_privada/conversaciones_codex/`

## Qué no se edita a mano

No se corrigen manualmente los artefactos derivados. Se regeneran.

- [`README.md`](/V:/Sistema_Operativo_Tesis_Posgrado/README.md)
- [`06_dashboard/wiki/index.md`](/V:/Sistema_Operativo_Tesis_Posgrado/06_dashboard/wiki/index.md)
- [`06_dashboard/generado/index.html`](/V:/Sistema_Operativo_Tesis_Posgrado/06_dashboard/generado/index.html)
- [`06_dashboard/publico/index.md`](/V:/Sistema_Operativo_Tesis_Posgrado/06_dashboard/publico/index.md)
- [`06_dashboard/publico/manifest_publico.json`](/V:/Sistema_Operativo_Tesis_Posgrado/06_dashboard/publico/manifest_publico.json)

## Criterio de esta base

- formatos simples antes que automatización opaca
- trazabilidad antes que comodidad aparente
- operación humana explícita antes que dependencia de IA
- público derivado y sanitizado antes que duplicación manual
- confirmación verbal corroborada con transcripción y captura para `VAL-STEP` nuevos
- TDD para automatización, validadores y software nuevo
