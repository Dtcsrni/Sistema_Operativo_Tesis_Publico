# README de entrada rápida

![Security Status](06_dashboard/publico/dashboard/badges/security_status.svg)
![Integrity Status](06_dashboard/publico/dashboard/badges/integrity.svg)
![Ledger Status](06_dashboard/publico/dashboard/badges/ledger.svg)

## Qué es este repositorio

Este repositorio es el **Sistema Operativo de la Tesis**: una base documental, técnica y operativa para gobernar una tesis de posgrado en IoT sobre resiliencia de telemetría y control adaptativo en entornos urbanos intermitentes.

No existe para delegar la tesis a la IA. Existe para dejar una base:

- humana;
- trazable;
- auditable;
- explicable;
- publicable sin exponer la superficie privada.

## Por qué existe

Existe para que el proyecto pueda:

- retomar contexto en minutos y no en días;
- vincular decisiones, evidencia, backlog, implementación y redacción;
- sostener soberanía humana estricta cuando se usa IA instrumental;
- separar base privada canónica de superficie pública sanitizada;
- explicarse con claridad al tesista y a lectores externos.

## Módulos del sistema

Los subsistemas principales son:

- gobierno y soberanía humana;
- trazabilidad y evidencia;
- planeación y control del trabajo;
- canon técnico y configuración;
- automatización y validación;
- publicación derivada y superficie pública;
- tesis IoT como objeto gobernado por el sistema.

## Principio operativo

- **Superficie privada:** canon, backlog, decisiones, bitácora, auditoría y evidencia completa.
- **Superficie pública:** bundle sanitizado en `06_dashboard/publico/`, derivado y no editable a mano.
- **Publicación externa:** el sitio y la exposición pública salen del downstream `https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico`, no del repo privado canónico.
- **IA opcional:** la IA acelera trabajo, pero no es requisito para operar el sistema.

## Estructura operativa nueva

La capa operativa para despliegue real y reproducibilidad ahora se organiza también en:

- `docs/`: arquitectura, operación, seguridad y reproducibilidad.
- `manifests/`: contratos máquina-legibles de almacenamiento, servicios, dominios, routing y publicación.
- `bootstrap/`: instalación por fases para host Windows y Orange Pi.
- `runtime/openclaw/`: integración opcional de OpenClaw, wrappers y políticas.
- `config/systemd/` y `config/env/`: units y variables de entorno de referencia.
- `tests/smoke/` y `tests/integration/`: pruebas operativas pensadas para el sistema objetivo.
- `benchmarks/` y `ops/`: medición, respaldo, recuperación y actualización.

## Ruta de lectura rápida

Si retomas el proyecto o necesitas explicar el sistema desde cero:

