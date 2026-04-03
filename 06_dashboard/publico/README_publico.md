# Sistema Operativo de la Tesis

![Security Status](dashboard/badges/security_status.svg)
![Integrity Status](dashboard/badges/integrity.svg)
![Ledger Status](dashboard/badges/ledger.svg)

> Este `README.md` es un artefacto generado. No lo edites manualmente.
> Fuente de verdad: `README_INICIO.md` + `00_sistema_tesis/config/` + `01_planeacion/`.

## Propósito

Arquitectura resiliente para telemetría y control adaptativo en entornos urbanos intermitentes: simulación y validación experimental en la Zona Metropolitana de Pachuca

La intermitencia urbana de conectividad y energía degrada la continuidad de telemetría y compromete acciones de control oportunas en despliegues IoT metropolitanos. El proyecto busca diseñar y validar una arquitectura que degrade con gracia, preserve variables críticas y sostenga operación útil bajo interrupciones parciales.

Este repositorio privado gobierna decisiones, hipótesis, backlog, riesgos, experimentos, datos, implementación, redacción y gobernanza de IA para una tesis de posgrado en IoT enfocada en resiliencia operativa en entornos urbanos intermitentes.

## Estado actual

- **Versión del sistema:** `0.1.0`
- **Estado global:** `base_operativa_inicial`
- **Bloque activo:** `B0` - Gobierno del sistema de tesis y base operativa
- **Fase actual:** `investigacion_y_desarrollo_metodologico`
- **Siguiente entregable:** `ENT-001` - Base operativa del sistema de tesis
- **Riesgo principal abierto:** `R-001`

## Qué contiene

- `00_sistema_tesis/`: gobierno del sistema, decisiones, bitácora, reportes y plantillas.
- `00_sistema_tesis/documentacion_sistema/`: narrativa canónica del propósito, módulos, flujos e interacción.
- `01_planeacion/`: backlog, riesgos, roadmap y entregables canónicos.
- `02_experimentos/`: simulación y validación experimental.
- `03_datos/`: datos raw, procesados y catálogos.
- `04_implementacion/`: firmware, gateway y analítica.
- `05_tesis/`: capítulos, figuras y ensamblaje de tesis.
- `06_dashboard/`: dashboard HTML y exportables derivados.
- `07_scripts/`: validación, generación y consolidación.
- `docs/`: arquitectura, operación, seguridad y reproducibilidad estructuradas.
- `manifests/`: contratos máquina-legibles de almacenamiento, dominios, servicios y publicación.
- `bootstrap/`: instalación por fases para host Windows y Orange Pi.
- `runtime/openclaw/`: integración opcional, wrappers y políticas de OpenClaw.
- `config/systemd/` y `config/env/`: servicios, timers y variables de entorno de referencia.
- `tests/smoke/`, `tests/integration/`, `benchmarks/` y `ops/`: verificación, medición y operación de campo.

## Retoma rápida

Empieza por estos archivos:

