---
title: "SPEC: Agent Ops Core para Optimizacion Holistica"
date: 2026-05-13
category: specification
status: implementation-ready
owner: "Tesista Principal / HOA"
decisions: ["DEC-0014", "DEC-0023", "DEC-0031", "DEC-0041", "DEC-0042"]
step_id: "PENDIENTE"
trace_status: "pendiente_de_validacion_humana"
---

# SPEC: Agent Ops Core para Optimizacion Holistica

## Objetivo

Convertir el ecosistema del Sistema Operativo de Tesis en un flujo operativo eficiente para agentes agnosticos, con entrada obligatoria por Caveman, contexto compacto por Serena, fallback controlado a filesystem y gates verificables antes de cualquier cambio.

## Alcance

- Aplica a agentes que consultan, editan, auditan o preparan cambios en el repositorio.
- Primera ola: Agent Ops Core, no refactor profundo de OpenClaw, Mission Control, Docker ni canon.
- La implementacion futura debe avanzar por cambios incrementales, con gate focalizado antes de ampliar alcance.
- No se marca validacion humana sin Step ID explicito del Tesista.

## Rutas Afectadas

- `00_sistema_tesis/pendientes/`: especificaciones SDD y cola de trabajo local.
- `07_scripts/ops/`: gates operativos y reportes ejecutables.
- `07_scripts/tests/`: pruebas focalizadas de los gates.
- `04_implementacion/control_mission/mission-control.db`: verificacion SQLite en modo lectura.
- `config/backups/`, `04_implementacion/control_mission/.tmp/`, logs operativos: inventario dry-run de residuos.
- `historial interno no público/test_impact_history.jsonl`: historial append-only de impacto y resultados de pruebas.
- `07_scripts/ops/human_validation_gate.py`: preparacion dry-run de validacion humana, firma y atestacion local.

## Estado Base Verificado

- Caveman esta disponible como punto de entrada de estilo y control de ruido.
- Serena `serena-local` HTTP es la ruta operativa esperada cuando `check_serena_access.py --attempt-start-http --json` lo reporta disponible y recomendado.
- El contrato Serena vigente publica 29 herramientas, incluyendo `context.repo_map`, `context.todo_scan`, `context.bundle`, `memory.lookup` y `governance.preflight`.
- Mission Control usa SQLite en `04_implementacion/control_mission/mission-control.db` y debe verificarse en modo seguro antes de reparaciones.
- DEC-0041 y DEC-0042 ya establecen MCT, FRE, PVC y ESE como estandares de calidad.
- El worktree puede contener cambios previos amplios; ningun agente debe revertirlos sin instruccion explicita.

## Contrato Operativo

1. Entrada de sesion:
   - Ejecutar Caveman como modo base de comunicacion.
   - Verificar Serena con `python3 07_scripts/serena/check_serena_access.py --attempt-start-http --json`.
   - Si Serena no queda recomendado, registrar bloqueo operativo y degradar a filesystem scoped.
2. Contexto:
   - Usar primero herramientas compactas: `context.repo_map`, `context.todo_scan`, `context.bundle`, `memory.lookup`.
   - Evitar lecturas amplias de `runtime/models`, tokenizers, dumps, evidencia privada y salidas generadas salvo necesidad explicita.
3. Edicion:
   - Ejecutar preflight, protected path check, backup cuando aplique, diff scope y pruebas focalizadas.
   - No editar archivos protegidos ni canon sin Step ID.
   - No declarar validacion humana por inferencia.
4. Eliminacion:
   - Toda limpieza inicia como inventario dry-run.
   - Si el destino no esta vacio, requiere confirmacion humana explicita antes de borrar.
   - La rotacion automatica de backups solo puede usar politicas declaradas y ventana minima de proteccion.

## Gates Publicos

El gate Agent Ops Core debe emitir JSON con esta forma minima por cada chequeo:

```json
{
  "status": "ok|degraded|blocked|unavailable",
  "available": true,
  "recommended": true,
  "blocking_reason": "",
  "affected_paths": [],
  "required_step_id": "",
  "next_action": "none"
}
```

Gates requeridos:

- `python3 07_scripts/audit/check_agent_context_tools.py --json`
- `python3 07_scripts/serena/check_serena_access.py --attempt-start-http --json`
- `python3 07_scripts/serena/check_serena_multi_host_contract.py --json`
- Verificacion SQLite de `04_implementacion/control_mission/mission-control.db` en modo lectura.
- Seleccion incremental de pruebas con `python3 07_scripts/ops/test_impact_gate.py --json`.
- Preparacion de validacion humana con `python3 07_scripts/ops/human_validation_gate.py --json`.
- Inventario dry-run de `.bak`, logs y temporales.
- Validacion estructural de esta spec.
- `python3 07_scripts/build_all.py` solo como cierre posterior a implementacion y trazabilidad.

## Sistema de Pruebas Incremental

El sistema de pruebas debe diferenciar tres niveles:

1. **Focalizado:** pruebas unitarias o gates asociados directamente a las rutas cambiadas. Es el nivel por defecto.
2. **Integracion justificada:** pruebas que levantan contenedores, Mission Control completo, OpenClaw runtime amplio o rutas con dependencias externas. Solo se recomiendan cuando cambian rutas de integracion o configuracion.
3. **Auditoria total:** `build_all.py` completo. Solo se ejecuta como cierre posterior a implementacion y trazabilidad, o por cambio transversal de alto riesgo.