1. Lee este archivo completo.
2. Lee [`00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
3. Lee [`00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
4. Lee [`00_sistema_tesis/documentacion_sistema/flujos_operativos.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
5. Lee [`00_sistema_tesis/documentacion_sistema/glosario_terminologia_y_convenciones.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md) para entender IDs, términos y convenciones.
6. Si vas a operar el sistema, continúa con [`00_sistema_tesis/manual_operacion_humana.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
7. Si vas a preparar despliegue, revisa [`docs/02_arquitectura/arquitectura-general.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md), [`docs/02_arquitectura/topologia-de-almacenamiento.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md) y `bootstrap/`.
8. Si quieres diagnóstico inmediato, ejecuta `python 07_scripts/tesis.py status` y `python 07_scripts/tesis.py next`.

## Mapa de navegación y rastreo

Si necesitas orientarte sin perder el origen canónico:

1. Empieza en [`README_INICIO.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md) y luego entra a [`06_dashboard/wiki/index.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
2. Desde cada página de la wiki, usa el bloque `Origen canónico y artefactos relacionados`.
3. Si necesitas cambiar contenido, salta de la página derivada a su fuente canónica declarada y edítala ahí.
4. Si necesitas verificar publicación o sanitización, cruza [`06_dashboard/generado/wiki_manifest.json`](06_dashboard/wiki/nota_seguridad_y_acceso.md) con [`06_dashboard/publico/manifest_publico.json`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
5. Si necesitas trazabilidad operativa interna, revisa [`00_sistema_tesis/bitacora/matriz_trazabilidad.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md) y [`00_sistema_tesis/bitacora/log_conversaciones_ia.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).

## Entradas por necesidad

- Entender propósito, módulos y flujos: [`00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md), [`00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md) y [`00_sistema_tesis/documentacion_sistema/flujos_operativos.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
- Entender reglas e interacción humana: [`00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md) y [`00_sistema_tesis/config/ia_gobernanza.yaml`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
- Entender términos, IDs y convenciones: [`00_sistema_tesis/documentacion_sistema/glosario_terminologia_y_convenciones.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
- Entender trabajo en curso: [`01_planeacion/backlog.csv`](06_dashboard/wiki/nota_seguridad_y_acceso.md), [`01_planeacion/riesgos.csv`](06_dashboard/wiki/nota_seguridad_y_acceso.md) y [`06_dashboard/wiki/planeacion.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md).
- Entender decisiones y continuidad: [`00_sistema_tesis/decisiones`](06_dashboard/wiki/nota_seguridad_y_acceso.md) y [`00_sistema_tesis/bitacora`](06_dashboard/wiki/nota_seguridad_y_acceso.md).

## Fuentes canónicas para entender el sistema

- [`00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`00_sistema_tesis/documentacion_sistema/flujos_operativos.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`00_sistema_tesis/documentacion_sistema/glosario_terminologia_y_convenciones.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`00_sistema_tesis/config/sistema_tesis.yaml`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`00_sistema_tesis/config/publicacion.yaml`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`00_sistema_tesis/config/ia_gobernanza.yaml`](06_dashboard/wiki/nota_seguridad_y_acceso.md)

## Qué revisar siempre

- [`00_sistema_tesis/manual_operacion_humana.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`01_planeacion/backlog.csv`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`01_planeacion/riesgos.csv`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`00_sistema_tesis/bitacora/matriz_trazabilidad.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`06_dashboard/wiki/index.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`06_dashboard/generado/index.html`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`06_dashboard/publico/index.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)

## Flujos operativos mínimos

Retomar estado:

```powershell
python 07_scripts/tesis.py status
python 07_scripts/tesis.py source status --check
python 07_scripts/tesis.py next
python 07_scripts/tesis.py doctor
```

Si `doctor` reporta que el `python` del shell no coincide con la `.venv`, usa los wrappers oficiales del repo (`tesis.py`, `build_all.py`, `governance_gate.py`), porque ellos fuerzan el intérprete preferido del proyecto.

Antes de cerrar una sesión larga, revisa también la evidencia fuente de conversación con `python 07_scripts/tesis.py source status --check`.

Auditar y regenerar:

```powershell
python 07_scripts/tesis.py source status --check
python 07_scripts/tesis.py audit --check
python 07_scripts/build_all.py
```

Publicar salida sanitizada:

```powershell
python 07_scripts/tesis.py publish --check
python 07_scripts/tesis.py publish --build
python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --branch main --check
```

Para publicación real del downstream:

```powershell
python 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --repo-url https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico.git --branch main --push
```

Verificar evidencia fuente de conversación:

```powershell
python 07_scripts/tesis.py source status --check
python 07_scripts/tesis.py source verify --step-id [validacion_humana_interna]
```

## Dónde registrar cada cosa

- **Decisiones de arquitectura, gobernanza o método:** [`00_sistema_tesis/decisiones/`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- **Bitácora operativa o de sesión:** [`00_sistema_tesis/bitacora/`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- **Tareas y prioridades:** [`01_planeacion/backlog.csv`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- **Riesgos y mitigaciones:** [`01_planeacion/riesgos.csv`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- **Política pública sanitizada:** [`00_sistema_tesis/config/publicacion.yaml`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- **Evidencia fuente privada de conversación:** `[evidencia_privada_redactada]/conversaciones_codex/`

## Qué no se edita a mano

No se corrigen manualmente los artefactos derivados. Se regeneran.

- [`README.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`06_dashboard/wiki/index.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`06_dashboard/generado/index.html`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`06_dashboard/publico/index.md`](06_dashboard/wiki/nota_seguridad_y_acceso.md)
- [`06_dashboard/publico/manifest_publico.json`](06_dashboard/wiki/nota_seguridad_y_acceso.md)

## Criterio de esta base

- formatos simples antes que automatización opaca;
- trazabilidad antes que comodidad aparente;
- operación humana explícita antes que dependencia de IA;
- público derivado y sanitizado antes que duplicación manual;
- confirmación verbal corroborada con transcripción para `VAL-STEP` nuevos;
- TDD para automatización, validadores y software nuevo.