- [`README_INICIO.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/README_INICIO.md)
- [`00_sistema_tesis/config/sistema_tesis.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/sistema_tesis.yaml)
- [`00_sistema_tesis/config/hipotesis.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/hipotesis.yaml)
- [`00_sistema_tesis/config/bloques.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/bloques.yaml)
- [`00_sistema_tesis/config/publicacion.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/publicacion.yaml)
- [`00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md)
- [`00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md)
- [`00_sistema_tesis/documentacion_sistema/flujos_operativos.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/flujos_operativos.md)
- [`00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md)
- [`00_sistema_tesis/documentacion_sistema/glosario_terminologia_y_convenciones.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/documentacion_sistema/glosario_terminologia_y_convenciones.md)
- [`01_planeacion/backlog.csv`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/01_planeacion/backlog.csv)
- [`docs/02_arquitectura/arquitectura-general.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/docs/02_arquitectura/arquitectura-general.md)
- [`manifests/storage_layout.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/manifests/storage_layout.yaml)
- [`bootstrap/orangepi/10_primer-arranque.sh`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/bootstrap/orangepi/10_primer-arranque.sh)
- [`06_dashboard/wiki/index.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/wiki/index.md)
- [`06_dashboard/generado/index.html`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/dashboard/index.html)

## Ruta de lectura

- Para entender para qué existe el sistema: `README_INICIO.md` y `proposito_y_alcance.md`.
- Para entender módulos y relaciones: `mapa_de_modulos.md`.
- Para entender recorridos de trabajo: `flujos_operativos.md`.
- Para entender identificadores, términos y convenciones: `glosario_terminologia_y_convenciones.md`.
- Para operar como tesista: `manual_operacion_humana.md`.
- Para exploración externa: wiki derivada y bundle público sanitizado.

## Navegación y trazabilidad

- La entrada navegable del sistema es [`06_dashboard/wiki/index.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/wiki/index.md).
- Cada página de la wiki debe declarar navegación local, fuentes canónicas y artefactos derivados relacionados.
- Si una salida derivada necesita cambio, la intervención correcta es sobre la fuente canónica declarada, no sobre el derivado.
- Para cerrar la cadena de rastreo revisa [`06_dashboard/generado/wiki_manifest.json`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/manifest_publico.json) y [`06_dashboard/publico/manifest_publico.json`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/manifest_publico.json).
- Para trazabilidad operativa interna revisa [`00_sistema_tesis/bitacora/matriz_trazabilidad.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/bitacora/matriz_trazabilidad.md) y [`00_sistema_tesis/bitacora/log_conversaciones_ia.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/bitacora/log_conversaciones_ia.md).

## Qué revisar siempre

- [`00_sistema_tesis/manual_operacion_humana.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/manual_operacion_humana.md)
- [`00_sistema_tesis/config/sistema_tesis.yaml`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/config/sistema_tesis.yaml)
- [`01_planeacion/backlog.csv`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/01_planeacion/backlog.csv)
- [`01_planeacion/riesgos.csv`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/01_planeacion/riesgos.csv)
- [`00_sistema_tesis/bitacora/matriz_trazabilidad.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/bitacora/matriz_trazabilidad.md)
- [`06_dashboard/wiki/index.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/wiki/index.md)
- [`06_dashboard/generado/index.html`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/dashboard/index.html)
- [`06_dashboard/publico/index.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/index.md)

## Hipótesis activas prioritarias

- **H3** · Priorización contextual protege variables críticas · prioridad `critica`
  Bloques: B2, B3, B4, B5, B6
- **HG** · Superioridad integrada de arquitectura resiliente · prioridad `critica`
  Bloques: B2, B3, B4, B5, B6, B7
- **H1** · Buffer adaptativo reduce pérdida útil · prioridad `alta`
  Bloques: B2, B4, B5, B6
- **H2** · Topología híbrida mejora resiliencia · prioridad `alta`
  Bloques: B2, B4, B5, B6, B7

## Backlog inmediato

- **T-007** · `B1` · Delimitar formalmente el caso de estudio en la Zona Metropolitana de Pachuca · prioridad `critica` · objetivo `2026-03-30`
- **T-010** · `B2` · Definir arquitectura base de comparación contra la propuesta · prioridad `critica` · objetivo `2026-04-05`
- **T-011** · `B2` · Formalizar componentes flujos y modos de degradación de la arquitectura propuesta · prioridad `critica` · objetivo `2026-04-08`
- **T-008** · `B1` · Definir taxonomía inicial de intermitencia urbana relevante para la tesis · prioridad `alta` · objetivo `2026-04-02`
- **T-009** · `B1` · Identificar variables críticas y no críticas por escenario operativo · prioridad `alta` · objetivo `2026-04-04`
- **T-012** · `B2` · Refinar hipótesis en variables métricas y criterios de soporte ejecutables · prioridad `alta` · objetivo `2026-04-10`