`test_impact_gate.py` debe producir un `impact_key` por hash de rutas cambiadas y comandos seleccionados. El historial `test_impact_history.jsonl` permite detectar `previous_ok_same_impact`; cuando aparece, el agente puede omitir repeticion exacta o ejecutar solo smoke si no hubo nuevos cambios.

El historial no valida por si mismo. Solo evita redundancia tecnica; la validacion humana y canonica siguen dependiendo de Step ID.

## Validacion Humana Practica

La validacion humana se separa en dos fases:

1. **Preparacion dry-run:** `human_validation_gate.py` verifica formato de validación humana interna no pública, necesidad de evento interno no público, hash de texto de confirmacion, drift de `sign_offs.json` y estado de metodos de firma sin escribir en canon.
2. **Registro canonico:** solo ocurre cuando el Tesista entrega Step ID y confirmacion explicita; despues se usan los flujos existentes de `tesis.py`/canon para registrar `human_validation`, Ledger y Matriz.

Windows Hello puede mejorar fluidez si actua como desbloqueo de una llave retenida por Windows que firma una atestacion local. No debe reemplazar Step ID, fuente conversacional ni evento canonico. La promocion a operativo requiere:

- prueba live desde el host Windows que demuestre acceso a llave/certificado protegido por Windows Hello;
- verificacion desde WSL o puente explicito sin exponer secreto privado;
- salida JSON con `available=true` solo despues de una firma de prueba;
- fallback a GPG firmado o confirmacion Step ID tradicional.

## Contrato MCP Externo

Los conectores Zotero, Scite/ArXiv, E2B, Playwright, GitHub y Docker se especifican como capacidades, no como operativos por defecto. Cada capacidad requiere:

```json
{
  "capability_id": "zotero",
  "backend": "mcp",
  "auth_required": true,
  "live_check": "connector_health",
  "fallback": "filesystem_or_manual",
  "allowed_domains": ["academico"],
  "trace_level": "alto"
}
```

Nada se marca disponible sin prueba live, conector instalado o backend local verificable.

## Pruebas y Aceptacion

- Serena/Caveman health gate devuelve `status=ok` solo si ambos estan listos.
- Contrato Serena multi-host conserva 29 herramientas esperadas.
- Inventario de limpieza dry-run no elimina archivos.
- El selector incremental recomienda pruebas focalizadas para cambios locales y marca integracion como justificada, no obligatoria por defecto.
- El historial de impacto detecta ejecuciones equivalentes previamente exitosas sin declarar validacion humana.
- El gate de validacion humana bloquea si falta Step ID y reporta Windows Hello como candidato, no como validacion canonica.
- La spec SDD contiene objetivo, alcance, decisiones DEC, rutas afectadas, gates, pruebas, rollback y cierre de trazabilidad.
- Mission Control DB pasa `PRAGMA integrity_check` en modo lectura.
- El reporte sistemico del gate es accionable y no toca canon protegido.

## Rollback

- Al ser una primera ola de especificacion y gates, el rollback tecnico consiste en retirar el gate nuevo y la spec creada.
- No se modifica Ledger, Matriz ni canon sin Step ID; por tanto no hay rollback canonico automatico.
- Si una implementacion futura toca configuracion o infraestructura, debe crear `.bak` con guardrails antes del cambio.

## Cierre de Trazabilidad

- Estado actual: pendiente de Step ID humano.
- Esta spec puede guiar implementacion tecnica, pero no queda validada hasta que el Tesista emita un Step ID.
- Cuando exista Step ID, registrar instruccion, archivos afectados, hash de contenido citado, resultado de auditoria y vinculacion en Ledger/Matriz mediante el flujo canonico vigente.

## FRE - Formato de Respuesta Epistemica

### [RAZONAMIENTO]
La optimizacion se desplaza desde instrucciones verbales hacia gates ejecutables, contexto compacto y contratos de disponibilidad.

### [EVIDENCIA Y TRAZABILIDAD]
La spec se vincula a DEC-0014, DEC-0023, DEC-0031, DEC-0041 y DEC-0042. El Step ID permanece pendiente.

### [SINTESIS CIENTIFICA]
Agent Ops Core reduce consumo de contexto al forzar descubrimiento compacto, limita mutaciones por preflight y conserva soberania humana sobre validaciones.

### [AUTO-AUDITORIA DE RIGOR]
- Se respondio al objetivo original: Si.
- Se fabricaron validaciones humanas: No.
- Pendiente critico: Step ID humano para cierre canonico.

## ESE - Esquema de Salida Estructurada

```json
{
  "integridad": {
    "hash_de_fuente": "pendiente_en_cierre_canonico",
    "fidelidad_de_extraccion": 1.0
  },
  "metadatos_epistemicos": {
    "conceptos_primarios": ["Agent Ops Core", "Serena MCP", "Caveman", "Mission Control", "MCT", "FRE", "ESE"],
    "puntaje_de_relevancia": 100
  }
}
```

_Última actualización: `2026-05-15`._