## Riesgos abiertos

- **R-001** · Deriva entre fuentes canónicas y artefactos generados · probabilidad `media` · impacto `alto`
- **R-002** · Ambigüedad en la línea base de comparación · probabilidad `alta` · impacto `alto`
- **R-003** · Escenarios de intermitencia poco representativos del caso de estudio · probabilidad `media` · impacto `alto`
- **R-005** · Dependencia excesiva de IA en tareas sustantivas · probabilidad `media` · impacto `alto`

## Decisiones recientes

- **2026-03-27** · [DEC-0021 Publicacion desde Downstream Publico Sanitizado](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-27_DEC-0021_publicacion_desde_downstream_publico_sanitizado.md)
- **2026-03-27** · [DEC-0020 OpenClaw como Capa Asistiva Opcional y Evaluable](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-27_DEC-0020_openclaw_como_capa_asistiva_opcional_y_evaluable.md)
- **2026-03-27** · [DEC-0019 Reestructura Operativa y Despliegue Orange Pi](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/2026-03-27_DEC-0019_reestructura_operativa_y_despliegue_orangepi.md)

## Operación

Ruta humana mínima:

```powershell
python 07_scripts/tesis.py status
python 07_scripts/tesis.py doctor
python 07_scripts/tesis.py next
```

CLI canónica:

```powershell
python 07_scripts/tesis.py status
python 07_scripts/tesis.py doctor
python 07_scripts/tesis.py next
python 07_scripts/tesis.py audit --check
python 07_scripts/tesis.py materialize
python 07_scripts/tesis.py publish --check
python 07_scripts/tesis.py publish --build
```

Flujo recomendado:

```powershell
python 07_scripts/build_all.py
```

Validar estructura y relaciones:

```powershell
python 07_scripts/validate_structure.py
python 07_scripts/validate_wiki.py
```

Generar wiki verificable Markdown + HTML:

```powershell
python 07_scripts/build_wiki.py
```

Generar dashboard HTML:

```powershell
python 07_scripts/build_dashboard.py
```

Generar esta portada:

```powershell
python 07_scripts/build_readme_portada.py
```

Exportar hoja maestra:

```powershell
python 07_scripts/export_master_sheet.py
```

Generar reporte de consistencia:

```powershell
python 07_scripts/report_consistency.py
```

## Superficies

- La superficie privada conserva canon, backlog, decisiones, bitácora y auditoría completa.
- La superficie pública vive en `06_dashboard/publico/` como bundle sanitizado y derivado.
- La IA es opcional; el sistema debe poder operarse y explicarse siguiendo rutas humanas explícitas.
- La capa pública existe para exploración y evaluación técnica, no para sustituir el canon privado.

## Criterios de gobierno

- El repositorio es la fuente de verdad.
- Los artefactos generados no se corrigen a mano; se regeneran.
- La wiki verificable es una guía derivada y trazable; no sustituye a las fuentes canónicas.
- Los bloques macro viven en `bloques.yaml`; los subbloques y tareas en `backlog.csv`.
- Toda decisión relevante debe registrarse.
- TDD rige cambios en scripts, validadores, generadores y software nuevo.
- La IA se usa como apoyo instrumental con revisión humana proporcional al riesgo.

## Artefactos derivados

- [`README.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/README_publico.md)
- [`06_dashboard/wiki/index.md`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/wiki/index.md)
- [`06_dashboard/generado/wiki/index.html`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/wiki_html/index.html)
- [`06_dashboard/generado/wiki_manifest.json`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/manifest_publico.json)
- [`06_dashboard/generado/index.html`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/dashboard/index.html)
- [`06_dashboard/generado/hoja_maestra_consolidada.csv`](https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/06_dashboard/generado/hoja_maestra_consolidada.csv)
- [`[reporte_interno_redactado]`](NOTA_SEGURIDAD_Y_ACCESO.md)

_Generado automáticamente el [fecha_hora_redactada]._
